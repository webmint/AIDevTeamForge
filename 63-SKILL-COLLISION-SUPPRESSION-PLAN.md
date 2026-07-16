# 63 — Command Namespace + Model-Invocable (Path B): make forge commands the thing the model actually calls

**Status:** NOT STARTED — decisions drafted, **awaiting Phase-0 maintainer ratification**. No code.
**Branch:** `develop-2.0-init`.
**Approach chosen (2026-07-15):** Path B — namespace the forge commands AND make them model-invocable, so the model calls the RIGHT command instead of a bundled/plugin skill of the same intent. The old `disableBundledSkills`/`skillOverrides` approach (Path A) is **rejected** — retained below for the record so it is not re-proposed.

---

## Problem

The framework emits 20 project slash commands into a consumer's `.claude/commands/` (the
`_PROMOTED` tuple, `scripts/emitters/claude.py:49`): `init-forge, generate-docs, configure,
constitute, research, discover, specify, spec-check, plan, breakdown, implement, pr-review, audit,
review, verify, grill, summarize, finalize, fix, report-bug`.

**Reported bug:** the model offered *"want me to fix this then verify?"*, the user agreed, and the
model invoked a **non-forge `verify`** (a bundled/plugin skill), not the forge `/verify` pipeline.

### Root-cause diagnosis (auto-invocation, caused by the disable flag — NOT the name)

The hijack is **auto-invocation**, and its root cause is that every one of the 20 forge commands sets
`disable-model-invocation: true` in its frontmatter (verified: `grep -n disable-model-invocation
src/commands/*/main.md` → present in all 20; exact line varies 4–6 with frontmatter length). That flag
does two things:

1. It **stops the model from invoking** the forge command, and
2. It **drops the command's `description` from the model's context entirely.**

So when the model forms a "verify" / "review" / "plan" intent, it has **no forge command it can call** —
the forge commands are invisible to it. It falls to a **bundled or superpowers skill** of the same
intent (bundled `verify`, `superpowers:verification-before-completion`, etc.), which auto-fires on
`description` match. **Renaming alone does not fix this; the disable flag is the cause.** A forge
command that stays `disable-model-invocation: true` remains unreachable no matter what it is named.

**Typed-slash resolution is already fine and is not the problem** (both claims verified via
`claude-code-guide` against `docs.claude.com`, 2026-07-15). A project command auto-shadows a
same-named bundled skill (the project command wins, name appears once in the `/` menu), and plugin
skills are always namespaced (`superpowers:verify`, `caveman:x`) so a typed `/verify` can never
resolve to a plugin skill. The defect is purely model-side **auto-invocation**.

### The fix (Path B — two coordinated changes)

1. **Model-invocable:** remove `disable-model-invocation: true` from the forge command frontmatter so
   the model CAN invoke the forge command directly (call the forge command when the user agrees to
   "verify"). This also fixes the separate *"the model tells me to type it myself"* friction — the
   model can run the command on user agreement instead of instructing the user to type it.

2. **Namespace prefix:** prefix every emitted command name with a forge namespace so the unique name
   is what the model calls and there is **zero collision** with bundled/plugin skills. The exact
   prefix FORM is an Open Question routed to `claude-code-guide` (see OQ-1) — it is not picked blind.

The idiomatic industry fix (see **Prior art**) is to **namespace the framework's own commands and
keep them model-invocable** so the model calls the right command — NOT to disable Claude's bundled
infrastructure.

---

## Prior art (the evidence that drove Path B)

We surveyed the two dominant spec-driven-development frameworks. **Neither disables Claude's bundled
skills; both namespace their own commands and keep them model-invocable.**

- **spec-kit** (GitHub official, `https://github.com/github/spec-kit`): commands are prefixed
  `speckit.*` (`/speckit.specify`, `/speckit.plan`). Its command frontmatter (verified at
  `https://raw.githubusercontent.com/github/spec-kit/main/templates/commands/specify.md`) carries a
  `description` plus a `handoffs` array for agent→agent routing, and **does NOT set
  `disable-model-invocation`** — the commands ARE model-invocable.
- **BMAD-METHOD** (`https://github.com/bmad-code-org/BMAD-METHOD`) — **reported, NOT independently
  verified** (web-search text only; no pinpoint file confirmed): colon-namespaced commands under
  `.claude/commands/bmad/` (e.g. `/bmad:bmm:agents:pm`) with v6 shipping as a Claude Code plugin
  (plugins auto-namespace `plugin:skill`). This is a *corroborating* second data point only — it must
  be pinpoint-verified via `claude-code-guide` at Phase 0 before it is treated as load-bearing (OQ-1
  brief). Do NOT rest the conclusion on it.

**Conclusion (rests on the CONFIRMED spec-kit precedent + the `docs.claude.com` grounding below):**
namespace the framework's own commands and make them model-invocable so the model calls the RIGHT
command — do not disable Claude's built-in surface to favor the framework. spec-kit is the verified
anchor; BMAD corroborates pending Phase-0 confirmation.

---

## Rejected alternative — Path A (`disableBundledSkills` / `skillOverrides`) — retained for the record

The previous version of this plan proposed suppressing the intent-colliding skills per consumer by
emitting a `skillOverrides` block into `.claude/settings.json` (each colliding skill set to
`"user-invocable-only"`), with `disableBundledSkills: true` considered as a blunter variant.

**Rejected as non-idiomatic:** it kills part of Claude Code's built-in surface to favor the framework
— the opposite of what both dominant frameworks (spec-kit, BMAD) do. It is also a *distributed-framework
overreach*: another consumer may have installed superpowers deliberately and want its auto-fire, so a
framework that silently disables third-party plugin auto-invocation is imposing the maintainer's
environment on every consumer. **Path B fixes the actual root cause (forge commands unreachable by the
model) instead of degrading the surrounding surface.**

**Do not re-propose Path A.** If a future session believes bundled/plugin skills still hijack after
Path B ships, the fix is to confirm the forge commands are model-invocable and correctly namespaced —
not to disable the other skills.

Path A's authoritative grounding (verified via `claude-code-guide` against `docs.claude.com`,
2026-07-15) is preserved here so it is not re-derived:

- `skillOverrides` (`.claude/settings.json`, project-scoped) maps a skill id → `"on"` /
  `"name-only"` / `"user-invocable-only"` / `"off"`.
- Skill ids: bundled skills are bare (`verify`, `code-review`); plugin skills are namespaced
  (`superpowers:verification-before-completion`, `caveman:caveman-stats`).
- `disable-model-invocation: true` prevents the model from auto-invoking THAT command/skill and drops
  its description from context; it does not change typed-`/name` resolution.

---

## Current-state anchors (verified 2026-07-15)

| Fact | Location | Note |
|---|---|---|
| The 20 emitted command names | `scripts/emitters/claude.py:49` (`_PROMOTED` tuple) | `init-forge, generate-docs, configure, constitute, research, discover, specify, spec-check, plan, breakdown, implement, pr-review, audit, review, verify, grill, summarize, finalize, fix, report-bug` |
| Command sources are folder-layout | `src/commands/<name>/main.md` (+ `references/`) | The command name derives from `<name>`; `main.md` frontmatter carries `name` + `description` + `disable-model-invocation: true` |
| Every command sets the disable flag | all 20 `src/commands/*/main.md` (exact line varies 4–6) | `disable-model-invocation: true` — present in all 20 (verified via `grep -n`) |
| Install writes settings | `install.sh:334` | `cp … src/settings.template.json → .claude/settings.json` — flat copy. **Path B does NOT touch `settings.json` or bundled skills** — the old plan's whole settings mechanism is dropped. |
| Consumer command catalog | consumer `src/CLAUDE.md` "## Workflow" + "### Command Details" | The always-on model-facing awareness source — load-bearing PRECISELY BECAUSE command descriptions are NOT in model context today (see the context-cost OQ) |

**Propagation — a non-problem.** The framework has few installations; a rename reaches fresh installs
and `install.sh` re-runs. No `update.sh` merge is needed. (Note: renaming command *directories* means
a re-install/update leaves the OLD-named command files on disk in an existing consumer — see Phase 4b
for the stale-file cleanup.)

---

## Decisions

- **D1 (locked by approach choice):** mechanism = Path B (namespace + model-invocable). Path A
  (`skillOverrides` / `disableBundledSkills`) is rejected — see the Rejected-alternative section.
- **D2 (PROPOSED — needs Phase-0 sign-off):** the prefix FORM is chosen at Phase 0 via OQ-1
  (`claude-code-guide`), not picked here. Candidates: dot (`forge.verify`), colon-via-nested-dir
  (`.claude/commands/forge/verify` → `/forge:verify`), dash (`forge-verify`).
- **D3 (PROPOSED — needs Phase-0 sign-off):** scope of the disable-flag removal — all 20 commands, or
  only the model-spontaneous-intent commands (see OQ-3). Prefer a single uniform rule (zero-escape-hatch
  discipline) unless a hard reason to split emerges.
- **D4 (PROPOSED — needs Phase-0 sign-off):** reconcile with plan `26-REINTRODUCE-FIX-PLAN.md` D2
  (`/fix` is model-PROPOSED, user-INVOKED). Path B would let the model invoke `/fix` on agreement —
  either amend plan 26 D2 or keep `/fix` as a `disable-model-invocation: true` exception (see OQ-4).
- **D5:** settings.json / bundled skills are **untouched** — Path B is entirely a command-frontmatter
  + command-name + emitter + docs change. No `settings.template.json` edit, no `update.sh` merge, no
  `manifest.json` `mergeFiles` entry.

---

## Open questions (must resolve before/at Phase 0)

- **OQ-1 — prefix FORM (route to `claude-code-guide`):** which project-command name form actually
  works and is idiomatic — **dot** (`forge.verify`, spec-kit precedent, verified `speckit.*` at
  `https://github.com/github/spec-kit`), **colon via nested directory** (`.claude/commands/forge/verify`
  → `/forge:verify`, BMAD precedent `/bmad:bmm:agents:pm` at
  `https://github.com/bmad-code-org/BMAD-METHOD`), or **dash** (`forge-verify`, a literal rename with
  no special resolution)? The agent must confirm how each form is discovered, typed, and shadowed, and
  whether a nested-directory command changes the emitter's output path. **No prefix is committed until
  this is answered.**
- **OQ-2 — CONTEXT COST (the central tradeoff):** making 20 commands model-invocable puts their
  `description` back into always-on model context — the exact thing `disable-model-invocation` was
  chosen to avoid. Plan `08-CLAUDE-MD-COMMAND-TRIM-PLAN.md` trimmed the consumer `src/CLAUDE.md`
  command catalog, and the catalog is load-bearing PRECISELY BECAUSE descriptions were NOT in context
  (memory: `project_command_awareness_disable_model_invocation`). Path B may let that always-on
  catalog SHRINK (descriptions now reach the model via the commands themselves), **partially
  offsetting** the cost — but the **net context delta must be MEASURED, not assumed.** This is the
  decision's main open question: is the added description weight worth the reachability fix, and how
  much of the `src/CLAUDE.md` catalog can be trimmed to compensate?
- **OQ-3 — scope of the disable-flag removal:** do ALL 20 commands drop `disable-model-invocation`, or
  only the ones tied to model-spontaneous intents (`verify` / `review` / `plan` / `fix` / `audit` /
  `research`), leaving two other categories human-only — the one-time **setup** commands (`init-forge`
  / `generate-docs` / `configure` / `constitute`) and the **opt-in adversarial** checks (`grill` /
  `spec-check`, which are deliberately user-invoked gates, never something the model should auto-start)?
  Prefer a single uniform rule (zero-escape-hatch) unless there is a hard reason to split.
- **OQ-4 — human-gated pipeline (why the "keep it human-only" objection is weak):** forge deliberately
  made commands human-invoked so the pipeline is human-driven. **Counter-point:** forge's hard approval
  gates live INSIDE each command body (spec approval before `/plan`, plan approval before `/breakdown`,
  breakdown approval before `/implement`, the per-task hard gate in `/implement`), so even if the model
  STARTS `/breakdown` or `/implement`, it still halts at the in-command approval gate — the human-gate
  guarantee is mostly preserved even when model-invocable. This is the reason the "keep it human-only"
  cost is weak; ratification confirms it.
- **OQ-5 — plan 26 D2 reconciliation:** plan `26-REINTRODUCE-FIX-PLAN.md` D2 EXPLICITLY specifies the
  model PROPOSES `/fix` and the USER invokes it (never model-invoked). Path B would let the model
  invoke `/fix` on agreement — this must be reconciled with plan 26 D2 (either 26 D2 is amended, or
  `/fix` stays a `disable-model-invocation: true` exception). **Flag it; do not silently override plan
  26.**
- **OQ-6 — adopt spec-kit's `handoffs` frontmatter?** spec-kit's command frontmatter carries a
  `handoffs` array for command→command routing. Out of scope for the core fix, but noted as a possible
  follow-on since Path B makes the pipeline model-drivable.

---

## Blast radius (a real cost — sizes the cross-ref-sweep phase)

Renaming every command touches:

- `scripts/emitters/claude.py:49` (`_PROMOTED` tuple) + any emitter logic that derives the command
  name / output path from `<name>` (a nested-directory prefix form, OQ-1, changes the output path).
- Every `src/commands/<name>/main.md` frontmatter (`name` field + the `disable-model-invocation`
  removal) and every in-body self-reference and cross-command reference (e.g. `/verify` says "run after
  `/review`, before `/summarize`/`/finalize`").
- The consumer `src/CLAUDE.md` command catalog + workflow arrow-chain + "### Command Details" + the
  "### Conversational fix-or-file offer" block (every `/name` mention).
- Every cross-reference in the other repo-root PLAN files and specs (dozens of `/name` mentions across
  the `NN-*-PLAN.md` set and `src/commands/*/references/*.md`).
- Handoff-doc command mentions and any `feedback_*`/memory notes that name a command.

This is enumerated as a dedicated cross-ref-sweep phase, not folded into the per-command edits.

---

## Phased execution

### Phase 0 — Ratification gate (maintainer)
Close OQ-1 (prefix FORM, via `claude-code-guide` — the same brief pinpoint-verifies the BMAD prior-art
claim and the two typed-slash shadowing/namespace facts), decide OQ-2 (the context-cost tradeoff —
including whether to measure the net delta before or during build), decide OQ-3 (scope of the
disable-flag removal), reconcile OQ-5 (plan 26 D2), confirm OQ-4's reasoning holds, and record OQ-6 as
deferred (per Non-goals). Lock D2/D3/D4. **No build until this closes.**

**Verify:** OQ-1..OQ-6 answered inline in this file; D2/D3/D4 marked locked or amended; the chosen
prefix form recorded verbatim.

### Phase 1 — Emitter + naming mechanism (python)
Implement the chosen prefix form in the emitter — update `_PROMOTED` (or the name-derivation logic) so
each emitted command carries the forge namespace, and adjust the output path if OQ-1 selects the
nested-directory form. Route through the **python-engineer → python-reviewer** loop.

**Verify:** a fresh `install.sh` (or emit) into a scratch target produces `.claude/commands/` with the
namespaced command names/paths; no `{{` leaks; the emitter's existing tests pass (extend them for the
new name shape).

### Phase 2 — Command frontmatter: remove the disable flag + rename (per OQ-3 scope)
For every in-scope command `main.md`: remove `disable-model-invocation: true` and update the `name`
field to the namespaced form. Route **every** command `main.md`/frontmatter edit through the
**instruction-author → instruction-reviewer + claude-code-guide** iterative loop (writer → reviewer →
loop until clean → integrate) — these files ship into `.claude/`.

**Verify:** each edited `main.md` frontmatter parses; the in-scope commands no longer carry
`disable-model-invocation`; `claude-code-guide` confirms the frontmatter is valid for a
model-invocable namespaced command.

### Phase 3 — Consumer `src/CLAUDE.md` reconcile (docs + catalog trim)
Update the workflow arrow-chain, "### Command Details", and the "### Conversational fix-or-file offer"
block to the namespaced command names. If OQ-2 resolves that the always-on catalog can shrink (because
descriptions now reach the model via the commands), trim it here and record the net context delta.
Route every `src/CLAUDE.md` edit through the **instruction-author → instruction-reviewer +
claude-code-guide** loop.

**Verify:** grep the consumer `src/CLAUDE.md` for any un-namespaced `/name` mention → zero; the
arrow-chain and Command-Details section use the namespaced names consistently.

### Phase 4a — Cross-reference sweep, docs/specs (blast radius)
Grep every OLD command name across `src/commands/*/main.md` bodies, `src/commands/*/references/*.md`,
every repo-root `NN-*-PLAN.md`, handoff docs, and the memory/`feedback_*` notes; update each to the
namespaced form. **Discipline split:** edits to files that ship into `.claude/`
(`src/commands/**/main.md` bodies + `references/*.md`) route through the **instruction-author →
instruction-reviewer + claude-code-guide** loop; the non-shipping subset (repo-root `NN-*-PLAN.md`,
memory/`feedback_*` notes) is plain-edit, no loop needed.

**Verify:** grep for each old `/name` across `src/` + repo-root plans → every remaining reference is
either updated or an intentional historical citation explicitly noted as such; no dangling reference.

### Phase 4b — Stale-old-file cleanup on re-install (code, only if the prefix renames directories)
Conditional on OQ-1 selecting a directory-renaming prefix form. A re-install/update leaves the
OLD-named command files/dirs on disk in an existing consumer's `.claude/commands/`. Name the target
(most plausibly `update.sh`, and/or `install.sh`) and add a fail-soft removal of the superseded old
command paths. Route through the **python-engineer → python-reviewer** loop. If OQ-1 selects a
non-directory-renaming form (dot in a flat file name), this phase is a no-op — record that explicitly.

**Verify:** a scratch consumer with the OLD-named command files → run the updated `install.sh`/`update.sh`
→ old-named command files are gone, new namespaced ones present; a non-git / absent-path case is a
benign no-op (fail-soft).

### Phase 5 — Docs reconcile (release-docs propagation)
Per the standing `feedback_release_docs` discipline (propagate command changes to README /
DEVELOPMENT-STATUS / storage-rules on any command change): `CHANGELOG.md` entry; the root `CLAUDE.md`
"Where to find what" table and any command-name mentions; **`README.md`** (grep confirms 9 `/name`
mentions), **`DEVELOPMENT-STATUS.md`** (12 mentions), **`src/devforge/storage-rules.md`** (5 mentions);
this plan's status; a `feedback_*`/memory note if a durable rule emerges (e.g. "forge commands are
namespaced + model-invocable"). (`CLAUDE.template` named in the memory note does not exist as a file —
superseded by `src/CLAUDE.md`, handled in Phase 3.)

**Verify:** grep for `disable-model-invocation` across `src/` → only intentional exceptions remain
(per OQ-3/OQ-5); grep each old `/name` across `README.md` / `DEVELOPMENT-STATUS.md` /
`src/devforge/storage-rules.md` → zero, or explicitly-noted historical citations; grep the new
namespace prefix across docs → consistent.

### Phase 6 — Consumer / testForge20 e2e (user-driven HARD GATE)
Fresh install into a consumer; in a real session, the model offers to "verify" (or the user agrees to
a proposed "fix then verify"); confirm the model now invokes the forge namespaced command (e.g.
`/forge:verify`) and **no bundled/plugin skill hijacks**.

**Verify:** transcript evidence — on user agreement to "verify", the model invokes the forge
namespaced command, not a bundled/superpowers `verify` skill; the human approval gates inside the
command still halt as designed; superpowers/caveman still auto-fire in a NON-forge repo (their global
behavior is untouched, since Path B disables no skill).

---

## Non-goals

- Disabling any bundled or plugin skill (`skillOverrides` / `disableBundledSkills`) — rejected as Path
  A; see the Rejected-alternative section.
- Touching `settings.json`, `install.sh`'s settings copy, or `update.sh` — Path B is command-side only
  (D5).
- Adopting spec-kit's `handoffs` frontmatter for command→command routing (OQ-6 — possible follow-on,
  not this fix).
- An `update.sh` merge for propagation — few installs; re-run `install.sh` (the stale-old-file cleanup
  for renamed directories is Phase 4, not a merge).

---

## Context for next session

The reported bug: the model, on user agreement to "verify", invoked a **non-forge** `verify` skill
(bundled/plugin), not the forge `/verify`. Root cause is **auto-invocation**, and it is caused by the
`disable-model-invocation: true` flag on all 20 forge commands — the flag makes the forge commands
unreachable by the model AND drops their descriptions from context, so the model falls to a
same-intent bundled/superpowers skill. Renaming alone does not fix it; the flag is the cause.

Chosen fix = **Path B** (idiomatic per spec-kit + BMAD, neither of which disables bundled skills):
(1) **remove the disable flag** so the model can invoke the forge command, and (2) **namespace every
command** so the unique name is what the model calls (zero collision). The old `skillOverrides` /
`disableBundledSkills` approach (Path A) is **rejected and recorded** so it is not re-proposed.

The crux is **OQ-2 (context cost)** — model-invocable puts 20 descriptions back into always-on context
(the thing the disable flag avoided); the `src/CLAUDE.md` catalog may shrink to offset, but the **net
delta must be measured**. Also open: **OQ-1** (prefix FORM, via `claude-code-guide`) and **OQ-5** (plan
26 D2 — `/fix` is model-proposed/user-invoked; Path B would let the model invoke it — reconcile, don't
silently override). Everything is drafted; **nothing built**; Phase 0 ratification is the gate.

## When resuming work

1. Re-read this file top to bottom.
2. Route **OQ-1** (prefix FORM: dot vs colon-via-nested-dir vs dash) to `claude-code-guide` with the
   spec-kit + BMAD precedents in the brief; record the answer verbatim.
3. Resolve **OQ-2** (context cost) — decide whether to measure the net `src/CLAUDE.md`-catalog delta
   before committing, and **OQ-3** (all 20 vs intent-only scope), and **OQ-5** (plan 26 D2).
4. Get maintainer sign-off on D2/D3/D4 at Phase 0. **No build until Phase 0 closes.**
5. Build phase by phase. **Every** command `main.md`/frontmatter edit and **every** `src/CLAUDE.md`
   edit routes through the **instruction-author → instruction-reviewer + claude-code-guide** iterative
   loop (writer → reviewer → loop until clean → integrate). **Every** emitter/python change routes
   through the **python-engineer → python-reviewer** loop. This dual-agent-loop discipline is a hard
   requirement from the repo `CLAUDE.md`.
6. Run the Phase 4 cross-reference sweep as its own phase (grep every old `/name` across specs, docs,
   and the repo-root plans).
7. Close with the Phase 6 consumer / testForge20 e2e HARD GATE (user-driven).
