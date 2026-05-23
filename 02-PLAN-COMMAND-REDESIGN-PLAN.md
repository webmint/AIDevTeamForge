# PLAN-COMMAND-REDESIGN-PLAN

**Status**: SHIPPED, PARITY-PENDING (2026-05-23) — all code/spec work done + committed on `develop-2.0-init` (8 commits, head `fa8d9ca`). `/plan` ports the v2 shape + helper (8 verbs, 84 tests) + re-scoped architect + emitter/install + upstream-handoff consumption. Two items open by design:
- **Step 6 (parity 4-run)** — user-driven offline; needs testForge20 re-install first (Step-5 install predates Step-7 wirings), then 4 `plan.md` outputs handed back for the variance verdict. This is the last gate to call plan-02 fully complete.
- **Step 7.7 (render-findings reads structured `spec_seeds` vs re-parse `spec.md`)** — DEFERRED as YAGNI; spec.md parse works, pick up only if re-parse fragility is observed.

Per-step state: Steps 1-5 ✅ · Step 7 core 7.1-7.6 ✅ · 7.7 ⏸ deferred · Step 6 ⏸ parity-pending (user-offline) · **Step 8 ✅ SHIPPED 2026-05-23** (orchestrator-mediated specialist consultation — latent-bug fix: architect emits consultation requests, orchestrator invokes specialists incl. FE/BE, controlled-shape Specialist Consultation block) · **Step 9 ⏸ DRAFTED-NOT-STARTED** (plan→breakdown structured handoff, producer-side now per "consumer obeys producer"; `/breakdown` consumer pending).
**Date**: 2026-05-15 (status updated 2026-05-23)
**Branch**: `develop-2.0-init`
**Owner**: orchestrator (Claude) + user

## Context for next session

`/plan` exists today only in the legacy reference project `<reference-project>/.claude/commands/plan.md` (v2, 15.3 KB). It has NOT been ported into the forge template tree (`src/commands/`). The forge ships an architect agent template (`src/agents/architect.md`, 10.1 KB) that claims `/plan` ownership in its prose, but no actual `/plan` slash command spec exists under `src/commands/`.

This plan ports `/plan` into the forge as a templated command spec, builds the supporting Python helper, makes it consume the `/specify` output (most-recent `specs/NNN-*/spec.md` with user confirmation), and re-scopes the architect agent so the two artifacts don't contradict each other.

**Update 2026-05-22 — `/plan` now has TWO inputs, not one.** Steps 1–6 were written before the pipeline-handoff layers shipped. `/plan` still reads `spec.md` (WHAT/WHERE), but also auto-discovers the sibling `specs/NNN/handoff.json` `/specify` writes (`spec_seeds` + a `provenance` pointer to the originating research/discover handoff, which carries the HOW-extraction `plan_seeds`). **Step 7** builds that consumer half + wires the two downstream verbs `/specify` ships for `/plan` (`check-spec`, `resolve-open-question`). Read Step 7 before touching Phase 0 of the command spec.

### Source-of-truth context (must preserve)

`reference-project/.claude/commands/plan.md` is the canonical `/plan` shape. Per the parity-test notes in Obsidian (`20 Projects/AIDevTeamForge/parityTest/`), this command was optimized through a v1→v2 patch sequence that dropped mean pairwise variance from ~11% to ~4.4–5% across 4-run replays. **v3 regressed and was reverted** — `the reference project`'s on-disk copy is v2 and is load-bearing.

The four v2 patches that any port MUST preserve verbatim:

1. **Patch 1 — Context7 binding (Phase 0 Step 3)**: when the spec names a specific library, Context7 (`resolve-library-id` → `query-docs`) is the required first call, not WebSearch. Fallback to WebSearch only when Context7 returns nothing or is unavailable, and document the fallback reason.
2. **Patch 2 — Research output rule (Phase 0)** — **HIGHEST-LEVERAGE patch.** When 1+ signals detected, EITHER generate `specs/[feature]/research.md` OR cite an existing `research/*.md` with quoted findings (2–3 specific quotes proving the file was read). No third path. This is what collapsed 6/7 JUDGMENT divergences across the 4-run replay.
3. **Patch 3 — Phase 1.5 "Findings from Spec"**: required intermediate output enumerating every spec §3/§4/§5/§6/§7/§8/§9 bullet to the conversation BEFORE writing plan tables. Same load-bearing pattern as `/specify` Phase 1.5.
4. **Patch 4 — MODE disambiguation (Phase 3, User Approval)**: auto vs interactive paths; uncertain → prefer interactive.

### Anti-patterns (DO NOT reintroduce — v3 regression)

- Mandatory `research/` inventory procedure → bloated plans by 20–40%, introduced new path-glob fork.
- Prose-only Draft-status warning rule → fires 1/4 runs, same as no patch. "Soft mode-detection rules don't bind reliably even when made explicit."
- More procedural rules → "More instructions = more interpretation room. Anchor patches > procedural patches."

### Aligned decisions (user-confirmed 2026-05-15)

- **Spec resolution**: auto-pick most-recent `specs/NNN-*/spec.md` by mtime, then user-confirm via AskUserQuestion (`yes / pick-other / cancel`). `$ARGUMENTS` overrides auto-pick.
- **Status flip**: `/plan` flips spec `Status: Draft → Approved` on first run. The act of invoking `/plan` IS approval. Hard structural rule, replaces the parity-flagged unreliable prose check.
- **Helper**: `.devforge/lib/plan_helper` (Python, mirrors `specify_helper` shape). Helper owns structural emission; LLM composes values.

### Ordering rationale (argued + confirmed)

`/plan` command spec first, architect agent re-scope second. Reasoning:

- Contract flows command → agent (command is the user-facing entry; agent is consumed). Command shape drives agent shape.
- Forge's templated architect.md currently claims `/plan` ownership ("You own `/plan` and `/breakdown`") — this directly conflicts with the reference project's command-driven shape. Doing architect first would lock a contract the /plan port must undo.
- Parity test concluded: "Anchor patches > procedural patches." Command-driven orchestration is the anchor; pushing logic INTO architect erodes anchors that drove variance from 11% → 4.4%.

---

## Steps

Each step leaves the framework in a buildable, verifiable state. **Verify** criteria are concrete commands or grep checks that must pass before moving to the next step.

### Step 1 — Port `/plan` command spec from the reference project to forge template tree

**Goal**: create `src/commands/plan/main.md` + `src/commands/plan/references/*.md` carrying the v2 shape, parameterized with `{{PLACEHOLDERS}}` for multi-stack templating.

**Tasks**:
1.1 Create `src/commands/plan/` directory.
1.2 Copy `reference-project/.claude/commands/plan.md` → `src/commands/plan/main.md`.
1.3 Parameterize hard-coded references for portability:
   - Path examples mentioning `module` → `{{PROJECT_ROOT}}` or per-package references using the `## Packages` table convention from `src/CLAUDE.md`.
   - Documentation impact table rows with concrete `docs/module/...` paths → generic `docs/<package>/<concern>.md` placeholders matching `/generate-docs` output layout.
   - Constitution Section 7 references stay as-is (constitution.md is a per-project artifact, so the reference is generic).
1.4 Add forge-specific Workflow context block at top (mirrors `/specify/main.md` prelude):
   - Reference the 4-command setup gate (`/init-forge → /generate-docs → /configure → /constitute`).
   - State that `/plan` consumes `/specify` output and produces `specs/NNN-feature/plan.md`.
   - State the manual handoff to `/breakdown` (no automated dispatch).
1.5 Replace Phase 0 Prerequisites prose ("If status is still Draft, stop and inform the user") with the structural status-flip rule (see Step 2.4 — helper-driven).
1.6 Replace `$ARGUMENTS` "most recently modified feature" wording with the explicit auto-pick + confirm flow (see Step 2.3 — helper-driven).
1.7 Verbatim-preserve the four load-bearing v2 patch passages (Phase 0 Step 3 Context7 binding; Phase 0 Research Output Rule; Phase 1.5 Findings from Spec; Phase 3 MODE disambiguation).

**Verify**:
- `ls src/commands/plan/main.md` returns the file.
- `grep -c "Context7" src/commands/plan/main.md` ≥ 2 (Phase 0 Step 3 + Rationale).
- `grep -c "Findings from Spec" src/commands/plan/main.md` ≥ 1 (Phase 1.5 heading present).
- `grep -c "Research Output Rule" src/commands/plan/main.md` ≥ 1 (Patch 2 heading present).
- `grep -c "auto mode\|interactive mode" src/commands/plan/main.md` ≥ 2 (Phase 3 mode disambiguation).
- `grep -c "module" src/commands/plan/main.md` == 0 (no project-specific paths leak through).
- Spawn `instruction-reviewer` agent on the file: must return no logical-flow / hallucination findings.

### Step 2 — Build `.devforge/lib/plan_helper` (Python, test-first)

**Goal**: helper-owns-shape support. Mirror `specify_helper` patterns from `src/devforge/lib/`.

**Tasks** (each function = test in same turn per `feedback_test_first_python_helpers`):

2.1 `pick-spec [path]` — resolve which spec to plan against.
   - Arg given → validate the path exists, has the 9-section shape (`## 1. Overview` ... `## 9. Risks` headings present), return its directory + parsed frontmatter fields (Date, Status, Spec type).
   - No arg → glob `specs/*/spec.md`, pick highest mtime, return same payload.
   - No specs found → exit 2 with stderr "no spec found under specs/; run /specify first".

2.2 `render-pick-summary <spec-path>` — deterministic 4-bullet block for AskUserQuestion preview.
   - Lines: `**Spec**: specs/NNN-name/spec.md`, `**Type**: <Spec type>`, `**AC count**: N criteria across M subsections`, `**Status**: Draft|Approved|Complete`, `**Last modified**: <ISO date>`.
   - Stdout is the verbatim block the LLM copies into the user-facing turn.

2.3 `list-specs` — for the `pick-other` branch.
   - Glob `specs/*/spec.md`, sort by mtime desc, emit one line per spec with index + path + Status + AC count.

2.4 `check-status-and-flip <spec-path>` — structural Draft→Approved flip.
   - If `**Status**: Draft` → rewrite line to `**Status**: Approved` in place, return `flipped` on stdout.
   - If `**Status**: Approved` → return `already-approved`.
   - If `**Status**: Complete` → return `complete` (LLM will warn user but proceed).
   - If no Status line → insert `**Status**: Approved` under the `**Date**:` line, return `inserted`.
   - All paths exit 0; LLM uses the stdout token to compose the user message.

2.5 `render-findings-from-spec <spec-path>` — Phase 1.5 skeleton.
   - Parse the spec's §3 Desired Behavior bullets, §4 Affected Areas table rows, §5 AC subsections (5.1–5.7), §6 OOS bullets, §7 Constraints bullets, §8 Open Questions bullets, §9 Risks table rows.
   - Emit the section template with bullet stubs that include identifying refs (e.g., `- §4 row 1: <Area name> → <Files>: [PLAN COVERAGE: ?]`). LLM fills coverage decisions; helper owns the bullet count + identifiers.

2.6 `render-breakdown-handoff <spec-path> <plan-path>` — Phase 4 (new) manual handoff block.
   - Deterministic block: `## Manual next step — run /breakdown`, embedded literal `/breakdown specs/NNN-feature/plan.md`, plan-status (Draft → flipped by `/breakdown` on first run, same pattern), AC count, file-impact count, risk count.
   - Mirror `specify_helper render-plan-handoff` shape — same restart-Claude-Code instruction.

**Verify** (each task):
- New file `src/devforge/lib/plan_helper.py` exists with the six subcommands as a Click/argparse CLI.
- New file `tests/lib/test_plan_helper.py` exists with one test per subcommand minimum, each round-tripping via a real `specify_helper`-rendered spec (per `feedback_test_first_python_helpers` — no hand-authored fixtures).
- `cd src/devforge && pytest ../../tests/lib/test_plan_helper.py -v` → all green.
- Run `python -m devforge.lib.plan_helper pick-spec` with no specs present → exits 2, stderr matches "no spec found".
- Run `pick-spec` with a synthetic `specs/001-test/spec.md` (rendered via `specify_helper`) → exits 0, stdout names the path.
- Run `check-status-and-flip` against a Draft spec → file mutates to `**Status**: Approved`, stdout reads `flipped`.
- Run `render-findings-from-spec` on `specs/008-sample-feature/spec.md` (port the fixture from the reference project into a test fixtures dir) → output enumerates all 13 ACs from §5 + all 7 OOS bullets from §6 + all 6 risks from §9.

### Step 3 — Wire helper subcommands into `src/commands/plan/main.md`

**Goal**: replace prose-driven steps from Step 1 with helper invocations. Helper owns shape; spec text composes values.

**Tasks**:
3.1 Phase 0a (NEW) — Spec resolution:
   - Replace the `$ARGUMENTS — Path to a spec file ... If empty, use the most recently modified feature` wording with a concrete subcommand sequence:
     ```bash
     .devforge/lib/plan_helper pick-spec $ARGUMENTS
     .devforge/lib/plan_helper render-pick-summary <picked-path>
     ```
   - LLM: emit the rendered summary as a fenced block, then AskUserQuestion `"Process this spec?"` options `["yes", "pick-other", "cancel"]`.
   - On `pick-other` → run `list-specs`, present numbered list, AskUserQuestion to pick.
   - On `cancel` → end turn.

3.2 Phase 0b (NEW) — Status flip:
   - `.devforge/lib/plan_helper check-status-and-flip <picked-path>`
   - LLM: surface the flip result to the user in one line (`Spec status: Draft → Approved (implicit approval via /plan invocation).`).

3.3 Phase 1.5 — replace the literal table skeleton in the spec with:
   - `.devforge/lib/plan_helper render-findings-from-spec <picked-path>`
   - LLM: copy stdout VERBATIM into the conversation as a fenced block, then fill in the `[PLAN COVERAGE: ?]` decisions inline. Spec text retains the existing prose explaining purpose and the "skipping/compressing this step is a hard error" rule.

3.4 Phase 4 (NEW) — Manual handoff:
   - After Phase 3 approval, run `.devforge/lib/plan_helper render-breakdown-handoff <picked-path> <plan-path>`.
   - LLM copies stdout verbatim as a fenced block. Mirrors `/specify` Phase 5.4 exactly.

3.5 Preserve verbatim the four load-bearing patches (Patches 1–4 above). Do NOT rewrite them with helper calls — they are anchor-prose, not procedural prose. The helper-owns-shape principle applies to STRUCTURAL output (skeletons, summaries, handoffs), not to anchoring rules.

**Verify**:
- `grep "plan_helper" src/commands/plan/main.md | wc -l` ≥ 5 (the five subcommand invocations).
- `grep -c "Context7" src/commands/plan/main.md` still ≥ 2 (load-bearing prose intact after rewiring).
- `grep -c "Research Output Rule" src/commands/plan/main.md` still ≥ 1.
- Spawn `instruction-author` agent + `instruction-reviewer` agent in parallel on the file; both must clear before move-on.
- Run command-spec hallucination check (`feedback_sentence_level_hallucination_check_specs`): every sentence verifiable now / mechanically true / explicit forward ref.

### Step 4 — Architect agent re-scope

**Status**: APPLIED 2026-05-23 on `develop-2.0-init` (untracked). Reconciled framing (user-confirmed): architect = "decision authority for architectural choices, INVOKED BY `/plan` and `/breakdown`; orchestrator runs the commands." Not a pure ownership-strip — "decision authority" retained per the active rule (`memory/project_architect_role_scope`) + the shipped main.md mandatory-invocation hooks. Landed via `claude-code-guide` (convention: command names belong in body, not the `description` field) → `instruction-author` → `instruction-reviewer` iterative loop (2 apply iters; F1 dangling `breakdown.md` ref + a bare-`MEMORY.md` path nit fixed; clean). Final: `You own`=0; `/plan`+`/breakdown`=5 refs, all invoked-by framing; `description` carries no command names.

**Goal**: align forge's `src/agents/architect.md` with the command-driven `/plan` shape. Strip command-ownership prose; keep director-role + synthesis-rule framing for specialist-consultation invocations.

**Tasks**:
4.1 Read current `src/agents/architect.md`. Identify all passages claiming command ownership:
   - Frontmatter description: "decision authority for `/plan` and `/breakdown`".
   - "## Role & Boundaries" → "**You own:** `/plan` — translating...", "**You own:** `/breakdown` — turning...".
   - "Rules" → "2. **You own /plan and /breakdown.** Reject invocations..."

4.2 Rewrite as **consultable specialist invoked by `/plan` and `/breakdown`** when those commands need domain-decision depth (multi-package boundary, cross-stack pattern choice, ambiguous layer assignment). Architect does NOT own the commands themselves; the orchestrator (LLM following the command spec) does.

4.3 Retain verbatim:
   - Multi-stack `## Packages` table guidance (`src/CLAUDE.md` is authoritative for monorepos).
   - Specialist consultation matrix (security-reviewer, db-engineer, etc. — when to consult).
   - Synthesis rule (NEVER rubber-stamp; accepted / modified / rejected framing).
   - Termination rule (always decide; never bounce to asker).
   - Never-consult-the-asker rule (loop prevention).
   - Output Format for Decisions block.

4.4 Rewrite the "If asked to implement" refusal-and-route language — currently routes "for this task, direct it to [specialist-name]". Keep this; it's correct. But add a parallel rule: "If asked to OWN a slash command run, refuse and route to the command spec — architect is invoked by commands, not the inverse."

4.5 Verify via `claude-code-guide` agent (per `feedback_claude_code_authoring_best_practices`): is "consultable agent invoked by a slash command" a valid Claude Code pattern? What's the canonical wording? Apply the agent's findings before writing.

**Verify**:
- `grep -c "You own" src/agents/architect.md` == 0 (ownership prose stripped).
- `grep -c "consult\|specialist\|synthes" src/agents/architect.md` ≥ 5 (consultation framing retained).
- `grep -c "/plan\|/breakdown" src/agents/architect.md` ≤ 5 (mentions limited to "invoked by" / "do NOT own" / "refuse to run" context, NOT "owned by"). Ceiling raised from initial estimate of ≤3 to ≤5 during execution — the description-examples + invocation-list + refusal-list + refusal-example + Rule-2 prescriptions land at 5 mentions; all five are in the correct framing.
- Spawn `instruction-reviewer` on `src/agents/architect.md`: no logical-flow / hallucination findings.
- Cross-check: does `src/commands/plan/main.md` (post-Step 3) reference the architect agent? If yes, verify the reference is "consult-when-needed", not "dispatch-to-own".

### Step 5 — Emitter + install verification

**Status**: 5.1–5.3 DONE 2026-05-23. `"plan"` added to `scripts/emitters/claude.py` `_PROMOTED` (after `"specify"`). `install.sh /Users/mykolakudlyk/Projects/testForge20` exits 0 — emits `plan command: yes (folder, 0 references)`. Verified in target: `.claude/commands/plan.md` (26.2K, 0 `{{` leaks), `.devforge/lib/plan_helper` shim + `plan_helper.py` (`--help` lists all 6 subcommands; `pick-spec` with no specs → exit 2 per Step 2.1), `.claude/agents/architect.md` re-scoped (`You own`=0). **5.4 (full `/plan` command boot against a synthetic approved spec) = user-side manual e2e** — orchestrator cannot run a fresh Claude Code session; pending like other plans' testForge20 e2e stops. **Pre-existing blocker cleared:** install aborted on a stray untracked `src/devforge/init.yaml` (null helper-state leaked into source tree) — removed (untracked, guard-flagged); unrelated to this step.

**Goal**: get `/plan` installed end-to-end into a target project. Per `feedback_emitter_promoted_cross_check`, `src/commands/plan/` MUST be added to `scripts/emitters/claude.py` `_PROMOTED` list AND verified via install.

**Tasks**:
5.1 Edit `scripts/emitters/claude.py`: add `"plan"` to `_PROMOTED`.
5.2 Run `bash install.sh` against `~/Projects/testForge20` (or a fresh test target).
5.3 Verify:
   - `~/Projects/testForge20/.claude/commands/plan.md` exists with substituted placeholders.
   - `~/Projects/testForge20/.devforge/lib/plan_helper` is installed and executable.
   - `~/Projects/testForge20/.claude/agents/architect.md` exists with re-scoped wording.
5.4 In testForge20, invoke `/plan` against a synthetic approved spec — confirm the command boots, picks the spec, runs the status flip, emits Phase 1.5 findings skeleton, and stops at the Phase 3 approval gate.

**Verify**:
- `bash install.sh` exits 0.
- `diff` of installed `plan.md` vs `src/commands/plan/main.md` shows only `{{PLACEHOLDER}}` substitutions (no spurious changes).
- Synthetic `/plan` run produces a Phase 1.5 findings block that enumerates every section of the synthetic spec.

### Step 6 — Empirical parity check (PARTIAL: prep complete, 4-run gate open)

**Goal**: confirm the redesigned `/plan` does not regress below the 4.4–5% mean variance baseline established by the reference project v2.

**Sandbox decision (2026-05-15)**: `testParity` has old/incomplete setup (no `init.yaml`/`configure.yaml` from the new 4-command chain). Re-using `testForge20` instead — it already passed Step 5 install + helper smoke and has the full setup chain populated.

**Fixture decision (2026-05-15)**: parity target is the reference project 008 spec (`008-sample-feature`) plus its referenced research doc (`2026-04-30-sample-research.md`). This is the EXACT spec the v2 baseline was measured against — best apples-to-apples comparison.

**Staged in testForge20** (2026-05-15):
- `specs/008-sample-feature/spec.md` (18.6KB, 22 ACs across 7 subsections, Status flipped to Draft so Phase 0b structural flip exercises uniformly across all 4 runs).
- `research/2026-04-30-sample-research.md` (8.8KB — exercises Patch 2 skip-with-reference path).
- testForge20's `/plan` + `plan_helper` + re-scoped architect agent all installed and Step-5-smoke-tested.

**4-run procedure** (user-driven — orchestrator cannot run 4 clean Claude Code sessions from inside one):

For each run (N=1..4):
1. Open Claude Code in `~/Projects/testForge20` (fresh session boot — `/clear` is NOT enough; quit + relaunch).
2. Run: `/plan specs/008-sample-feature/spec.md`
3. Walk Phase 0a confirmation → Phase 0b status flip (helper-driven) → Phase 0 Research Eval → Phase 1.5 Findings → Phase 1 Tech Design → Phase 2 Plan rendering → Phase 2.5 cross-check → Phase 3 approval gate.
4. **At Phase 3 approval gate**: select `cancel`. The rendered `specs/008-sample-feature/plan.md` is the parity artifact. (Phase 4 handoff block is deterministic helper output; cancelling skips it without affecting variance measurement.)
5. Save: `cp specs/008-sample-feature/plan.md /tmp/plan-run-N.md` (N=1,2,3,4).
6. **Reset between runs**: `sed -i.bak 's/^\*\*Status\*\*: Approved$/\*\*Status\*\*: Draft/' specs/008-sample-feature/spec.md && rm specs/008-sample-feature/spec.md.bak && rm specs/008-sample-feature/plan.md`

**Diff variance computation** (orchestrator-driven after the user provides the 4 plan.md outputs):
- 6 pairwise comparisons: (1,2), (1,3), (1,4), (2,3), (2,4), (3,4).
- Per pair: token-level diff ratio per Obsidian `20 Projects/AIDevTeamForge/parityTest/Methodology - per-command deviation measurement.md`.
- Mean across 6 pairs is the parity metric.

**Verify**:
- Mean pairwise variance ≤ 7% (parity-test stop condition).
- If ≤ 5% (matches v2 baseline) → ship.
- If 5–7% → investigate single highest-deviation pair; if cause is the new helper-driven sections (skeleton or handoff) showing legitimate determinism variance, ship; if cause is removed anchor prose, restore the anchor.
- If > 7% → STOP, revert helper rewiring (Step 3), keep prose-only port (Step 1 output). Diagnose before re-attempting.

**Open**: the 4-run gate. User performs the 4 runs in testForge20 and provides resulting plan.md outputs back; orchestrator computes variance + emits verdict.

**Note (housekeeping)**: `~/Projects/testForge20/specs/001-config-menu-sort/spec.md` line 4 carries a stale `**Status**: Approved` from Step-5 helper smoke (auto-mode blocked cross-project Edit revert). Does NOT affect the 008 parity run (the 008 spec is the explicit parity target). Manual one-line revert if user wants the 001 spec back to Draft: change line 4 from `Approved` → `Draft`.

### Step 7 — Handoff consumption alignment (research → discover → specify → /plan)

**Status**: ADDED 2026-05-22. Plan Steps 1–6 were authored 2026-05-15, **before** the pipeline-handoff layers shipped (`03-DISCOVER-HANDOFF-PLAN.md` + the `/specify` rewrite). `/plan` now has TWO inputs, not one: the spec it always read, plus a structured handoff chain that carries the HOW-extraction (`project_research_how_extraction_queued`). This step builds the consumer half that `/specify` already names as "not yet wired."

**Progress**: 7.1–7.3 (core) SHIPPED 2026-05-23 (commit `a30c8e3` + cross-ref flip `2c2cad2`): `read-specify-handoff` + `render-plan-seeds` verbs (84 tests), Phase 0a.5 wiring. 7.4–7.6 SHIPPED 2026-05-23 (this batch, main.md only): Phase 0a.6 `check-spec` drift gate (handles `current`/`missing`/`drift`/`not-a-git-repo`), Phase 0 Step 3 anti-relitigation (Phase 1.3 stays unconditional), Phase 1.5 `resolve-open-question` wiring. Reviewed via instruction-author→instruction-reviewer loops (clean). **7.7 (render-findings-from-spec source reconciliation) DEFERRED** — requires helper code (read structured `spec_seeds` from the handoff vs re-parse `spec.md`) + tests; the current spec.md parse works, so this is a robustness refinement, not core. Pick up as its own python-engineer task if/when re-parse fragility is observed.

**Goal**: `/plan` auto-discovers and consumes the upstream handoff chain — `spec_seeds` (WHAT, via the specify-handoff) and `plan_seeds` (HOW, via the upstream research/discover handoff the specify-handoff points at) — and wires the two downstream verbs `/specify` ships for `/plan` to call (`check-spec` drift gate, `resolve-open-question`).

**Consumption contract (verified 2026-05-22 against shipped schemas)**:

```
research/discover handoff.json      → spec_seeds + plan_seeds   (HOW lives here)
        │ specify import-handoff consumes spec_seeds ONLY; plan_seeds passes through
        ▼
specs/NNN/handoff.json (specify)    → spec_seeds + provenance.upstream_handoff_path (pointer; NO plan_seeds)
        │ /plan reads THIS — deterministic sibling to spec.md
        ▼
specs/NNN/spec.md                   → WHAT/WHERE
```

- `/plan` reads the **sibling** `specs/NNN/handoff.json` (deterministic path — no reverse-glob). Schema: `src/devforge/lib/_specify/handoff_schema.py` (`Handoff.spec_seeds` + `Handoff.provenance`).
- The specify-handoff carries `provenance.upstream_handoff_path` / `upstream_handoff_kind` / `upstream_completed_at` — a pointer to the originating research/discover handoff. It does **NOT** forward `plan_seeds` (verified: 0 hits). HOW is a **second hop**: follow the pointer, read `plan_seeds` from the upstream handoff.
- The two handoff kinds have **divergent `plan_seeds` shapes** — research: `recommended_approach_id/summary` + `layer_destination/justification` + `complexity` + `alternatives_considered` + `proposed_call_shape` + `cited_canonical_patterns`; discover: `design_options` + `build_vs_buy` + `complexity` + `recommended_option_id` + `recommended_option_rationale` + `cited_canonical_patterns`. Any consumer verb MUST kind-dispatch (mirror `research_helper check-outcome`).
- Cold path: a spec authored without an upstream handoff (or by the pre-rewrite `/specify`) has `provenance.upstream_handoff_path == null` or no sibling handoff at all — `/plan` derives HOW itself, exactly as Steps 1–6 already describe.

**Tasks** (each helper function = test in same turn per `feedback_test_first_python_helpers`, round-tripping via real `specify_helper finalize-handoff` + `research_helper`/`discover_helper finalize-handoff` output — no hand-authored fixtures):

7.1 `plan_helper read-specify-handoff <spec-path>` — resolve the sibling `specs/NNN/handoff.json` next to the picked spec.
   - Present → parse, emit a deterministic block carrying `spec_seeds` presence summary + `provenance.upstream_handoff_path` (or `none`) + `upstream_handoff_kind`. Exit 0.
   - Absent (legacy/cold spec) → exit 0 with stdout token `no-handoff` (NOT an error — falls back to spec.md parse path).
   - Malformed/invalid JSON → exit 2, stderr names the file.

7.2 `plan_helper render-plan-seeds <specify-handoff-path>` — emit the HOW seed block.
   - Read the specify-handoff's `provenance.upstream_handoff_path`. Null → stdout token `cold-no-plan-seeds`, exit 0.
   - Non-null → open the upstream handoff, **kind-dispatch on `handoff_kind`** (research vs discover), render the deterministic HOW block (recommended approach/option + layer + complexity + alternatives/design-options + `proposed_call_shape` when present + cited canonical patterns). Helper owns the block shape; LLM composes the plan narrative from it.
   - Upstream pointer dangling (file gone) → exit 2, stderr names the missing path; LLM surfaces and proceeds cold.

7.3 main.md Phase 0a.5 (NEW, after `pick-spec`/confirm, before the Phase 0b status flip) — handoff discovery:
   - `.devforge/lib/plan_helper read-specify-handoff <picked-path>`.
   - On `no-handoff` → one-line note "No upstream handoff; planning cold from spec." Continue to existing Phase 0.
   - On present → `.devforge/lib/plan_helper render-plan-seeds <handoff-path>`; copy stdout VERBATIM into the conversation as a fenced block. The HOW seed feeds Phase 0 Research Eval (does plan_seeds already cite research?), Phase 1 Tech Design, and Phase 1.3 Architecture Decisions. On `cold-no-plan-seeds` → same cold note.

7.4 main.md Phase 0 — `check-spec` drift gate (`/specify` main.md:721 names `/plan` as a caller; verb lives in `cbm_sync_helper`, reads `.devforge/spec-stamps.jsonl`):
   - `.devforge/lib/cbm_sync_helper check-spec <picked-path>`.
   - `current` → proceed silently. `drift <a>..<b> <files>` → surface the changed §4-cited files, AskUserQuestion `["proceed", "cancel"]`. `missing` → one-line note, proceed. `not-a-git-repo` (exit 2) → advisory check unavailable, one-line note, proceed (non-git target must not block planning).

7.5 main.md — wire `resolve-open-question` (verb SHIPS at `_specify/_cmds_phase5.py:61`; `/specify` main.md:783 expects `/plan` to call it):
   - At the point `/plan` resolves a `/specify` §8 open question during planning, call `.devforge/lib/specify_helper resolve-open-question` with the resolution note + phase + timestamp. The resolution audit trail lives in specify-state; re-renders strike through the resolved entry.

7.6 Phase 0 Step 3 / plan_seeds reconciliation (anti-relitigation):
   - When `render-plan-seeds` supplied `alternatives_considered` (research) or `design_options` (discover), `/plan` SEEDS the Phase 0 Step 3 alternatives table from them rather than rediscovering. The mandatory architect invocation at Phase 0 Step 3 fires only when `/plan` introduces a NEW alternative not present in plan_seeds. Skip-with-seed must be recorded in the plan.md "Specialist Consultation" section (the single-source-of-truth for consultation provenance), citing the upstream handoff path.

7.7 `render-findings-from-spec` source reconciliation (Step 2.5):
   - Prefer the structured `spec_seeds` from the specify-handoff (already-parsed AC / affected-areas / OOS / risks) over re-parsing `spec.md` markdown when the sibling handoff is present. Fall back to the existing spec.md parse for legacy/cold specs. Identical bullet-count + identifier guarantees apply on both paths.

**Verify**:
- `src/devforge/lib/plan_helper` exposes `read-specify-handoff` + `render-plan-seeds`; `tests/lib/test_plan_helper.py` has ≥1 test each, round-tripped through a real `specify_helper finalize-handoff` output whose `provenance.upstream_handoff_path` points at both (a) a real `research_helper`-produced handoff and (b) a real `discover_helper`-produced handoff. All green.
- `render-plan-seeds` on a research-kind upstream emits `proposed_call_shape`/`alternatives_considered`; on a discover-kind upstream emits `design_options`/`build_vs_buy` — proves kind-dispatch.
- `render-plan-seeds` on a specify-handoff with `provenance.upstream_handoff_path == null` → stdout `cold-no-plan-seeds`, exit 0.
- `read-specify-handoff` on a spec with no sibling handoff → stdout `no-handoff`, exit 0.
- `grep -c "read-specify-handoff\|render-plan-seeds\|check-spec\|resolve-open-question" src/commands/plan/main.md` ≥ 4 (all four wirings present).
- `grep -c "Context7\|Research Output Rule" src/commands/plan/main.md` unchanged from Step 3 (load-bearing anchor prose intact after the Phase 0a.5 insert).
- Spawn `instruction-author` + `instruction-reviewer` in parallel on `src/commands/plan/main.md`; both clear.
- Cross-check: DONE 2026-05-23 (with the 7.1-7.3 core). Flipped the now-false "/plan's auto-discovery reader is not yet wired" claim at `/specify` main.md lines 19/773/781 → "auto-discovers"; also flipped the same claim in the helper string `_specify/_render.py` (+ its assertion in `test_specify_helper.py`), the consumer-overlay `src/CLAUDE.md` /specify entry, and the `CLAUDE.md` pipeline-handoff index row (NOT YET WIRED → WIRED). Historical "Shipped 2026-05-22" notes in `1.5-SPECIFY-PLAN-HANDOFF-PLAN.md` left as point-in-time record.

**Depends on**: Step 1+2+3 (the command + helper must exist). Independent of Step 4 (architect) and orthogonal to Step 6 (parity) — though a fresh parity run after Step 7 should re-baseline, since the Phase 0a.5 insert changes the rendered plan for handoff-seeded specs.

### Step 8 — Orchestrator-mediated specialist consultation (latent-bug fix + generalization)

**Status**: SHIPPED 2026-05-23. 8.1 (architect.md consultation = emit-request not invoke + no-relay fallback + Rule 4 fix), 8.2 (`/plan` Phase 1.3 relay loop + "Architect Consultation"→"Specialist Consultation" rename + render-consultation-block wiring), 8.3 (`plan_helper render-consultation-block` controlled-shape verb, headingless, 10 tests), 8.4 (cross-check: only architect.md had the bug). 94 plan_helper tests pass. Reviewed via claude-code-guide + python-engineer/-reviewer + instruction-author/-reviewer loops (clean).

**Trigger / root cause**: `claude-code-guide` confirmed (against docs.claude.com) that **subagents cannot spawn other subagents** — the Agent/Task tool is withheld from any agent running as a subagent, with no config override (*"prevents infinite nesting"*). Therefore `src/agents/architect.md`'s current "Consulting Specialists → How to consult: **invoke the specialist** with the sub-question" instructs an **impossible action** — the architect (a subagent) physically cannot invoke `db-engineer`/`security-reviewer`/etc. This is a latent correctness bug, not cosmetic.

**Goal**: make all specialist consultation **orchestrator-mediated** and **controlled-shape**. The `/plan` orchestrator (the LLM following main.md) is the only actor that can invoke specialists; the architect becomes a pure decision/synthesis function that *requests* consults rather than performing them. `/plan` may consult any planning-relevant agent for expertise: `architect` (synthesizer/decision-authority), `frontend-engineer` + `backend-engineer` (consulted for **layer feasibility / FE-BE patterns** — consulted for expertise, NEVER assigned implementation here; implementation is `/execute-task`'s job), `security-reviewer`, `db-engineer`, `migration-engineer`, `api-designer`, `performance-analyst`, `design-auditor`, `mobile-engineer`, `devops-engineer`, `qa-engineer`. The remaining four agents (`code-reviewer`, `runtime-debugger`, `tech-writer`, `ac-verifier`) are out of `/plan`'s consult scope — they serve later phases (review / verify / finalize), not planning.

**Tasks**:

8.1 **Fix `src/agents/architect.md` consultation model** (latent-bug fix; via `claude-code-guide` → `instruction-author` → `instruction-reviewer` loop):
   - Rewrite "Consulting Specialists → How to consult" from "invoke the specialist" → the architect **emits a structured consultation request** (named specialist + specific sub-question + the context the orchestrator needs) in its output; it does NOT invoke anyone.
   - Retain verbatim: the when-to-consult matrix (reframed as "flag these to the orchestrator"), the synthesis rule (architect synthesizes specialist input the **orchestrator relays back**), the termination rule, the never-consult-the-asker rule, the Output Format for Decisions.
   - Affirm: architect NEVER writes implementation code and is NEVER assigned implementation work (no "architecture implementation" carve-out — zero-escape-hatch).

8.2 **`/plan` orchestrator consultation loop** (`src/commands/plan/main.md`, Phase 1.3): define the relay — orchestrator invokes `architect` → architect returns decision + zero-or-more consultation requests → orchestrator invokes each named specialist with the architect's sub-question + context → orchestrator re-invokes `architect` with the specialists' input → architect synthesizes the final decision. Architect remains the decision-authority/synthesizer; the other specialists supply domain input only. The orchestrator may also consult a specialist directly when the command spec calls for it (not only on architect's request).

8.3 **Controlled-shape consultation records** (helper-owns-shape, per `feedback_helper_owns_shape_principle`): each consult is recorded in a fixed shape — `(specialist, sub-question, input-summary, accepted | modified | rejected, cites)`. Generalize the existing prose-only plan.md "Architect Consultation" section into a structured **"Specialist Consultation"** block. DESIGN CHOICE (confirm before building): emit the block skeleton via a `plan_helper` verb (helper-owns-shape, preferred) vs a hand-authored main.md template. Lean: helper verb (`render-consultation-block` or extend an existing one) so the structure is mechanically owned, not prose-enforced.

8.4 **Cross-check**: grep that no shipped agent/command file instructs a subagent to invoke another subagent (the same latent bug may exist in other `src/agents/*.md` consult sections — e.g. any agent whose prose says "invoke X agent"). Reconcile each to the orchestrator-mediated pattern or flag for its owning command.

**Verify**:
- `grep -c "invoke the specialist\|invoke .*agent" src/agents/architect.md` shows no instruction for the architect to spawn another agent.
- `src/commands/plan/main.md` Phase 1.3 defines the orchestrator-relay loop (architect request → orchestrator invokes specialist → re-feed → synthesis).
- Consultation records in plan.md follow the fixed `(specialist, sub-question, input, accepted/modified/rejected, cites)` shape.
- `instruction-author` + `instruction-reviewer` clear on both files; `claude-code-guide` consulted for the consultation-coordination convention.

**Depends on**: Step 1+3 (the command + main.md must exist — they do). Independent of Step 6/7. Touches `src/agents/architect.md` + `src/commands/plan/main.md` (+ possibly a new `plan_helper` verb for 8.3).

### Step 9 — plan → breakdown structured handoff (producer side)

**Status**: DRAFTED 2026-05-23. NOT STARTED. Decision (user): build the producer now — "consumer obeys producer." `/plan` defines the contract; the refactored `/breakdown` conforms. **Producer-only: `/breakdown` consumer is pending — no doc may claim a reader exists** (avoid the specify→plan stale-claim trap that `2c2cad2` cleaned up).

**Goal**: `/plan` emits a structured handoff carrying its decisions as breakdown-seeds, so the future `/breakdown` consumes structured data instead of re-parsing `plan.md`. Mirrors the specify→plan pattern (schema + finalize verb + atomic sibling-file write).

**Tasks** (test-first per `feedback_test_first_python_helpers`; via `python-engineer` → `python-reviewer` loop):

9.1 **Schema** (`src/devforge/lib/_plan/handoff_schema.py` or plan_helper-side): `Handoff` with `schema_version`, `handoff_kind = "plan"` (constant), `plan_path`, `plan_completed_at`, `provenance` (pointer back to the upstream specify-handoff), and `breakdown_seeds`. Design `breakdown_seeds` from the plan.md template (Layer Map, File Impact per-file action, Architecture Decisions, Risk Assessment) + the `src/_pending/commands/breakdown.md` draft so the contract anticipates what `/breakdown` needs to emit atomic tasks: layer map (area→layer), file impact (per file: create/modify/verify), architecture decisions, dependencies/ordering hints, AC→file mapping, risks, and the Step-8 controlled-shape specialist-consultation records.

9.2 **Producer verb** `plan_helper finalize-handoff` (mirror `specify_helper finalize-handoff`): reads the rendered `plan.md` (+ resolved spec/state), builds + validates the handoff, atomic-writes `specs/NNN-<feature>/plan-handoff.json` (sibling to `plan.md`; **separate filename** from specify's `handoff.json` — distinct `handoff_kind`s must not share a file). No status mutation. Tests round-trip via a real rendered `plan.md`.

9.3 **Wire main.md Phase 4**: on approval, call `finalize-handoff` to write `plan-handoff.json` and surface the path; **KEEP** the existing `render-breakdown-handoff` manual text block as the human bridge (the user still launches `/breakdown` manually). Both coexist: structured handoff for the future consumer + text block for the user now.

9.4 **Docs**: CLAUDE.md pipeline-handoff index gains a `plan → breakdown` row marked **producer-only, consumer pending**. Every mention says producer-side — never "wired".

**Verify**: schema + `finalize-handoff` verb + tests green; `specs/NNN/plan-handoff.json` written on `/plan` approval, validates against the schema; `grep` shows no doc claiming a `/breakdown` reader exists.

**Open design Qs**: (a) filename `plan-handoff.json` (recommended, separate from specify's `handoff.json`). (b) final `breakdown_seeds` field set — reconfirm against `/breakdown`'s real needs at its refactor (the producer contract may be revised then, which is fine — that is the consumer obeying, then negotiating).

**Consumer handshake (user, 2026-05-23)**: when `/breakdown`'s consumer is built, the user will **check this `/plan` producer side first** and align the consumer to whatever this producer emits (producer is the contract; consumer conforms, then any revision is negotiated from here).

**Depends on**: Step 1+3 (plan.md producer exists). Soft-dep Step 8 (consultation records feed `breakdown_seeds` — can stub if Step 8 lands later).

### Handoff status (note — not a step)

- **Inbound (specify → plan)**: WIRED 2026-05-23 (Step 7). `/plan` auto-discovers the sibling specify-handoff and consumes the upstream research/discover `plan_seeds`.
- **Outbound (plan → breakdown)**: today a **manual-next-step text block** only (`plan_helper render-breakdown-handoff`, Phase 4). A **structured `plan→breakdown handoff.json` will be built now (producer-side) — see Step 9.** Decision (user, 2026-05-23): "consumer obeys producer" — `/plan` defines the contract; `/breakdown` conforms to it when refactored. To avoid the stale-"reader exists" trap that bit specify→plan, the producer + every doc that mentions it must state explicitly **producer-side; `/breakdown` consumer pending** (NOT "wired").

---

## When resuming work

1. Read this plan top-to-bottom before touching code.
2. Check `git status` for `develop-2.0-init` — confirm working tree state matches `## Context for next session`.
3. Confirm the four load-bearing patches in `reference-project/.claude/commands/plan.md` are still intact (the reference project is the source-of-truth; if it drifted, sync before porting):
   ```bash
   grep -c "Context7\|Research Output Rule\|Findings from Spec\|MODE" <reference-project>/.claude/commands/plan.md
   ```
   Expect ≥ 4 hits.
4. Confirm Obsidian parity-test notes are unchanged at `20 Projects/AIDevTeamForge/parityTest/` (specifically: `Plan v2 4-run results - measured against predictions.md` and `Plan v2 reconfirmation - validates baseline at ~5%.md` are the load-bearing references).
5. Resume at the first Step whose **Verify** criteria are unmet.

## Out of scope (this plan)

- `/breakdown` port — separate plan. `/plan` redesign is a precondition (its Phase 4 handoff block targets `/breakdown`), but `/breakdown` itself stays in reference-project-only until a separate redesign cycle.
- Multi-spec planning (one `/plan` invocation covering N specs) — YAGNI; the existing one-spec-per-plan shape is the parity-validated contract.
- ~~`resolve-open-question` subcommand wiring (`/specify` Phase 5.4 references this for `/plan` to call when resolving §8 entries) — defer to a follow-up; current `/plan` v2 doesn't call it and parity holds.~~ **Superseded 2026-05-22 → IN SCOPE as Step 7.5.** The verb now ships (`_specify/_cmds_phase5.py:61`) and `/specify` main.md:783 names `/plan` as a caller.
- ~~`/plan` → architect agent dispatch automation — kept manual (LLM decides when to consult).~~ **Superseded 2026-05-16**: Plan F (`/plan` main.md + `architect.md` edits, this branch) introduces **targeted mandatory invocation at two named hooks** (Phase 1.3 every run; Phase 0 alternatives when 2+ compared) — not full dispatch automation. Discretionary consultation remains the policy outside those hooks. See `memory/project_architect_role_scope.md` for the active rule.

## Open questions

- **Q1**: Should `pick-spec` accept a partial feature name (e.g., `/plan sample-feature`) and fuzzy-match against `specs/NNN-*/`? Current Step 2.1 design accepts only exact paths. Recommendation: defer until user friction observed; exact paths are unambiguous.
- **Q2**: Should `check-status-and-flip` refuse to flip if the spec has any `[NEEDS CLARIFICATION]` markers from `/specify` Phase 1.5 accepted-partial-exit? Probable yes — running `/plan` against a spec with unresolved gaps undermines the contract. Recommend adding to Step 2.4 once the spec emission convention is finalized in `/specify`.
- **Q3** (RESOLVED 2026-05-22): Phase 4 handoff — should it call `resolve-open-question` for any `/specify` §8 entries this plan resolves? **Yes** — wired in Step 7.5. The verb ships at `_specify/_cmds_phase5.py:61` and `/specify` main.md:783 expects `/plan` to call it; `/plan` calls it at the point it resolves a §8 entry (not only at Phase 4).
- **Q4** (surfaced during Step 4 iter 3 review, 2026-05-15): `src/_pending/commands/_agent-assignment.md` and its 3 callers (`fix.md:167`, `refactor.md:161`, `breakdown.md:118`) currently fall back to the `architect` agent as an **implementation executor** for domain/shared/unclear code. This directly contradicts the Step-4 re-scope which states the architect "NEVER writes implementation code." All four files are in `src/_pending/` (not shipped). Resolution: deferred to port time for `/breakdown`, `/fix`, `/refactor` — when each is ported into `src/commands/<name>/main.md` (Step-1-style), reconcile the assignment table to fall back to `backend-engineer` (or appropriate generalist implementer), not `architect`. The architect remains consultable for decision sub-questions in those commands. Closing this Q is a precondition for each of those ports.
