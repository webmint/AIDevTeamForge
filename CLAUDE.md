# AIDevTeamForge

Spec-driven, agent-coordinated workflow framework for AI development. Generates Claude Code runtime files (`CLAUDE.md`, `.claude/agents/`, `.claude/commands/`) into target projects.

## Active work — read these before starting

When picking up work mid-stream, check the repo root for active plan files. **Read the relevant plan in full before making any changes** — plans encode multi-session context that isn't in the conversation.

Currently active (numbered = execution order):

- `01-CONSTITUTION-FORCING-FUNCTIONS-PLAN.md` — IN-FLIGHT 2026-05-22. Consumer-side family of mechanical detectors that back constitution rules LLMs systematically violate. **Phases 0+1+2+3+4+5a SHIPPED** on `develop-2.0-init` (Phase 0 substrate `ea18cd1`; Phase 1 magic-enum pilot `ccc25b8`; Phase 2 empirical-verify gate-relaxation decision `aae5a02` + `EMPIRICAL-VERIFY-MAGIC-ENUM-2026-05-21.md`; Phase 3 cross-layer `a370229`; Phase 4 any-leak `4b058da`; Phase 5a pre-commit hook template + `/constitute` Section 3.5 forcing-functions config-capture + Phase 6.4 hook opt-in prompt + `cmd_verify` `forcing_functions` block validation `f999a88`). **5b (`/execute-task` verify-gate) DEFERRED → ABSORBED INTO `07-EXECUTE-TASK-REDESIGN-PLAN.md` Phase 7** (do not implement here). **Phase 6 IN-FLIGHT** — docs propagation (`CHANGELOG.md` + repo-root `CLAUDE.md` + `src/constitution.md` §3.5/§3.6 cross-refs + `DEVELOPMENT-STATUS.md`) lands in the same commit as this update. Ships consumer-side via `.devforge/lib/constitute_helper` + `.devforge/templates/git-hooks/pre-commit-forcing-functions.sh`. Review-loop totals: Phase 0 = 4 iters / 9 findings; Phase 1 = 3 iters / 11 findings; Phase 3 = 4 iters / 8 findings; Phase 4 = 3 iters / 8 findings. 401 tests pass.
- `02-PLAN-COMMAND-REDESIGN-PLAN.md` — **Steps 1-5 + Step 7 (7.1-7.6) SHIPPED + COMMITTED 2026-05-23** on `develop-2.0-init` (7 commits, head `3e8ff48`). `/plan` slash command (`src/commands/plan/main.md`) + `plan_helper.py` (8 subcommands incl. `read-specify-handoff` + `render-plan-seeds`) + `test_plan_helper.py` (84 tests, synthetic "widget catalog" fixture rendered at test time via real `specify_helper render`). Step 4 architect re-scoped to invoked-by framing (`You own`=0). Step 5 emitter (`"plan"` in `_PROMOTED`) + testForge20 install verified. Step 7 = `/plan` consumes the upstream research/discover handoff chain (Phase 0a.5 auto-discovers sibling specify-handoff → follows provenance → renders upstream `plan_seeds`), plus Phase 0a.6 `check-spec` drift gate, Phase 0 Step 3 anti-relitigation, Phase 1.5 `resolve-open-question` wiring. All landed via python-engineer/-reviewer + instruction-author/-reviewer loops (clean). **Remaining: 7.7 (render-findings reads structured `spec_seeds` vs re-parse `spec.md`) DEFERRED as YAGNI (spec.md parse works; pick up only if re-parse fragility observed); Step 6 parity 4-run = user-driven offline (needs testForge20 re-install first, since Step-5 install predates the Step-7 wirings).** Gates THREE-LAYER Gap B+C (now archived).
- `03-DISCOVER-HANDOFF-PLAN.md` — Steps 1+3+4+5+6+7 SHIPPED on `develop-2.0-init` (commits `895eb80`, `067c09d`, `8e4c8e9`, `c20ae49`); Steps 2 N/A (research-side reuse); Step 8 = manual testForge20 e2e pending. 786 tests pass + 2 skipped + 13 subtests. Adds `_discover/handoff_schema.py`, `_discover/_cmds_handoff.py`, `_discover/_handoff_build.py`; extends `_specify/_cmds_handoff.py` and `_research/_cmds_handoff.py:check-outcome` (kind-dispatch). `/execute-task` outcome-reminder wire-in DEFERRED (command does not exist).
- `04-PR-REVIEW-PLAN.md` — Steps 1-11 SHIPPED 2026-05-20 on `develop-2.0-init`. Adds `/pr-review <PR#>` slash command + `pr_review_helper` subpackage for personal-overlay PR review of foreign repos (forge-overlay-aware AI-slop + blast-radius + scope-drift). Step 12 = testForge20 real-PR validation stop, pending manual e2e. Replay corpus seeded with a synthetic detector-catalog scenario (original real-PR fixture removed to keep third-party code out of the repo).
- `05-structural-integration-check-plan.md` — DRAFTED. Bounded ~30min pickup. Adds Section 7 (Structural Integration / DIR check) + Rule 1 extension to `src/agents/code-reviewer.md`. Source: SLUMP/ProjectGuard paper. Catches duplicate-by-new-file gap. No code landed.
- `06-CONDITIONAL-CONTEXT-PLAN.md` — DRAFTED 2026-05-20, primitive verified 2026-05-21 (Claude Code v2.0.64+ `.claude/rules/*.md` with `paths:` frontmatter). Move slices of always-on consumer-overlay `src/CLAUDE.md` (306 lines, ~4-5K tokens/turn) into conditionally-loaded rules. Largest scope; depends on stable baseline above. Step 0 = empirical token-baseline gate (kill-switch <15% reduction).
- `07-EXECUTE-TASK-REDESIGN-PLAN.md` — DRAFTED 2026-05-21. Builds `/execute-task` source spec + helper subpackage (`src/devforge/lib/_execute_task/`) — currently MISSING along with 9 other workflow commands (`/breakdown`, `/review`, `/verify`, `/summarize`, `/finalize`, `/fix`, `/refactor`, `/security`, `/audit`) per 2026-05-21 `src/commands/` audit. 12 phases: pre-flight → agent dispatch → scope-aware verify + self-repair → code-review → **forcing-functions verify-gate (absorbs 01-CONSTITUTION-FORCING-FUNCTIONS Phase 5b)** → memory + session-state → WIP commit + crash recovery → spec finalization → emitter wire-in → testForge20 e2e smoke. `/breakdown` is hard precondition (treated as read contract; Phase 11 uses hand-authored task file). 5 open questions surfaced for user confirmation before Phase 1 starts (agent ecosystem deps, wrapper-mode commit attribution, self-repair-loop ownership, crash-recovery UI shape, gate-failure-vs-WIP-commit policy).

Completed plans archived at `done-plans/`. Re-read only if maintaining the named feature.

## Conventions for ongoing work

- **Plans at repo root** as `<TOPIC>-PLAN.md` for any multi-session execution work
- Each plan includes a `## Context for next session` section + per-step `## Verify` criteria + `## When resuming work` instructions
- Plans are committed alongside the work they drive — git history shows plan evolution
- Investigation/journey knowledge lives in **Obsidian** (`20 Projects/AIDevTeamForge/`)
- Execution plans + active-state context lives in **repo**

## Branch state

- `main` — trunk.
- `develop-2.0-init` — current work branch (4-command sequence + all post-pivot work).

## Where to find what

| Topic | Location |
|---|---|
| Forge architecture decisions | `DEVELOPMENT-STATUS.md`, `CHANGELOG.md` |
| Spec sources | `src/commands/`, `src/agents/`, `src/files/` |
| Generators / emitters | `scripts/emitters/`, `scripts/generate*.py`, `scripts/generate.sh` |
| Runtime helpers (4-command sequence) | `src/devforge/lib/{init_helper,configure_helper,constitute_helper}.py` + `src/devforge/lib/_generate_docs/` |
| Forcing-functions detectors (consumer-side) | `src/devforge/lib/_constitute/_forcing_functions/` (substrate + per-rule `_magic_enum/`, `_cross_layer/`, `_any_leak/` + `_setters.py` + `_cmds_forcing_functions.py`); helper verbs `constitute_helper {verify-magic-enum, verify-cross-layer-imports, verify-any-leak, set-forcing-functions, list-forcing-functions}` ship via `.devforge/lib/constitute_helper`; opt-in pre-commit hook template at `src/git-hooks/pre-commit-forcing-functions.sh` installed to `.devforge/templates/git-hooks/` by `install.sh`. Distinct from forge-internal `constitute_helper forge-internal:verify-universal-defaults` (maintainer-side drift detector for `src/constitution.md` vs canonical defaults). |
| Pipeline handoff (research → specify → plan → execute-task) | `research/<date>-<slug>/handoff.json` (schema: `src/devforge/lib/_research/handoff_schema.py`); producer `research_helper finalize-handoff`; consumer `specify_helper import-handoff` (Phase 0.4); outcome marker `research_helper append-outcome` + `check-outcome` |
| Pipeline handoff (discover → specify → plan → execute-task) | `discover/<date>-<slug>.handoff.json` (sibling-file layout; schema: `src/devforge/lib/_discover/handoff_schema.py`, `handoff_kind = "discover"` constant); producer `discover_helper finalize-handoff` (Phase 4.0); consumer `specify_helper import-handoff` auto-dispatches on `handoff_kind`; `specify_helper find-handoffs` globs both research + discover layouts; outcome marker `discover_helper append-outcome`; `research_helper check-outcome` auto-dispatches kind for unmarked reminder text |
| Pipeline handoff (specify → plan) | `specs/NNN-<slug>/handoff.json` (nested per-feature, sibling to `spec.md`; schema: `src/devforge/lib/_specify/handoff_schema.py`, `handoff_kind = "specify"` constant); producer `specify_helper finalize-handoff` (carries `spec_seeds` structured snapshot + provenance, NO `plan_seeds` — HOW belongs to `/plan`); consumer `plan_helper read-specify-handoff` + `render-plan-seeds` **WIRED 2026-05-23** (Step 7 core, commit `a30c8e3` per `02-PLAN-COMMAND-REDESIGN-PLAN.md`) — `/plan` PHASE 0a.5 auto-discovers the sibling handoff, follows `provenance.upstream_handoff_path`, and renders the upstream research/discover `plan_seeds` into planning |
| Helper review-and-fix pipeline | `/review-helper <path>` — see `.claude/commands/review-helper.md` |
| Install / update logic | `install.sh`, `update.sh` |
| Investigation rationale | Obsidian: `20 Projects/AIDevTeamForge/` |

## Working process for all changes

**Apply to every change, not just complex ones.** Even apparently-mechanical changes (typo fixes, single-line edits, "do exactly X" instructions) go through this flow because the user's actual goal lives in their head — what looks fully specified to you may have implicit context you haven't surfaced. Friction up, surprise down.

For every change:

1. **Draft a plan first** — break the work into small steps. Each step should leave the system in a buildable, verifiable state. For a one-line change, the "plan" is a one-line confirmation: *"I'll change `<file>:<line>` from `<X>` to `<Y>` — confirm?"* That counts.
2. **Draft each step explicitly** — what files change, what the verification looks like, how it depends on prior steps.
3. **Argue every step** — give reasoning for why this step exists, what alternatives you considered, why this approach over others. Push back on the user's framing where you have substance to add. Don't rubber-stamp; engage with the trade-offs.
4. **Align with prior work** — every step must follow logically from the previous step. No logical gaps. No hallucinated assumptions about files, branches, commits, or state that you haven't verified. Read the actual code/files before making claims about what's there.
5. **Select the best option** — when alternatives exist, present them, recommend one, explain the trade-offs. Let the user redirect if they prefer a different path.
6. **Implement only after alignment** — once the user confirms, execute. End result of each step must be straightforward and independently verifiable.

The goal is that the user can challenge or redirect at any planning point before code lands. Implementation surprises are a process failure. **One extra exchange per change is the price of staying aligned.**

## Audit format

When asked for an audit, review, or critical evaluation:

1. **Count first** — state how many findings you have before presenting any. Example: *"I found 4 findings: 1 high, 2 medium, 1 nit."*
2. **One finding at a time** — present each finding individually. Wait for user reaction before the next.
3. **Per-finding format:**
   - **Severity** — high / medium / low / nit
   - **Location** — `file:line`, branch name, commit SHA, or section reference (be specific enough to navigate to)
   - **Issue** — what's wrong (concrete, not vague)
   - **Why it matters** — actual impact, not theoretical risk
   - **Fix** — specific suggestion, not "consider doing X"
4. **Cross-reference check (mandatory before proposing any fix)** — grep the entire codebase for references to whatever the fix touches: section numbers, file paths, helper command names, placeholder names, configuration keys. The fix must not leave dangling references, contradict text in other files, or miss a derivative location that needs the same change. State the cross-ref result inline with the fix (e.g., *"grep result: only the heading itself — rename safe"* or *"3 other locations reference this; will update all in the same fix"*). A fix proposed without this check is incomplete and tends to create the next audit's findings.
5. **Wait for user reaction** — they reply with one of: **fix** (apply the suggested fix), **defer** (note for later, don't fix now), **skip** (not a real issue, move on), **discuss** (engage further before deciding). **End every finding with the literal prompt `fix / defer / skip / discuss?` on its own line** — verbatim, not a paraphrase like "Vote?" or "What do you want to do?". The literal options remind the user of the available reactions without forcing them to remember.
6. After their reaction, move to the next finding. Repeat until all are addressed.

Don't batch findings into a single wall of text. Don't recommend without explaining. Don't proceed to the next finding before the user has reacted to the current one.

## Meta-discipline

These rules govern how all other discipline rules are written and applied. Violating a meta-rule erodes every rule downstream.

### Zero-escape-hatch policy

No discipline rule may contain an escape clause. Any rule with "OR", "if X except Y", "use judgment", "when reasonable", "unless trivial", or any equivalent slip-path creates a place I will drop in. When defining or revising a rule: name a single mandatory action, no carve-outs.

Past examples of escape hatches eliminated:
- "Use the claude-code-guide agent OR `docs.claude.com`" → "invoke the agent" (claimed-but-unperformed checks are unfalsifiable)
- "For non-trivial python edits, invoke reviewer" → "for ALL python edits, invoke reviewer" ("non-trivial" is a judgment call I've gotten wrong)
- "Trivial functions (≤5 lines, no branches, no I/O) may skip explicit test" → "every function gets a test" (the bugs we hit fit in <10 lines)

When proposing or revising any rule, apply this check: does the rule have an OR / if / except / unless / when-reasonable clause? If yes, the rule has an escape hatch — close it before adopting.

### Default-argue: engage critically with every request

For every non-trivial user request — code change, workflow decision, naming choice, scope question, design tradeoff, anything beyond a one-line trivial task — engage critically BEFORE or WHILE acting. The user shouldn't have to write the word "argue" to get pushback; it's the default behavior.

What "engage critically" means:
- Identify counter-arguments, simpler alternatives, edge cases the user may not have considered
- Surface conflicts with established patterns, principles, or earlier decisions
- Push back where you have substance; agree explicitly where the request is already correct
- Name tradeoffs (cost, complexity, blast radius) that affect the decision

What "sane" calibration means:
- **Don't manufacture pushback for trivial requests.** Typo fixes, repetitive operations, clearly-defined tasks with no architectural implication — execute, don't argue.
- **Don't argue past the substance.** One well-argued round (your view + reasoning + recommendation). If the user reaffirms, proceed. Multi-round bargaining is not engagement, it's friction.
- **Engagement is informational, not blocking.** Under auto mode, share your argument THEN proceed on what you think is right. The user redirects if they disagree. Engagement isn't an excuse to stall.
- **Agreement is fine.** If after thinking critically you genuinely agree, say so explicitly with the reasoning ("agreed because X") — don't fake disagreement to look engaged.

Failure modes this prevents:
- Rubber-stamping requests that have real tradeoffs (the user wanted critical engagement, got compliance)
- Drifting into anti-patterns because nobody argued for the principle that should have applied
- The user having to re-prompt with "argue" / "what are the tradeoffs" / "are you sure" to get the engagement that should have been default

### No-underspecification when delegating to agents

When invoking any agent (Task tool, subagent invocation, etc.), provide complete context the agent needs to succeed. The agent doesn't have your conversation history, your mental model of the architecture, or your knowledge of constraints — it sees only what you brief it with.

Before delegating, gather:
- The goal (what does success look like?)
- Integration context (where does this fit; what consumes its output)
- Constraints (what conventions / patterns must it follow; what existing code/files matter)
- Edge cases YOU know of (don't make the agent rediscover what you already know)
- Success criteria (how will the agent know it's done; what's the verification step)
- What NOT to do (out-of-scope changes, anti-patterns to avoid)

"Sane" calibration: match brief depth to task complexity. A 10-line helper doesn't need a 5000-word brief; a multi-file refactor needs one. But never under-deliver — agents diverging from intent because of a thin brief is the orchestrator's failure, not the agent's. If the agent surfaces a question or makes a wrong assumption, the brief was incomplete.

## Code & spec discipline

These rules apply to all framework work — not just audits. Audit findings are the consequence of violating these; following them prevents most findings from existing in the first place.

### Test-immediately-after-write for python helpers

Every python function in `scripts/lib/*.py` (or any helper script) must have a test written + actually run in the same turn as the function. No exceptions for size, complexity, "trivial" functions, or "covered by caller test" — every function gets its own test that runs. "I think this passes" is not verification. Tests must use input shapes matching what the function will receive in production — for parsers reading another tool's output, round-trip via the real producer (e.g., `configure_helper render-config` → file → `constitute_helper read-configure` parser), not hand-authored fixtures.

### Sentence-level hallucination check for spec docs

Every sentence in spec/instruction docs (`src/commands/*/main.md`, `src/commands/*/references/*.md`, `src/agents/*.md`, `CLAUDE.md`, etc.) must satisfy ONE of: (a) mechanically/definitionally true (restating an established convention), (b) verifiable right now against code/files, (c) explicit forward reference with the future state named (e.g., "Phase 4's `apply-agents` populates this — see §6.4"). Sentences that don't fit any category are hallucination risk. The most dangerous failure mode is sentences that USED to be true but became false after later edits — they look like ground truth and mislead future sessions.

### Cross-check after every change

After any edit (code, spec, doc — not just audit fixes), grep for affected identifiers, paths, section numbers, placeholder names, config keys, helper command names. Any dangling reference, contradiction in another file, or derivative location needing the same change is part of the SAME change to fix. Don't leave it for the next audit.

### Pre-empt future-session hallucination

Before declaring any change complete, ask: "What would a fresh future session falsely believe about this state?" Common seeds: removed function still referenced, renamed file still cited, deprecated pattern documented as current, partial migration mid-flight. Fix the inconsistency now — future sessions can't tell they're hallucinating because the contradictions look like ground truth.

### Verify Claude Code authoring conventions before writing commands/agents

For files that ship into a target project's `.claude/` directory or describe Claude Code integration (slash commands, agent files, command frontmatter), **invoke the `claude-code-guide` agent** to verify current authoring conventions. The agent is responsible for fetching from `docs.claude.com` and synthesizing the answer; relying on training-knowledge conventions is hallucination risk.

**Why agent-only, not "agent OR docs":** an OR clause creates an escape hatch — I can claim "I checked the docs" without an observable verification step. Agent invocation is a real tool call that leaves a trace; claimed-but-unperformed doc checks don't. Routing through the agent makes the verification observable and harder to skip silently.

Framework-internal conventions (per-project `.devforge/`, helper APIs like `configure_helper` / `constitute_helper`, etc.) live in this CLAUDE.md + spec files — those are framework-authoritative and don't need the agent. Claude-Code-integration conventions are external and require the agent per edit.
