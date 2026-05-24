# CONDITIONAL-CONTEXT-PLAN

**Status**: **ABORTED 2026-05-24** on `develop-2.0-init`. Step 0 gate ran and failed (kill-switch fires); the plan's core premise was found false. Never started — no `src/rules/`, no emitter, no commits. See *Step 0 result* + *Abort rationale* below. Archived to `done-plans/`.

**Status (historical)**: Drafted 2026-05-20. Primitive verification re-affirmed 2026-05-21 by user (Claude Code v2.0.64+ ships `.claude/rules/*.md` with `paths:` frontmatter as a first-class primitive alongside `CLAUDE.md` / `settings.json` / `skills/` / `agents/`). Plan stayed queued, not started.
**Branch**: `develop-2.0-init`. Queue: forcing-functions Phase 2 ahead; PR-REVIEW + DISCOVER-HANDOFF code-complete (awaiting testForge20 manual e2e), do not block this plan after their tests pass.
**Driver**: Comparison vs leaked Kiro system prompts (gist `CypherpunkSamurai/ad7be9c3ea07cf4fe55053323012ab4d`, 2026-05-20 conversation) surfaced one Claude-Code-supported primitive worth importing: **path-scoped `.claude/rules/*.md`** with `paths:` frontmatter. Goal: move slices of the always-on consumer-overlay `src/CLAUDE.md` (306 lines, ~4-5K tokens per turn) into conditionally-loaded rules so each domain's discipline lights up only when relevant files are in play.

Verification of Claude Code support performed by `claude-code-guide` agent on 2026-05-20, re-affirmed by user 2026-05-21:
- `.claude/rules/*.md` with `paths:` frontmatter — **supported**. Available since Claude Code v2.0.64. Scope: project (`.claude/rules/`) + global (`~/.claude/rules/`). All `.md` in dir auto-loaded each session alongside `CLAUDE.md`. Git-committable (unlike `settings.local.json`). Docs:
  - Directory reference: https://code.claude.com/docs/en/claude-directory
  - Rules section: https://code.claude.com/docs/en/memory#organize-rules-with-claude/rules/
- `.claude/skills/*/SKILL.md` with `paths:` — **supported** (alternate venue; not used in this plan because forge already owns commands not skills).
- Agents / commands / CLAUDE.md sections — **NOT** conditionally gateable. Out of scope.

**Scope-decision note (2026-05-21)**: target-repo emission strategy (which `.claude/rules/*.md` files the framework ships into a consumer project, gated on detected project nature) is a per-implementation decision deferred to Step 1 / Step 2 of execution. It is NOT a planning premise to revisit pre-pickup. Plan scope as written (consumer-overlay `src/CLAUDE.md` split) holds.

## Context for next session

The 4-command sequence (`/init-forge` → `/generate-docs` → `/configure` → `/constitute`) emits the runtime overlay into a consumer project. Current consumer-side `src/CLAUDE.md` packs every discipline rule (audit format, default-argue, test-first, sentence-level hallucination check, cross-check, helper-owns-shape, etc.) into one always-on file. Cost = full 306 lines billed every turn even when the user is editing a markdown spec, running a one-line bash investigation, or asking a meta question.

Two reasons this matters now:
1. **Token economics** — every consumer turn pays for rules that don't apply (e.g. python-helper test-first rule loaded when no `.py` file is touched). Multiplied across N consumer projects × M sessions per day = real spend.
2. **Discipline signal degradation** — a single 300-line file blurs which rule applies *now*. A focused 30-line rule that loads only when `src/devforge/lib/**` is touched is a sharper signal than the same rule embedded at line 142 of an always-on wall.

**This plan does NOT touch**:
- Forge-internal `CLAUDE.md` at repo root (154 lines) — that's read by forge maintainers, not consumers; reorganizing it is a separate, lower-priority concern.
- Agent gating (Claude Code doesn't support it).
- File-include `@path` syntax for commands/agents (Claude Code doesn't support it; CLAUDE.md `@`-imports are deferred to a separate small-edit pass — see *Out of scope* below).

**Kill-switch**: Step 0 must measure ≥15% token reduction from the candidate set, OR the plan aborts. We are not building this for theoretical neatness.

Cross-cutting discipline (apply to every step):
- **Test-first** per `feedback_test_first_python_helpers.md` — every new emitter function or rule-load probe ships with a pytest case written + run same turn.
- **Sentence-level hallucination check** per `feedback_sentence_level_hallucination_check_specs.md` — every line written into a new `.claude/rules/*.md` must be verifiable now / mechanically true.
- **Cross-check after every change** per `feedback_cross_check_after_every_change.md` — when a rule is migrated out of `src/CLAUDE.md`, grep the consumer-overlay surface (`src/commands/**`, `src/agents/**`) for sentences that referenced the rule by location ("see CLAUDE.md §discipline") and update them to the new rules-file path.
- **Emitter cross-check** per `feedback_emitter_promoted_cross_check.md` — `scripts/emitters/claude.py` does NOT auto-discover; any new file class (rules) needs explicit registration and end-to-end install verification.
- **Claude-Code-authoring conventions** per `feedback_claude_code_authoring_best_practices.md` — re-invoke `claude-code-guide` agent before Step 2 freezes the rules-file frontmatter schema (the 2026-05-20 verification covered existence; Step 2 needs exact field names + valid values).
- **No escape hatches** per `feedback_zero_escape_hatch_policy.md` — each step's verify block is a single shell assertion, not "consider checking".

---

## Step 0 — Empirical baseline + kill-switch

**Severity**: gate (no work proceeds without this). **Owner**: orchestrator (no helper, no agent).

### Why

Discipline rule (`project_research_patches_1_5_empirical_failed.md`): patches must replay-the-failure, not just be structurally pretty. Token-savings claim is currently unmeasured. If `src/CLAUDE.md` contains no isolable conditionally-loadable chunks, the plan is YAGNI.

### Files

None written. Pure measurement.

### Procedure

1. Tokenize `src/CLAUDE.md` (e.g. `python -c "import tiktoken; ..."` or any consistent counter — record the counter used).
2. Section the file by H2 headings. For each section, classify:
   - **Always** — applies to every consumer turn (e.g. "command spec single-responsibility").
   - **Path-scoped candidate** — applies only when certain file types touched (e.g. test-first rule applies only when `src/devforge/lib/**` or `.py` files in play).
   - **Domain-scoped candidate** — applies only when certain workflow active (e.g. audit format applies only when user asks for audit/review — NOT path-gateable, stays always-on).
3. Sum token counts in the **path-scoped candidate** bucket. Compute `(path_scoped_tokens / total_tokens) × 100`.
4. **Kill-switch**: if percentage < 15%, write the measurement into this plan's *Step 0 result* slot below, mark plan **ABORTED**, stop. Do not proceed to Step 1.

### Verify

```bash
# Re-run the same counter, confirm reproducibility:
python -c "import tiktoken; e = tiktoken.get_encoding('cl100k_base'); print(len(e.encode(open('src/CLAUDE.md').read())))"
# Categorization table committed to this plan as "Step 0 result" block (see below).
```

### Step 0 result (run 2026-05-24)

Counter: word-count proxy (`tiktoken` unavailable in env; ratio is what the kill-switch needs, not absolute tokens). `src/CLAUDE.md` = 3383 words / 306 lines, sectioned by H2:

| Section heading | Words | % | Classification |
|---|---|---|---|
| Workflow (command catalog + per-command detail) | 1656 | 49.0% | Always — command/domain-scoped, NOT path-gateable (a command fires regardless of which files are open) |
| Key Rules (Always/Never one-liners) | 317 | 9.4% | Partial path-scoped — ~half (Document new code / Lint everything / Handle both paths / Validate at boundaries / SOLID-DRY-KISS) is code-touch scoped |
| Artifact Storage | 307 | 9.1% | Always — reference |
| CBM-first Protocol Enforcement | 320 | 9.5% | Always — hook reference |
| Enforced Quality Gates | 268 | 7.9% | Always — task-boundary, not path |
| Session Continuity | 210 | 6.2% | Always |
| Commit Convention | 93 | 2.7% | Always — domain (committing), not path |
| Placeholder Convention | 81 | 2.4% | Always — meta |
| Project Overview/Structure/Dev/Arch/Agents/References | ~120 | ~3.5% | Always — placeholders + refs |

**Total**: 3383 words. **Path-scoped subtotal**: ≈ a slice of Key Rules ≈ **5–9%** (best case, the code-discipline one-liners). **Threshold**: 15%. **Decision: ABORT.** To reach 15% one would have to misclassify command-gated Workflow content as path-gated, which Step 0's own procedure (line 59: domain-scoped stays always-on) forbids.

### Abort rationale (2026-05-24)

Two independent findings, either of which is sufficient to abort:

1. **Premise false.** Plan line 18 asserts `src/CLAUDE.md` "packs every discipline rule (audit format, default-argue, test-first, sentence-level hallucination check, cross-check, helper-owns-shape)." It does not, and a `git show` of the file at the nearest draft-time commit (`8eebb69`, 2026-05-15) confirms it never did — zero discipline keywords, identical 14 sections. Those rules live in the **repo-root forge-internal `CLAUDE.md`**, which (a) the plan marks explicitly out of scope (line 25) and (b) governs forge *development* of `src/`, not the consumer overlay that spawns into target projects. The author conflated the two files at drafting time.

2. **Mechanism is the wrong tool for the real cost.** Investigation via `claude-code-guide` (2026-05-24, three queries, docs.claude.com) established the consumer-side always-on/​on-invocation model:
   - In a spawned project the only always-on surface is the emitted `CLAUDE.md` (+ `.claude/rules/`). `.claude/commands/*.md` bodies load **only on invocation**.
   - Custom commands are **merged into skills**; the model normally sees each command's `description` frontmatter always-on for awareness — **EXCEPT** when `disable-model-invocation: true`, which sets *"Description not in context"* (docs table, code.claude.com/docs/en/skills). Every forge command sets `disable-model-invocation: true` (deliberate manual-only / full-user-control stance).
   - Consequence: the command catalog in `CLAUDE.md` is **load-bearing** (the only thing telling the model the commands exist), and the genuine always-on bloat is the **deep phase-by-phase per-command paragraphs** (research 170w / discover 268w / specify 299w) that duplicate the on-invocation command body. That is fixed by **trimming/deleting** those paragraphs to purpose one-liners — not by path-scoped `.claude/rules/`. The mechanism this plan proposes does not address the real cost.

**Successor**: `08-CLAUDE-MD-COMMAND-TRIM-PLAN.md` (phase-detail trim, deletion-only, ~20% always-on saving).

---

## Step 1 — Confirm Claude Code rules-file frontmatter schema

**Severity**: gate (Step 2 codifies what Step 1 confirms). **Owner**: orchestrator + `claude-code-guide` agent.

### Why

The 2026-05-20 `claude-code-guide` verification confirmed `.claude/rules/*.md` + `paths:` exists. It did **not** capture every valid frontmatter field, glob semantics (does `paths: ["**/*.py"]` cross directory boundaries the way we expect?), or interaction edges (what if two rules match — both load? merge? first-wins?). Step 2 emitter cannot be written safely without that.

### Files

None written. Investigation only.

### Procedure

Re-invoke `claude-code-guide` agent with a self-contained brief listing the four questions:

1. **Full frontmatter schema for `.claude/rules/*.md`**: every valid key, value types, defaults. Source URL required.
2. **Glob semantics for `paths:`**: case-sensitivity, `**/` recursion, negation, multiple patterns. Confirm with a doc citation.
3. **Multi-rule match behavior**: when two rules match the same conversation context, do both load? Is there ordering? Is there a token cap?
4. **Failure mode on older Claude Code versions**: what happens when a consumer's Claude Code binary predates rules support? Silent ignore? Error? (Drives Step 4 version-pin work.)

Record the answers as a `## Step 1 result` block appended to this plan.

### Verify

```bash
grep -A20 "^## Step 1 result" 06-CONDITIONAL-CONTEXT-PLAN.md  # answers persisted
```

---

## Step 2 — Add rules emitter

**Severity**: high (foundation for Step 3+). **Owner**: python-engineer + python-reviewer.

### Why

`scripts/emitters/claude.py` currently emits only commands (`.claude/commands/*.md` + references). It does not handle rules. The rules need a parallel emission path: read from a new `src/rules/` source tree, write to `target/.claude/rules/*.md`. `install.sh:145` `cp "$TEMPLATE_DIR/src/CLAUDE.md" "$TARGET_DIR/CLAUDE.md"` stays untouched — CLAUDE.md keeps its always-on portion; rules-files supplement.

### Files

- `src/rules/` — new authoring directory. Empty in this step; Step 3 lands the first file.
- `scripts/emitters/claude.py` — extend `emit()` with a `_emit_rules()` helper:
  - If `src / "rules"` exists and is a directory, iterate every `*.md` file.
  - Copy each to `target / ".claude" / "rules" / <name>`.
  - Print `"    {name} rule: yes ({scope})"` where `scope` is the `paths:` value parsed from frontmatter (or `"always"` if no `paths:` key) — print line confirms install.sh sees the emission.
- `tests/scripts/test_claude_emitter.py` — new tests:
  - Empty `src/rules/` → emitter prints nothing for rules, exits 0.
  - One `src/rules/foo.md` with frontmatter `paths: ["**/*.py"]` → target file exists at `.claude/rules/foo.md`, content byte-identical, emitter print line includes `paths: ["**/*.py"]`.
  - Two rules, one with frontmatter, one without → both copied, both print lines correct.
- `scripts/generate.sh` — verify it calls `claude.py emit()` (it should; emitter is the single entry). If it inlines a separate rules copy, remove duplication.
- `install.sh` — no change in this step (rules ship with the rest of `.claude/`).

### Verify

```bash
pytest tests/scripts/test_claude_emitter.py -v
# End-to-end smoke against testForge20:
./install.sh /tmp/testForge20-rules-smoke
ls /tmp/testForge20-rules-smoke/.claude/rules/  # empty dir or absent OK; Step 3 fills it
grep -n "_emit_rules\|src.*rules" scripts/emitters/claude.py  # function exists
```

### Argue

Alternatives considered:
- **Bake rules emission into `install.sh`** instead of `claude.py`. Rejected: install.sh is bash, harder to test, splits emission logic across two languages.
- **New separate emitter `scripts/emitters/rules.py`**. Rejected: rules are a Claude-Code-specific runtime artifact; belongs alongside commands in `claude.py`. Creating a new file just inflates the emitter dir.
- **Auto-discover all `src/rules/*.md`** without explicit `_PROMOTED`-style allowlist. Accepted (deviates from commands pattern): rules are append-only static text files, not multi-file structures with references. Risk of shipping a half-finished rule is lower than for commands; the cost of an allowlist is higher (every new rule needs two edits).

---

## Step 3 — Pilot: migrate the lowest-blast-radius rule

**Severity**: high (validates Step 2 + measures real token impact). **Owner**: orchestrator + instruction-author + instruction-reviewer.

### Why

Before migrating N rules, migrate ONE and measure. Pick the smallest, most path-scopable rule from Step 0's classification — likely the test-first rule (`feedback_test_first_python_helpers.md` content embedded in `src/CLAUDE.md`) because:
- Tight scope: `paths: ["**/*.py"]` (or specifically `["src/devforge/lib/**/*.py", "tests/lib/**/*.py"]`).
- Low risk: rule already exists in repo as a memory file; we know its phrasing is stable.
- Easy to test in consumer: open a `.py` file in testForge20, confirm rule loads; open a `.md` file, confirm it doesn't.

Other candidate rules wait until pilot succeeds.

### Files

- `src/rules/python-helper-test-first.md` — new file:
  ```yaml
  ---
  paths: ["**/*.py"]
  ---
  ```
  Body: ~30 lines verbatim from the `feedback_test_first_python_helpers.md` content currently inlined in `src/CLAUDE.md`. Edit for self-containment (no "see above" / "see §X" forward-refs that assume CLAUDE.md context).
- `src/CLAUDE.md` — remove the migrated section. Add a 1-line stub at the deletion point: `> Test-first discipline for python helpers is loaded conditionally via .claude/rules/python-helper-test-first.md when .py files are touched.` (LLM-readable pointer; not a forward-ref hallucination because the file shipped in Step 2 emitter.)
- `tests/scripts/test_claude_emitter.py` — extend pilot test: install into temp dir, assert `.claude/rules/python-helper-test-first.md` exists with the `paths:` frontmatter intact.

### Verify

```bash
pytest tests/scripts/test_claude_emitter.py -v
# Sentence-hallucination scan on the rule + the stub:
grep -n "see CLAUDE\|see §\|see above" src/rules/python-helper-test-first.md  # must be 0 matches
# Cross-check: no other doc still references the rule's old CLAUDE.md location:
grep -rn "CLAUDE.md.*test-first\|test-first.*CLAUDE.md" src/ tests/  # must be 0 matches
# Token delta:
wc -w src/CLAUDE.md  # confirm word count dropped by the migrated chunk
```

Empirical verify (manual; loop until clean):
1. `./install.sh /tmp/testForge20-pilot`.
2. Open a `.py` file in the consumer; ask Claude Code "what is the test-first rule for python helpers" → expected: cites the rule.
3. Open only a `.md` file; ask the same question → expected: cites no rule, or cites the always-on CLAUDE.md fallback.
4. If step 3 fails (rule loads anyway because of session cross-talk), re-invoke `claude-code-guide` agent for the failure mode + fix.

### Argue

Why not migrate everything in one step? Because if Step 1 missed a frontmatter edge case, fixing one file is a 10-minute revert; fixing 8 is a multi-hour rollback with consumer-overlay drift. The cost of one extra step is < the cost of partial-rollout corruption.

---

## Step 4 — Claude Code version-pin in `install.sh`

**Severity**: medium (without this, consumers on older Claude Code binaries get silent rule-non-load with zero warning, defeating the entire plan's purpose). **Owner**: python-engineer (install.sh shell + a small detection helper).

### Why

`claude-code-guide` (Step 1) answers what older Claude Code does when it sees an unknown frontmatter key. If the answer is "silent ignore" (most likely), consumers running old `claude` CLI will copy the rules files but never load them. The discipline gap is invisible. We need a hard gate.

### Files

- `install.sh` — add a pre-install check:
  ```bash
  # ── Verify Claude Code version supports .claude/rules/ ──
  if ! command -v claude >/dev/null 2>&1; then
      echo "warning: claude CLI not found in PATH; rules support cannot be verified" >&2
  else
      CLAUDE_VERSION=$(claude --version 2>/dev/null | head -1)
      # Minimum version threshold determined by Step 1 result.
      # Example: require >= 1.X.Y.
      # ... version comparison ...
      if [ <version_below_threshold> ]; then
          echo "error: claude CLI version $CLAUDE_VERSION predates .claude/rules/ support. Upgrade to >= X.Y.Z." >&2
          exit 1
      fi
  fi
  ```
  Exact threshold filled in from Step 1's answer.
- `tests/install/test_version_check.sh` — bash test (or pytest invoking bash) that mocks `claude --version` with old + new strings, asserts install exits 1 on old + 0 on new.
- `CLAUDE.md` (forge-internal, repo root) — add a one-line note under *Where to find what* that install.sh enforces a Claude Code minimum version for rules support.

### Verify

```bash
bash tests/install/test_version_check.sh
# Manual: install into testForge20 with a doctored old claude in PATH → exits 1
```

### Argue

Alternatives:
- **No version gate, rely on consumer noticing missing discipline**. Rejected: discipline failures are diffuse and slow to surface; a CI hook on a consumer wouldn't catch "the test-first rule never loaded".
- **Warn-but-continue instead of hard-fail**. Rejected: zero-escape-hatch policy. A warning at install time disappears into terminal scrollback; consumer ships with broken discipline forever.

---

## Step 5 — Migrate remaining path-scoped rules

**Severity**: medium (compounds Step 3's win). **Owner**: instruction-author + instruction-reviewer per file; orchestrator coordinates batch.

### Why

Pilot in Step 3 validated the pattern with one rule. Now move the rest of the path-scoped candidates from Step 0's table. Each rule = its own step-3-shaped sub-procedure: write the file with `paths:`, remove the migrated chunk from `src/CLAUDE.md`, leave a 1-line stub, run cross-check, run sentence-hallucination scan, run emitter test, manual testForge20 empirical.

### Files

One `src/rules/<name>.md` per migrated rule. Candidate list comes from Step 0 — do **not** prejudge it here; the empirical categorization decides.

### Verify

```bash
# After each migration:
pytest tests/scripts/test_claude_emitter.py -v
grep -rn "CLAUDE.md.*<rule-name>\|<rule-name>.*CLAUDE.md" src/ tests/  # 0 matches
wc -w src/CLAUDE.md  # word count dropped by each migration
# After all migrations:
wc -w src/CLAUDE.md  # confirm matches Step 0 prediction (within 5%)
```

Empirical: run `/research` or `/pr-review` end-to-end on testForge20 after each migration batch. Discipline rule must light up when its `paths:` matches; must not when it doesn't.

### Argue

Why batch rather than per-rule plan? Each migration is a mechanical apply of Step 3's pattern with a different file. A separate plan per rule = bureaucracy. But each migration is independently verifiable and revertible — landing them as individual commits on `develop-2.0-init` preserves bisect.

---

## Step 6 — testForge20 end-to-end empirical replay

**Severity**: gate (project_research_patches_1_5_empirical_failed.md — patches that score below baseline get rolled back). **Owner**: orchestrator + testForge20 fixture.

### Why

Plans land only after end-to-end consumer-side empirical replay confirms no regression. Specifically:
- Token cost per turn dropped by the predicted Step 0 percentage (measure on a multi-turn session).
- No discipline rule failed to load when it should have (sample N=3 sessions across `.py`, `.md`, and mixed-file work).
- No discipline rule loaded when it shouldn't have (token bloat regression).

### Files

None written. Pure execution.

### Procedure

1. Fresh `./install.sh /tmp/testForge20-final`.
2. Run 3 representative consumer workflows (full sessions, not single-shot prompts):
   - A python-helper work session in `src/devforge/lib/_pr_review/` — assert path-scoped python rule loaded.
   - A spec-edit session in `src/commands/research/main.md` — assert sentence-hallucination rule loaded (if migrated as path-scoped), python rule did NOT.
   - A mixed audit-style session — assert audit-format rule (always-on) loaded.
3. Compare per-turn token cost to a baseline session captured BEFORE Step 3 lands. Predicted Step 0 percentage must hold within ±10%.
4. If any of the three sessions show the wrong rule loaded / not loaded → roll back the offending migration commit, re-open Step 5 for that rule with a `# WONTFIX` note explaining why path-scoping doesn't work for it.

### Verify

```bash
# Captured token counts before/after stored in:
git log --grep "CONDITIONAL-CONTEXT" --format="%H %s"  # commit chain
# Plan's "## Step 6 result" block lists the 3 sessions + per-turn token delta.
```

---

## Step 7 — Doc updates + plan close-out

**Severity**: low (housekeeping; required for future-session coherence). **Owner**: instruction-author.

### Why

Per `feedback_preempt_future_hallucination.md`: a fresh future session will read `CLAUDE.md` + `DEVELOPMENT-STATUS.md` + `CHANGELOG.md` and form a mental model. The mental model must reflect rules-file emission as a normal forge artifact, not an undocumented one.

### Files

- `CLAUDE.md` (forge-internal repo root) — add row to *Where to find what* table: `Conditional-load rules | src/rules/<name>.md + scripts/emitters/claude.py _emit_rules()`.
- `DEVELOPMENT-STATUS.md` — add entry under the appropriate section noting `.claude/rules/` is now a runtime artifact emitted by forge, with version-pinned minimum Claude Code release.
- `CHANGELOG.md` — entry under `develop-2.0-init` noting the migration + the measured token reduction.
- This plan — append `## Step N result` blocks for Steps 0, 1, 3, 5 (post-batch), 6.
- Add memory `project_conditional_context_delivered.md` summarizing: token reduction achieved, rule list migrated, version threshold pinned, testForge20 replay outcome.

### Verify

```bash
grep -n "src/rules\|.claude/rules" CLAUDE.md DEVELOPMENT-STATUS.md CHANGELOG.md  # all three updated
ls .claude/projects/-Users-mykolakudlyk-Projects-ai-dev-team-forge/memory/project_conditional_context_delivered.md  # memory landed
```

---

## When resuming work

Read in order:
1. *Context for next session* block above.
2. *Step 0 result* block — if it exists and decision = abort, the plan is dead; do nothing further.
3. *Step 1 result* block — frontmatter schema authority for any later edits.
4. The most recent `## Step N result` block to find the resume point.
5. `git log --grep "CONDITIONAL-CONTEXT"` for landed commits.

Do NOT re-derive Steps 0 or 1; their results are load-bearing for every downstream step.

## Out of scope (explicit deferrals)

- **CLAUDE.md `@path` imports** (Kiro idea 2 from the 2026-05-20 comparison). Easy 1-line wins (e.g. `src/constitution.md` reference) — handle in a separate small-edit pass alongside the next CLAUDE.md touch. Not standalone plan-worthy.
- **Agent-level conditional gating**. Claude Code doesn't support it; not building hook workarounds.
- **Forge-internal `CLAUDE.md` reorg** (repo root, 154 lines). Read by forge maintainers only; deferred.
- **Skills as an alternate venue for path-scoped content**. Skills support `paths:` too, but forge owns commands not skills; introducing skills mid-plan would expand scope without benefit.

## Dependencies

Queue this plan **after**:
- `04-PR-REVIEW-PLAN.md` (Step 12 testForge20 validation stop) — same testForge20 fixture; serializing avoids fixture state contention.
- `RESEARCH-HANDOFF-PLAN.md` (Step 10 manual verify) — same reason.

No blocker on `COMMAND-VERIFY-GATES-PLAN.md` or `CONSTITUTION-DRIFT-DETECTOR-PLAN.md` — those touch different surfaces.
