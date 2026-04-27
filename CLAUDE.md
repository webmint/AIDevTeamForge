# AIDevTeamForge

Spec-driven, agent-coordinated workflow framework for AI development. Generates Claude Code runtime files (`CLAUDE.md`, `.claude/agents/`, `.claude/commands/`) into target projects.

## Active work — read these before starting

When picking up work mid-stream, check the repo root for active plan files. **Read the relevant plan in full before making any changes** — plans encode multi-session context that isn't in the conversation.

Currently active:

- **`CODEX-REMOVAL-PLAN.md`** — iterative removal of Codex runtime support (in progress on `feature/codex-remove`). Read it first if working on that branch, if the user mentions codex-removal / Codex drop / Claude-native cleanup, or if `git tag -l 'codex-remove/*'` shows in-progress checkpoints.

## Conventions for ongoing work

- **Plans at repo root** as `<TOPIC>-PLAN.md` for any multi-session execution work
- Each plan includes a `## Context for next session` section + per-step `## Verify` criteria + `## When resuming work` instructions
- Plans are committed alongside the work they drive — git history shows plan evolution
- Investigation/journey knowledge lives in **Obsidian** (`20 Projects/AIDevTeamForge/`)
- Execution plans + active-state context lives in **repo**

## Branch state

- `main` — current trunk (will be archived when develop-2.0 lands)
- `feature/onboard-hybrid` — R7 7-gate hybrid + R8 Claude reference state (frozen)
- `feature/codex-remove` — current work, removing Codex runtime support
- `archive/r11-investigation` — tag on `feature/onboard-memo-first`, preserves R9+R10 Codex hardening as historical artifact (do NOT cherry-pick from this; it was Codex-specific)
- R-run evidence preserved in `testParity` and `testParity-codex` linked-worktree branches (`claude-parity-run4/run5`, `codex-parity-run4/run5`)

## Where to find what

| Topic | Location |
|---|---|
| Forge architecture decisions | `DEVELOPMENT-STATUS.md`, `CHANGELOG.md` |
| Spec sources | `src/commands/`, `src/agents/`, `src/files/` |
| Generators / emitters | `scripts/emitters/`, `scripts/generate*.py`, `scripts/generate.sh` |
| Helper for `/onboard` | `scripts/lib/onboard_helper.py` |
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

Every python function in `scripts/lib/*.py` (or any helper script) must have a test written + actually run in the same turn as the function. No exceptions for size, complexity, "trivial" functions, or "covered by caller test" — every function gets its own test that runs. "I think this passes" is not verification. Tests must use input shapes matching what the function will receive in production — for parsers reading another tool's output, round-trip via the real producer (e.g., `detect_report compose` → file → `wizard_render` parser), not hand-authored fixtures.

### Sentence-level hallucination check for spec docs

Every sentence in spec/instruction docs (`src/commands/*/main.md`, `src/commands/*/references/*.md`, `src/agents/*.md`, `CLAUDE.md`, etc.) must satisfy ONE of: (a) mechanically/definitionally true (restating an established convention), (b) verifiable right now against code/files, (c) explicit forward reference with the future state named (e.g., "Phase 4's `apply-agents` populates this — see §6.4"). Sentences that don't fit any category are hallucination risk. The most dangerous failure mode is sentences that USED to be true but became false after later edits — they look like ground truth and mislead future sessions.

### Cross-check after every change

After any edit (code, spec, doc — not just audit fixes), grep for affected identifiers, paths, section numbers, placeholder names, config keys, helper command names. Any dangling reference, contradiction in another file, or derivative location needing the same change is part of the SAME change to fix. Don't leave it for the next audit.

### Pre-empt future-session hallucination

Before declaring any change complete, ask: "What would a fresh future session falsely believe about this state?" Common seeds: removed function still referenced, renamed file still cited, deprecated pattern documented as current, partial migration mid-flight. Fix the inconsistency now — future sessions can't tell they're hallucinating because the contradictions look like ground truth.

### Verify Claude Code authoring conventions before writing commands/agents

For files that ship into a target project's `.claude/` directory or describe Claude Code integration (slash commands, agent files, command frontmatter), **invoke the `claude-code-guide` agent** to verify current authoring conventions. The agent is responsible for fetching from `docs.claude.com` and synthesizing the answer; relying on training-knowledge conventions is hallucination risk.

**Why agent-only, not "agent OR docs":** an OR clause creates an escape hatch — I can claim "I checked the docs" without an observable verification step. Agent invocation is a real tool call that leaves a trace; claimed-but-unperformed doc checks don't. Routing through the agent makes the verification observable and harder to skip silently.

Framework-internal conventions (per-project `.devforge/`, `wizard_render` API, etc.) live in this CLAUDE.md + spec files — those are framework-authoritative and don't need the agent. Claude-Code-integration conventions are external and require the agent per edit.
