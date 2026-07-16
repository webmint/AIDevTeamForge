# 63 — `devforge:` command namespace + model-invocable (Path B)

**Status:** NOT STARTED — the naming design is SETTLED (token / form / refs relocation, below); only the
remaining SCOPE decisions await Phase-0 sign-off (which commands drop the disable flag; the context-cost
tradeoff; the plan-26 `/fix` reconcile). No code.
**Branch:** `develop-2.0-init`.

---

## Problem

The framework emits 20 project slash commands into a consumer's `.claude/commands/` (the `_PROMOTED`
tuple, `scripts/emitters/claude.py:49`): `init-forge, generate-docs, configure, constitute, research,
discover, specify, spec-check, plan, breakdown, implement, pr-review, audit, review, verify, grill,
summarize, finalize, fix, report-bug`.

**Reported bug:** the model offered *"want me to fix this then verify?"*, the user agreed, and the model
invoked a **non-forge `verify`** (a bundled/plugin skill), not the forge `/verify`.

**Root cause — auto-invocation, caused by the disable flag (NOT the name).** Every one of the 20 forge
commands sets `disable-model-invocation: true` in its frontmatter (verified: `grep -n
disable-model-invocation src/commands/*/main.md` → present in all 20; exact line varies 4–6 with
frontmatter length). That flag (1) stops the model from invoking the forge command, and (2) drops the
command's `description` from the model's context entirely. So when the model forms a "verify"/"review"/
"plan" intent it has **no forge command it can call** — the forge commands are invisible to it — and it
falls to a bundled or superpowers skill of the same intent. Renaming alone does not fix this; the disable
flag is the cause.

Typed-slash resolution is already fine (verified via `claude-code-guide` against `docs.claude.com`,
2026-07-15): a project command auto-shadows a same-named bundled skill, and plugin skills are always
namespaced (`superpowers:verify`), so a typed `/verify` never resolves to a plugin skill. The defect is
purely model-side **auto-invocation**.

**Second, independent defect surfaced during this design (folded in here):** the emitter writes each
command's on-demand reference files INTO `.claude/commands/<name>/references/` (`claude.py:70-71`).
Claude Code recursively discovers every `.md` under `.claude/commands/` and colon-namespaces it by path,
so each reference file leaks into the `/` menu as a **phantom command** —
`/constitute:references:section-shapes` and 27 others (28 total across 11 command folders, live-counted
via `find src/commands -path '*/references/*.md'`). This is not a
naming preference; it is menu pollution the same emitter change must fix, because the namespace move
touches the exact same output paths.

---

## The fix (Path B — three coordinated changes, all producer-side)

1. **Namespace via a `devforge/` subdirectory (flat command file inside it).** Emit each command to
   `.claude/commands/devforge/<name>.md` → the command surfaces as **`/devforge:<name>`** (e.g.
   `/devforge:verify`). This uses the DOCUMENTED flat-file rule (a file at `.claude/commands/<path>.md`
   is named by its subpath, filename-without-extension) — the `devforge/` path segment IS the namespace.
   NOT a nested `<name>/main.md` folder (there is no documented `main.md`-leaf-dropping rule — see the
   naming-decisions note). This makes the forge command uniquely named — zero collision with any
   bundled/plugin skill — and (with change 2) the thing the model actually calls.

2. **Model-invocable.** Remove `disable-model-invocation: true` from the in-scope command frontmatter so
   the model CAN invoke `/devforge:verify` when the user agrees to "verify". This also fixes the separate
   *"the model tells me to type it myself"* friction. Scope (all 20 vs a carve-out for setup + opt-in
   adversarial commands) is the one open decision — see OQ-2.

3. **References out of `.claude/commands/`.** Relocate every reference file to
   `.devforge/command-refs/<name>/<ref>.md` (outside the command-scan surface → no phantom commands). The
   command bodies relink automatically — the emitter already rewrites reference cross-refs (`claude.py:24-25`).

Changes 1 and 3 are the SAME emitter edit (both rewrite command/reference output paths — today
`claude.py:73` writes `.claude/commands/<name>.md` flat and `:70` writes refs to
`.claude/commands/<name>/references/`; the edit re-points both). Change 2 is a scoped frontmatter edit.
The 20 source `main.md` files barely change — the namespace and the phantom fix are entirely emitter-side.

---

## Settled naming decisions (do not re-open — each is evidence-backed)

- **Token = `devforge`.** It matches the framework's existing filesystem namespace (`.devforge/lib`,
  `.devforge/memory.md`, …) — one namespace across filesystem AND commands. Rejected: `forge` (a common
  word — software "forges", Laravel Forge, Terraform — real collision surface, undercutting the point);
  `aidtf` (unique but opaque/unmemorable).
- **Prefix, not suffix.** The `/` menu uses **fuzzy subsequence search** (verified via `claude-code-guide`:
  *"filter commands by name (fuzzy search)"*), so typing `verify` surfaces `/devforge:verify` — the prefix
  costs **zero** extra keystrokes. Prefix keeps the commands grouped under `devforge` in the menu and
  matches the industry norm (Prior art). A suffix (`verify-devforge`) scatters the menu and buys nothing.
- **Form = a flat command file under a `devforge/` subdirectory** (`.claude/commands/devforge/<name>.md`),
  NOT a frontmatter field and NOT a nested `<name>/main.md` folder. The `name:` frontmatter field is
  **display-only** — it sets the listing label and does NOT change what you type after `/` (verified via
  `claude-code-guide`); the command name is path-derived. The DOCUMENTED rule (Claude Code skills docs,
  fetched 2026-07-17) covers exactly the flat-file case: a file at `.claude/commands/<path>.md` is named by
  its subpath (filename without extension), so `.claude/commands/devforge/verify.md` → `/devforge:verify`.
  The current emitter already writes commands flat (`.claude/commands/<name>.md`, `claude.py:73`) — adding
  the `devforge/` segment is the whole change. **Note — a `main.md`-leaf-dropping rule is NOT documented and
  NOT observed:** the only nested evidence today is `.claude/commands/<name>/references/section-shapes.md` →
  `/<name>:references:section-shapes`, which RETAINS the full stem (drops nothing). So the flat form is
  chosen precisely because it is the documented, unambiguous path — a nested `<name>/main.md` would risk
  `/devforge:<name>:main` and is avoided.
- **References must leave `.claude/commands/`.** There is **no supported exclude mechanism** (verified via
  `claude-code-guide`: no underscore/dot filename convention, no frontmatter flag, no settings key hides a
  `.md` under `.claude/commands/` from discovery). Relocation is the only robust fix.

---

## Prior art (why Path B is the idiomatic fix)

The two dominant spec-driven-development frameworks both **namespace their own commands and keep them
model-invocable**; neither disables Claude's bundled skills:

- **spec-kit** (GitHub official, `https://github.com/github/spec-kit`) — CONFIRMED: commands are prefixed
  `speckit.*` (`/speckit.specify`); frontmatter (verified at
  `https://raw.githubusercontent.com/github/spec-kit/main/templates/commands/specify.md`) has `description`
  + a `handoffs` array and does NOT set `disable-model-invocation`.
- **BMAD-METHOD** (`https://github.com/bmad-code-org/BMAD-METHOD`) — REPORTED, not independently verified
  (web-search text only): colon-namespaced commands under `.claude/commands/bmad/`, v6 shipped as a plugin.
  A corroborating second data point only; pinpoint-verify at Phase 0 before treating as load-bearing.

The conclusion rests on the CONFIRMED spec-kit precedent + the `docs.claude.com` grounding.

---

## Rejected alternatives (retained so they are not re-proposed)

- **Path A — `disableBundledSkills: true` / per-skill `skillOverrides`.** Rejected as non-idiomatic: it
  kills part of Claude Code's built-in surface to favor the framework (the opposite of what spec-kit and
  BMAD do), and for a distributed framework it is overreach (imposes the maintainer's environment on every
  consumer). Path B fixes the actual root cause (forge commands unreachable by the model) instead of
  degrading the surrounding surface. If a future session believes skills still hijack after Path B, the fix
  is to confirm the forge commands are model-invocable and correctly namespaced — NOT to disable other skills.
- **Suffix naming** (`verify-devforge`). Rejected: scatters the menu by verb, no grouping, no namespace
  semantics, and fuzzy search already removes the only claimed benefit (typing the verb first).

---

## Current-state anchors (verified 2026-07-15 / 2026-07-17)

| Fact | Location | Note |
|---|---|---|
| The 20 emitted command names | `scripts/emitters/claude.py:49` (`_PROMOTED`) | `init-forge … spec-check … report-bug` |
| Command source layout | `src/commands/<name>/main.md` (+ `references/`) | SOURCE is a folder; the emitter FLATTENS on emit |
| Command emitted layout (TODAY) | `claude.py:73` `(commands_dir / f"{source.name}.md")` | `.claude/commands/<name>.md` — **flat file** → `/<name>` (documented flat-file rule). No `main.md` in the target tree |
| All 20 set the disable flag | all 20 `src/commands/*/main.md` (line varies 4–6) | `disable-model-invocation: true` (verified via `grep -n`) |
| `name:` field present in all 20 | `src/commands/*/main.md` | Display-only — does NOT drive the command name |
| Reference emit paths | `claude.py:70-71` (`refs_dir`, `refs_prefix`) | Writes refs to `.claude/commands/<name>/references/` → the 28 phantoms |
| Reference cross-ref rewrite | `claude.py:24-25` | Emitter already rewrites body reference paths — relocation is a prefix change here |
| Settings copy | `install.sh:334` | `cp settings.template.json → .claude/settings.json` (settings ONLY) |
| Full-install command generation | `install.sh:318` → `scripts/generate.sh` → `scripts/emitters/claude.py` | Commands/agents are GENERATED by the emitter, NOT `cp` |
| Surgical single-command delivery | `install.sh` `--only` path (~93-120) → `claude.py --only` | Direct emitter call for one command |
| Phantom reference commands | 28 files across 11 command folders | `audit` 6, `grill`/`implement`/`review` 4 each, `configure`/`constitute`/`spec-check` 2 each, `finalize`/`fix`/`summarize`/`verify` 1 each |

**Propagation — a non-problem.** Few installations; the move reaches fresh installs and `install.sh`
re-runs. Moving each flat command file into `commands/devforge/` leaves the OLD `.claude/commands/<name>.md`
files AND the now-empty old `.claude/commands/<name>/references/` folders on disk in an existing consumer
on re-install — a stale-file cleanup, addressed in Phase 4b.

**References home = `.devforge/command-refs/`** (outside the command scan, forge-owned). They are
install-reproducible, so they SHOULD be gitignored + untracked following plan 56's `.devforge/`
code-disposition model — but that infrastructure does NOT cover this new path yet: `src/files/devforge.gitignore`
and `scripts/devforge-state-migrate.sh` list only `lib/`/`bin/`/`templates/`. Adding `.devforge/command-refs/`
to both (plus a `storage-rules.md` CODE-class row) is REQUIRED work, not a free alignment — see Phase 1b.

---

## Decisions

- **D1 — token = `devforge`** (settled; see Settled naming decisions).
- **D2 — prefix via a flat command file under a `devforge/` subdir** `.claude/commands/devforge/<name>.md`
  → `/devforge:<name>` (settled; documented flat-file rule, no `main.md`-leaf risk).
- **D3 — references relocate** to `.devforge/command-refs/<name>/`; the 28 phantoms are killed by the same
  emitter edit (settled; the separate "plan 64" idea is absorbed here).
- **D4 — model-invocable** by removing `disable-model-invocation: true` (Path B). Scope is OQ-2.
- **D5 — settings.json / bundled skills untouched.** Path B is command-layout + frontmatter + emitter +
  docs only. No `settings.template.json` / `disableBundledSkills` / `skillOverrides` (Path A rejected).

---

## Open questions (the genuinely-open ones — naming is already settled above)

- **OQ-1 — CONTEXT COST (the central tradeoff):** making commands model-invocable puts their `description`
  back into always-on model context — the exact thing `disable-model-invocation` was chosen to avoid. Plan
  `08-CLAUDE-MD-COMMAND-TRIM-PLAN.md` made the consumer `src/CLAUDE.md` command catalog load-bearing
  PRECISELY BECAUSE descriptions were NOT in context (memory:
  `project_command_awareness_disable_model_invocation`). Path B may let that catalog SHRINK (descriptions
  now reach the model via the commands), partially offsetting the cost — but the **net delta must be
  MEASURED, not assumed.**
- **OQ-2 — scope of the disable-flag removal:** do ALL 20 commands drop `disable-model-invocation`, or only
  the model-spontaneous-intent commands (`verify` / `review` / `plan` / `fix` / `audit` / `research`),
  leaving two categories human-only — the one-time **setup** commands (`init-forge` / `generate-docs` /
  `configure` / `constitute`) and the **opt-in adversarial** checks (`grill` / `spec-check`, deliberately
  user-invoked gates the model should never auto-start)? Prefer a single uniform rule (zero-escape-hatch)
  unless there is a hard reason to split. NOTE: the `devforge:` NAMESPACE applies to all 20 regardless of
  this decision — only the disable-flag removal is scoped.
- **OQ-3 — plan 26 D2 reconcile:** plan `26-REINTRODUCE-FIX-PLAN.md` D2 specifies the model PROPOSES `/fix`
  and the USER invokes it (never model-invoked). If `/fix` drops the disable flag it becomes
  model-invocable — reconcile (amend plan 26 D2, or keep `/fix` a disable-flag exception). Flag it; do not
  silently override plan 26.
- **OQ-4 — human-gate objection is weak (record the reasoning):** forge deliberately made commands
  human-invoked. Counter-point: the hard approval gates live INSIDE each command body (spec approval before
  `/plan`, plan approval before `/breakdown`, the per-task gate in `/implement`), so even a model-STARTED
  command still halts at its in-command gate — the human-gate guarantee mostly survives model-invocability.
  **Explicit boundary reversal:** plan `08-CLAUDE-MD-COMMAND-TRIM-PLAN.md` records under "This plan does NOT
  touch" that `disable-model-invocation: true` is *"manual-only is the framework's design intent, not a
  bug."* D4 deliberately reverses that specific commitment (scoped) — this is a considered reconciliation
  given the hijack evidence, NOT an oversight; Phase 0 ratifies it the same way OQ-3 reconciles plan 26 D2.
- **OQ-5 — adopt spec-kit's `handoffs` frontmatter?** Out of scope for this fix; noted as a possible
  follow-on since Path B makes the pipeline model-drivable.

---

## Blast radius

- `scripts/emitters/claude.py` — flat command output path (`:73`, `+ "devforge"`), `refs_dir` /
  `refs_prefix` (`:70-71`); `_PROMOTED` unchanged (names stay `<name>`; the emitted PATH adds the
  `devforge/` segment).
- `install.sh` / `update.sh` — the stale-old-file cleanup (Phase 4b) removing old flat `.claude/commands/<name>.md`
  + old `.claude/commands/<name>/references/` folders. (Command generation itself flows through
  `scripts/generate.sh` → `claude.py`, not a `cp` — see anchors.)
- `src/files/devforge.gitignore` + `scripts/devforge-state-migrate.sh` — add `.devforge/command-refs/`
  (Phase 1b, plan-56 model).
- The 20 `src/commands/*/main.md` — the scoped `disable-model-invocation` removal ONLY (the namespace is
  path-side, not a frontmatter edit).
- Consumer `src/CLAUDE.md` — the workflow arrow-chain, "### Command Details", and the fix-or-file offer,
  every `/name` → `/devforge:name`; and the OQ-1 catalog-shrink if ratified.
- Every `/name` cross-reference across `src/commands/*/references/*.md`, the repo-root `NN-*-PLAN.md` set,
  handoff docs, `README.md`, `DEVELOPMENT-STATUS.md`, `src/devforge/storage-rules.md`, and memory notes.

---

## Phased execution

### Phase 0 — Ratification gate (maintainer)
Decide OQ-1 (context-cost tradeoff — and whether to measure the net `src/CLAUDE.md` delta before or during
build), OQ-2 (scope of the disable-flag removal), and reconcile OQ-3 (plan 26 D2). Confirm OQ-4's reasoning
holds; record OQ-5 as deferred. The naming decisions (D1–D3) are already settled and need no re-ratification.
**No build until this closes.**

**Verify:** OQ-1/OQ-2/OQ-3 answered inline; the disable-flag scope recorded explicitly (all 20, or the
named carve-out).

### Phase 1 — Emitter: namespace + references relocation (python)
One `scripts/emitters/claude.py` edit: emit each command as a flat file to
`.claude/commands/devforge/<name>.md` (change `:73` `commands_dir / f"{source.name}.md"` →
`commands_dir / "devforge" / f"{source.name}.md"`) and references to `.devforge/command-refs/<name>/`
(change `refs_dir` / `refs_prefix` at `:70-71`) so command bodies relink via the existing rewrite
(`:24-25`). Route through the **python-engineer → python-reviewer** loop; extend the emitter tests for the
new paths.

**Verify:** a fresh emit into a scratch target produces `.claude/commands/devforge/<name>.md` (flat) and
`.devforge/command-refs/<name>/*.md` with **zero** `.md` files anywhere under `.claude/commands/*/references/`;
no `{{` leaks; the emitter tests pass. Documented flat-file rule guarantees `/devforge:<name>`; a
**30-second live-confirm** in a scratch Claude Code session (type `/`, confirm `/devforge:verify` appears and
no `/devforge:verify:references:*` phantom) is a belt-and-suspenders check, not the primary evidence.

### Phase 1b — Gitignore + untrack the new references home (python; plan-56 model)
The relocated refs live at `.devforge/command-refs/` — an install-reproducible path that plan 56's
infrastructure does NOT yet cover. (a) Append `.devforge/command-refs/` to `src/files/devforge.gitignore`;
(b) extend the directory-untrack loop in `scripts/devforge-state-migrate.sh` to include it (fail-soft,
tracked-only, install-repo-only — the plan-56 pattern); (c) add a CODE-class row to
`src/devforge/storage-rules.md`. Route through the **python-engineer → python-reviewer** loop.

**Verify:** a fresh emit + `git status` in a scratch consumer shows `.devforge/command-refs/` untracked and
gitignored; the migrate script untracks a previously-tracked `.devforge/command-refs/` while leaving VERSIONED
`.devforge/` root files tracked; non-git / absent-path case is a benign no-op.

### Phase 2 — Frontmatter: remove the disable flag (scoped per OQ-2) (instruction)
Remove `disable-model-invocation: true` from the in-scope command `main.md` files. Route **every** edit
through the **instruction-author → instruction-reviewer + claude-code-guide** loop (these ship into `.claude/`).

**Verify:** each edited frontmatter parses; in-scope commands no longer carry the flag; any intentional
carve-out (OQ-2) still carries it and is listed; `claude-code-guide` confirms the frontmatter is valid for a
model-invocable command.

### Phase 3 — Consumer `src/CLAUDE.md` reconcile (instruction)
Update the workflow arrow-chain, "### Command Details", and the fix-or-file offer to `/devforge:<name>`. If
OQ-1 ratifies a catalog shrink, apply it here and record the measured net context delta. Route every edit
through the **instruction-author → instruction-reviewer + claude-code-guide** loop.

**Verify:** grep `src/CLAUDE.md` for any bare `/<name>` (un-namespaced) forge-command mention → zero; the
arrow-chain + Command-Details use `/devforge:` consistently.

### Phase 4a — Cross-reference sweep, docs/specs
Grep every old `/name` across `src/commands/*/main.md` bodies, `src/commands/*/references/*.md`, every
repo-root `NN-*-PLAN.md`, handoff docs, and memory/`feedback_*` notes; update to `/devforge:<name>`. Shipping
files (`src/commands/**` bodies + `references/*.md`) route through the **instruction-author →
instruction-reviewer + claude-code-guide** loop; non-shipping files (repo-root plans, memory notes) are plain-edit.

**Verify:** grep each old `/name` across `src/` + repo-root plans → every remaining reference is updated or an
explicitly-noted historical citation; no dangling reference.

### Phase 4b — Stale-old-command-dir cleanup on re-install (code)
A re-install/update leaves the OLD `.claude/commands/<name>/` dirs (and their reference subfolders) behind in
an existing consumer. Add a fail-soft removal of the superseded old command paths to `install.sh`/`update.sh`.
Route through the **python-engineer → python-reviewer** loop.

**Verify:** a scratch consumer with OLD-named command dirs → run the updated installer → old dirs gone, new
`.claude/commands/devforge/` present, refs under `.devforge/command-refs/`; absent-path / non-git case is a
benign no-op.

### Phase 5 — Docs reconcile (release-docs)
Per `feedback_release_docs`: `CHANGELOG.md`; root `CLAUDE.md` "Where to find what" table + command mentions;
`README.md` (9 `/name` mentions), `DEVELOPMENT-STATUS.md` (12), `src/devforge/storage-rules.md` (5); this
plan's status; a `feedback_*`/memory note if a durable rule emerges ("forge commands are `devforge:`-namespaced
+ model-invocable; refs live in `.devforge/command-refs/`").

**Verify:** grep `disable-model-invocation` across `src/` → only intentional OQ-2 carve-outs remain; grep
`/devforge:` across docs → consistent; grep old bare `/name` across README / DEVELOPMENT-STATUS / storage-rules
→ zero or explicitly-noted historical.

### Phase 6 — Consumer / testForge20 e2e (user-driven HARD GATE)
Fresh install into a consumer; in a real session, on user agreement to "verify" (or a proposed "fix then
verify"), confirm the model invokes `/devforge:verify` and **no bundled/plugin skill hijacks**.

**Verify:** transcript — on agreement to "verify", the model invokes the `devforge:`-namespaced command, not a
bundled/superpowers `verify`; the in-command approval gates still halt; superpowers/caveman still auto-fire in a
NON-forge repo (global untouched, since Path B disables no skill); the `/` menu shows `/devforge:*` commands and
**no** `:references:*` phantoms.

---

## Non-goals

- Disabling any bundled or plugin skill (`skillOverrides` / `disableBundledSkills`) — Path A, rejected.
- Touching `settings.json` / `install.sh`'s settings copy for skill control — Path B is command-side only.
- Migrating commands to the `.claude/skills/<name>/SKILL.md` format (a larger architecture pivot that also
  natively avoids reference phantoms) — noted as a possible future direction, NOT this plan.
- Adopting spec-kit's `handoffs` frontmatter (OQ-5, deferred).

## Context for next session

Bug: the model, on agreement to "verify", invoked a non-forge `verify` skill, not forge `/verify`. Root cause
= `disable-model-invocation: true` on all 20 forge commands makes them unreachable by the model (and drops
their descriptions from context), so the model falls to a same-intent bundled/plugin skill. Fix = **Path B**:
(1) namespace every command via a flat file under a `devforge/` subdir `.claude/commands/devforge/<name>.md`
→ `/devforge:<name>` (the emitter already writes commands flat — `claude.py:73` — so this just adds the
`devforge/` segment; NOT a nested `main.md`, which has no documented leaf-drop rule and would risk
`:main`); (2) remove the disable flag (scoped, OQ-2) so the model can invoke it; (3) relocate reference
files to `.devforge/command-refs/<name>/` (kills 28 phantom `/name:references:*` commands — same emitter
edit; needs its own gitignore/untrack per plan 56, Phase 1b). Token `devforge`, prefix-via-flat-subdir-file,
and refs-relocation are SETTLED and evidence-backed (fuzzy menu search = no typing cost; `name:` field is
display-only; documented flat-file naming rule; no reference-exclude mechanism exists). The remaining open
decisions are the disable-flag SCOPE (OQ-2), the context-cost tradeoff (OQ-1), and the plan-26 `/fix`
reconcile (OQ-3). Path A (`disableBundledSkills`/`skillOverrides`) is rejected + recorded. Nothing built;
Phase 0 is the gate.

## When resuming work

1. Re-read this file top to bottom.
2. Get maintainer sign-off at Phase 0 on OQ-1 (context cost), OQ-2 (disable-flag scope), OQ-3 (plan 26 D2).
   The naming (D1–D3) is settled — do not re-litigate it.
3. Build phase by phase. The emitter + installer changes (Phase 1, 4b) route through **python-engineer →
   python-reviewer**; every command `main.md` / `src/CLAUDE.md` / shipping-`references` edit (Phase 2, 3, 4a)
   routes through **instruction-author → instruction-reviewer + claude-code-guide**. This dual-agent-loop
   discipline is a hard requirement from the repo `CLAUDE.md`.
4. The form is the DOCUMENTED flat-file rule (`.claude/commands/devforge/<name>.md` → `/devforge:<name>`);
   Phase 1 Verify still includes a 30-second live-confirm as belt-and-suspenders, but it is not the primary
   evidence. Do NOT emit a nested `<name>/main.md` — there is no documented `main.md`-leaf-drop rule.
5. Close with the Phase 6 consumer / testForge20 e2e HARD GATE (user-driven).
