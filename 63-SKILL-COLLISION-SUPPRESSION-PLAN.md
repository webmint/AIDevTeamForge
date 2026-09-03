# 63 — `devforge:` command namespace + model-invocable (Path B)

**Status:** **✅ DONE 2026-08-07** — Phases 0–5 SHIPPED (working tree); **Phase 6 (consumer e2e) DEFERRED
by maintainer 2026-08-07 — to be tested after release, not blocking** (recipe stands below as the
validation procedure). Build included the two phases ADDED during build: **Phase 1c** (18 helper-CLI
`--references-dir` defaults, atomic with Phase 1) and **Phase 4c**
(~60 helper .py files' emitted `/name` strings namespaced + the constitution populate-guard sentinel made
multi-form — which also fixed a PRE-EXISTING silent guard bug: the with-slash guard literal never matched
the actually-shipped no-slash stub text, so all 8 preflight populate-guards were silent false-negatives).
Install ride verified: fresh
install emits ONLY `.claude/commands/devforge/` (20 commands), 28 refs at `.devforge/command-refs/`
(gitignored+untracked), stale-old-layout pruning works in both installers (scratch-fixture-verified), full
repo test suite green. Every phase built behind its dual-agent loop (python-engineer→python-reviewer /
instruction-author→instruction-reviewer + claude-code-guide); ~25 reviewer findings applied across phases.
NOTE for Phase 6: the docs give no explicit example of subdirectory namespacing under `.claude/commands/`
(only the flat-file rule + the observed colon-namespacing of the old phantom refs) — the e2e's `/` -menu
check (`/devforge:verify` appears; no `:references:*` phantoms) is the PRIMARY confirmation of the
invocation form, not belt-and-suspenders.
**Amended 2026-08-07** after src re-verification (4 findings: helper CLI refs-dir defaults; update.sh pruner
adaptation; installer comment reconcile; anchor precision).
**Amended 2026-09-03 by plan 93 (`93-MODEL-INVOCATION-CARVE-OUT-NARROWING-PLAN.md`): OQ-2's keep-7 set
narrowed to keep-4 — `grill`, `spec-check` and `fix` dropped the flag; counts 16/4. See the OQ-2
amendment block.**
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
command's on-demand reference files INTO `.claude/commands/<name>/references/` (`claude.py:70-72`).
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
   auto-relink is **PARTIAL**: the emitter rewrites only the author-relative `references/<file>.md` links in
   a command body (the rewrite lives in `scripts/lib/command_source.py` `processed`, parameterized by the
   `refs_prefix` argument passed at `claude.py:71-72`), so those relink for free when `refs_prefix` changes.
   It does NOT touch the explicit `--references-dir .claude/commands/<name>/references` literals inside the
   `/review`, `/grill`, and `/audit` command bodies, the refs-path prose in eight command headers, or the
   hardcoded `--references-dir` defaults in the three helper CLIs (`_review/_cli.py`, `_grill/_cli.py`,
   `_audit/_cli.py`). Those are in-scope work — Phase 1c (CLI defaults) and Phase 4a (command bodies).

Changes 1 and 3 are the SAME emitter edit (both rewrite command/reference output paths — today
`claude.py:73` writes `.claude/commands/<name>.md` flat and `:70` writes refs to
`.claude/commands/<name>/references/`; the edit re-points both). Change 2 is a scoped frontmatter edit.
The namespace is entirely emitter-side; the phantom fix is emitter-side PLUS the refs-path literals and
prose in eight command bodies (Phase 4a) and the 18 helper-CLI defaults (Phase 1c).

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

## Current-state anchors (verified 2026-07-15 / 2026-07-17; re-verified + extended 2026-08-07)

| Fact | Location | Note |
|---|---|---|
| The 20 emitted command names | `scripts/emitters/claude.py:49` (`_PROMOTED`) | `init-forge … spec-check … report-bug` |
| Command source layout | `src/commands/<name>/main.md` (+ `references/`) | SOURCE is a folder; the emitter FLATTENS on emit |
| Command emitted layout (TODAY) | `claude.py:73` `(commands_dir / f"{source.name}.md")` | `.claude/commands/<name>.md` — **flat file** → `/<name>` (documented flat-file rule). No `main.md` in the target tree |
| All 20 set the disable flag | all 20 `src/commands/*/main.md` (line varies 4–6) | `disable-model-invocation: true` (verified via `grep -n`) |
| `name:` field present in all 20 | `src/commands/*/main.md` | Display-only — does NOT drive the command name |
| Reference emit paths | `claude.py:70-72` (`refs_dir`, `refs_prefix`) | Writes refs to `.claude/commands/<name>/references/` → the 28 phantoms |
| Reference cross-ref rewrite | `scripts/lib/command_source.py` (`processed`), parameterized by `refs_prefix` (passed at `claude.py:71-72`) | Rewrites ONLY author-relative `references/<file>.md` links in a command body; `claude.py:23-26` is docstring prose, not the rewrite. Explicit `--references-dir` literals are NOT rewritten |
| Helper `--references-dir` defaults | `src/devforge/lib/_review/_cli.py` (`:179`, `:408`, `:1113`, `:1119`, `:1225`, `:1230`), `_grill/_cli.py` (`:206`, `:474`, `:1124`, `:1130`, `:1253`, `:1258`), `_audit/_cli.py` (`:507`, `:1149`, `:1671`, `:1677`, `:1947`, `:1952`) | 18 sites default to `.claude/commands/<name>/references` — the RUNTIME consumers of the refs path; `/review`, `/grill`, `/audit` break if Phase 1 lands without Phase 1c |
| Emitter tests | `tests/scripts/test_claude_emitter.py` | Phase 1 extends them for the new command + reference output paths |
| `claude.py --list` output | `scripts/emitters/claude.py` | Prints the canonical command NAMES; consumed by `update.sh`'s FIX-B pruner. Names-only, so the path move does NOT change it — but the pruner's staleness test depends on it (Phase 4b) |
| `update.sh` FIX-B pruner | `update.sh` ~`:590-601` (dry-run preview) + ~`:963-980` (execute) | Prunes a top-level `.claude/commands/*.md` (plus `rm -rf .claude/commands/<name>/`) only when the basename is NOT in `claude.py --list`. After the move it would KEEP every stale flat command (Phase 4b) |
| `update.sh` `--only` emit-path strings | `update.sh:89`, `update.sh:128` | Hardcode `.claude/commands/$ONLY_CMD.md (+ references/)` in the surgical-path dry-run/report text (Phase 4b) |
| Stale installer path comments | `install.sh:93`, `install.sh:227-229`, `update.sh` ~`:940` | `:93` cites `.claude/commands/<cmd>.md + references/`; `:227-229` cites `.devforge/commands/<cmd>/references/` (already wrong TODAY — refs go to `.claude/commands/<cmd>/references/`); `update.sh` ~`:940` cites `.claude/commands/<name>.md` (Phase 4b) |
| Settings copy | `install.sh:334` | `cp settings.template.json → .claude/settings.json` (settings ONLY) |
| Full-install command generation | `install.sh:318` → `scripts/generate.sh` → `scripts/emitters/claude.py` | Commands/agents are GENERATED by the emitter, NOT `cp` |
| Surgical single-command delivery | `install.sh` `--only` path (~93-120) → `claude.py --only` | Direct emitter call for one command |
| Phantom reference commands | 28 files across 11 command folders | `audit` 6, `grill`/`implement`/`review` 4 each, `configure`/`constitute`/`spec-check` 2 each, `finalize`/`fix`/`summarize`/`verify` 1 each |

**Propagation — bounded, but NOT automatic.** Few installations; the move reaches fresh installs and
`install.sh` re-runs. Moving each flat command file into `commands/devforge/` leaves the OLD
`.claude/commands/<name>.md` files AND the now-empty old `.claude/commands/<name>/references/` folders on
disk in an existing consumer on re-install — and `update.sh`'s existing FIX-B pruner will NOT remove them,
because it keeps any top-level `.claude/commands/*.md` whose basename appears in `claude.py --list` and the
NAMES are unchanged by the move. An upgraded consumer would therefore carry BOTH a stale flat `/verify` and
the new `/devforge:verify`, with the typed `/verify` resolving to the STALE command — the exact
collision/staleness defect this plan exists to fix. Adapting the pruner is REQUIRED work — see Phase 4b.

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
  emitter edit (settled; the separate pre-existing phantom-reference-commands idea is absorbed here — no
  standalone plan file was ever filed for it).
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
  **RESOLVED 2026-08-07 (maintainer): accept + offset via trim.** Measured baseline: all 20 frontmatter
  descriptions total 935 words (~1250 tokens); several are oversized (`spec-check` ~200w, `verify` ~120w,
  `review` ~110w, `finalize` ~90w); the `src/CLAUDE.md` "### Command Details" section is ~2500 words. Ratified
  handling: Phase 2 ALSO trims the descriptions of the 13 in-scope commands to ≤~40 words each (keep the
  invocation signal, cut the essay); Phase 3 shrinks those 13 commands' Command-Details entries toward
  arg-syntax pointers (descriptions now reach the model via the command surface); the 7 carved-out commands
  keep full catalog entries (the catalog stays their only model-facing awareness source). Record the measured
  net delta in Phase 3.
- **OQ-2 — scope of the disable-flag removal:** do ALL 20 commands drop `disable-model-invocation`, or only
  the model-spontaneous-intent commands (`verify` / `review` / `plan` / `fix` / `audit` / `research`),
  leaving two categories human-only — the one-time **setup** commands (`init-forge` / `generate-docs` /
  `configure` / `constitute`) and the **opt-in adversarial** checks (`grill` / `spec-check`, deliberately
  user-invoked gates the model should never auto-start)? Prefer a single uniform rule (zero-escape-hatch)
  unless there is a hard reason to split. NOTE: the `devforge:` NAMESPACE applies to all 20 regardless of
  this decision — only the disable-flag removal is scoped.
  **RESOLVED 2026-08-07 (maintainer): carve-out — 13 drop, 7 keep.** DROP the flag (model-invocable):
  `research, discover, specify, plan, breakdown, implement, pr-review, audit, review, verify, summarize,
  finalize, report-bug`. KEEP the flag (human-typed only): the setup 4 (`init-forge, generate-docs,
  configure, constitute` — one-time; a model auto-re-run mutates config/constitution), the opt-in adversarial
  2 (`grill, spec-check` — their own descriptions say "Opt-in — never an auto-gate"; auto-start would
  contradict plans 23/62), and `fix` (plan 26 D2 — see OQ-3). The zero-escape-hatch objection was weighed:
  that policy targets DISCIPLINE rules; this is an enumerated, category-named design carve-out with no
  judgment call at execution time. The maintainer's counter-question ("why disable at all if the framework is
  human-first?") was argued and resolved: the human-first guarantee lives in the in-command gates, and the
  flag's invisibility side-effect is what CAUSED the hijack bug — see OQ-4.
  **(AMENDED 2026-08-19 — the KEEP decision stands; one of its two quoted reasons no longer
  holds.)** `82-SPEC-CHECK-SUBJECT-RESOLUTION-MANDATORY-PLAN.md`'s ratified D5 sub-fork
  (a-ii) KEEPS `disable-model-invocation: true` on `spec-check`, so **the 13/7 counts are
  unchanged and this carve-out is NOT reopened** — but that plan's Phase 6 rewrote the very
  sentence quoted above: `spec-check`'s `description` no longer reads *"Opt-in — never an
  auto-gate"*, because a fresh `spec-check.md` is now a precondition of `/devforge:plan`.
  The command is still typed by the user and still never auto-invoked; what became mandatory
  is that the check RAN, and its verdict never binds. **So the REASON is replaced, not the
  decision:** keeping the flag now rests on plan 82 D5(a-ii)'s own argument plus the
  frontmatter semantics re-verified against current docs 2026-08-19
  (`https://code.claude.com/docs/en/slash-commands`, now serving the merged *"Extend Claude
  with skills"* page, whose invocation-control table records `disable-model-invocation:
  true` as *"Description not in context, full skill loads when you invoke"*) — the
  description therefore consumes no always-on context and no trim is owed. **`grill`'s half
  of the quoted reason is untouched and still accurate.**
  **(AMENDED 2026-08-26 — the KEEP decision stands; the OTHER half of the quoted reason has
  now also expired, so NEITHER quoted description survives and the sentence above naming
  `grill` as still accurate is superseded.)**
  `85-GRILL-MANDATORY-AUTO-ACCEPT-PLAN.md`'s ratified **D6 KEEPS `disable-model-invocation:
  true` on `grill`**, so **the 13/7 counts are again unchanged, this carve-out is NOT
  reopened, and no description trim is owed** — but that plan's Phase 4 rewrote `grill`'s
  `description` closing sentence from *"Opt-in — never an auto-gate."* to *"Human-typed
  only — `/devforge:breakdown` requires that it RAN, never that its disposition binds."*,
  because a grill run is now a precondition of `/devforge:breakdown`. The command is still
  typed by the user and still never auto-invoked; the blocked `/devforge:breakdown` NAMES it
  rather than running it. **So both halves of the reason are replaced, not the decision:**
  keeping the flag on `grill` now rests on D6's own argument — the skill listing has a
  budget scaling at ~1% of the context window and drops the descriptions of the
  LEAST-invoked skills first, and `grill` is by construction among them, so flipping the
  flag would buy unreliable awareness for a command the gate names anyway. Frontmatter
  semantics re-verified against current docs 2026-08-26
  (`https://code.claude.com/docs/en/slash-commands`, redirecting to
  `https://code.claude.com/docs/en/skills` — the merged *"Extend Claude with skills"* page):
  `disable-model-invocation` is *"Set to `true` to prevent Claude from automatically loading
  this skill. Use for workflows you want to trigger manually with `/name`. … Default:
  `false`"*, `description` is *"What the skill does and when to use it. Claude uses this to
  decide when to apply the skill"* and is truncated at 1,536 characters in the listing, and
  **all frontmatter fields are optional** — `name`, `argument-hint` and
  `disable-model-invocation` on `grill` are all valid and none was changed.
  **(AMENDED 2026-09-03 — the KEEP decision for `grill`, `spec-check` and `fix` is
  REVERSED by plan 93; the setup four KEEP, so the counts are now 16 model-invocable / 4
  human-typed only.)** The 2026-08-07 carve-out rested on three criteria; two expired
  (plans 82 and 85 made `/devforge:spec-check` and `/devforge:grill` mandatory
  preconditions, so "opt-in" is false for both) and the third (plan 26 D2) inherited the
  then-universal flag rather than arguing a `fix`-specific reason. Plan 93 D1 narrows the
  carve-out to ONE criterion: a one-time mutation of the framework's own basis under
  `.devforge/` with no feature scope. The 2026-08-19 and 2026-08-26 amendments above stand
  as history; their "counts are unchanged" and "no description trim is owed" clauses are
  false as of 2026-09-03 — OQ-1's ≈40-word budget now applies to the three and the trim was
  done at plan 93 Phase 1. The answer recorded above to the maintainer's counter-question —
  *"the human-first guarantee lives in the in-command gates"* (OQ-4) — is exactly the
  argument plan 93 applied to the three. Plan 85's listing-budget argument is answered, not
  refuted: the skill NAME never evicts and the `/devforge:plan` / `/devforge:breakdown`
  gates name the command. What did NOT change: Path B's namespace, the reference
  relocation, D5 (no `skillOverrides` / `disableBundledSkills`), and every gate predicate.
- **OQ-3 — plan 26 D2 reconcile:** plan `26-REINTRODUCE-FIX-PLAN.md` D2 specifies the model PROPOSES `/fix`
  and the USER invokes it (never model-invoked). If `/fix` drops the disable flag it becomes
  model-invocable — reconcile (amend plan 26 D2, or keep `/fix` a disable-flag exception). Flag it; do not
  silently override plan 26.
  **RESOLVED 2026-08-07 (maintainer): `/fix` KEEPS the flag** (it is in the OQ-2 keep-7 set). Plan 26 D2
  stands unamended — the model PROPOSES `/fix`, the user invokes it. **(AMENDED 2026-09-03
  — plan 93: `/fix` DROPS the flag, and plan 26 D2 was amended in place the same day — the
  model proposes, and on the user's agreement the model RUNS it; never self-initiated.)**
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
  `refs_prefix` (`:70-72`); `_PROMOTED` unchanged (names stay `<name>`; the emitted PATH adds the
  `devforge/` segment); `tests/scripts/test_claude_emitter.py` extended. `scripts/lib/command_source.py`
  needs NO edit — it takes `refs_prefix` as an argument.
- `src/devforge/lib/_review/_cli.py`, `src/devforge/lib/_grill/_cli.py`, `src/devforge/lib/_audit/_cli.py` —
  18 hardcoded `--references-dir` defaults (6 each) re-pointed to `.devforge/command-refs/<name>`, plus the
  covering `tests/lib/_review/`, `tests/lib/_grill/`, `tests/lib/_audit/` suites (Phase 1c, which must land
  atomically with Phase 1).
- `update.sh` — the FIX-B pruner at BOTH sites (dry-run preview ~`:590-601`, execute ~`:963-980`) adapted so
  a top-level `.claude/commands/<name>.md` bearing a canonical name counts as STALE; the `--only`
  surgical-path emit-path strings/logic at `:89` and `:128`; the stale path comment ~`:940` (Phase 4b).
- `install.sh` — the equivalent stale-path cleanup on re-install (it has no pruner today); the stale path
  comments at `:93` and `:227-229` (Phase 4b). (Command generation itself flows through
  `scripts/generate.sh` → `claude.py`, not a `cp` — see anchors.)
- `src/files/devforge.gitignore` + `scripts/devforge-state-migrate.sh` — add `.devforge/command-refs/`
  (Phase 1b, plan-56 model).
- The 20 `src/commands/*/main.md` — the scoped `disable-model-invocation` removal (Phase 2); PLUS, in the
  eight commands that name the refs path in their body, the explicit `--references-dir` literals
  (`review/main.md:156`, `review/main.md:272`, `grill/main.md:152`, `grill/main.md:230`, `audit/main.md`
  ~`:281` and ~`:403`) and
  the refs-path prose (`spec-check/main.md:28` + `:141`, `verify/main.md:18`, `summarize/main.md:18`,
  `finalize/main.md:20`, `fix/main.md:31`, `review/main.md:18` + `:159`, `grill/main.md:22` + `:155`,
  `audit/main.md:16`) — Phase 4a. The namespace itself is path-side, not a frontmatter edit.
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
(change `refs_dir` / `refs_prefix` at `:70-72`) so the author-relative `references/<file>.md` body links
relink via the existing rewrite (`scripts/lib/command_source.py` `processed`, which consumes `refs_prefix`
and needs no edit of its own). Route through the **python-engineer → python-reviewer** loop; extend
`tests/scripts/test_claude_emitter.py` for the new paths. Phase 1c ships in the SAME change-set.

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

### Phase 1c — Helper CLI `--references-dir` defaults (python)
Three helper CLIs hardcode the OLD refs path as their `--references-dir` default — 18 sites total:
`src/devforge/lib/_review/_cli.py` (`:179`, `:408`, `:1113`, `:1119`, `:1225`, `:1230`),
`src/devforge/lib/_grill/_cli.py` (`:206`, `:474`, `:1124`, `:1130`, `:1253`, `:1258`), and
`src/devforge/lib/_audit/_cli.py` (`:507`, `:1149`, `:1671`, `:1677`, `:1947`, `:1952`), each defaulting to
`.claude/commands/<name>/references`. The emitter's cross-ref rewrite does not reach them (it rewrites only
author-relative body links). Re-point all 18 to `.devforge/command-refs/<name>` and update the covering
tests. Route through the **python-engineer → python-reviewer** loop. **This phase MUST land atomically with
Phase 1 (one change-set):** the emitted reference path and the CLI defaults must agree, or `/review`,
`/grill`, and `/audit` read their reference files from a dead path at runtime.

**Verify:** `grep -rn '\.claude/commands' src/devforge/lib/` → zero; the `tests/lib/_review/`,
`tests/lib/_grill/`, and `tests/lib/_audit/` suites pass.

### Phase 2 — Frontmatter: remove the disable flag + trim descriptions (scoped per OQ-2/OQ-1) (instruction)
Remove `disable-model-invocation: true` from the 13 in-scope command `main.md` files (OQ-2 resolution:
`research, discover, specify, plan, breakdown, implement, pr-review, audit, review, verify, summarize,
finalize, report-bug`; the 7 keepers are `init-forge, generate-docs, configure, constitute, grill,
spec-check, fix`). Per the OQ-1 resolution, ALSO trim each in-scope command's `description:` to ≤~40 words
(these descriptions enter always-on model context once the flag drops — keep the invocation signal, cut the
essay; the 7 keepers' descriptions stay untouched, they remain invisible). Route **every** edit through the
**instruction-author → instruction-reviewer + claude-code-guide** loop (these ship into `.claude/`).

**Verify:** each edited frontmatter parses; the 13 in-scope commands no longer carry the flag and their
descriptions are ≤~40 words; the 7 carve-outs still carry it; `claude-code-guide` confirms the frontmatter is
valid for a model-invocable command.

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

This phase ALSO owns every refs-path string the emitter does NOT rewrite: (a) the explicit
`--references-dir .claude/commands/<name>/references` literals passed to helper verbs —
`src/commands/review/main.md:156` (+ the adjacent prose at `:159`), `src/commands/review/main.md:272`,
`src/commands/grill/main.md:152` (+ the adjacent prose at `:155`), `src/commands/grill/main.md:230`, and
`src/commands/audit/main.md` (regions
~`:281` and ~`:403`) — re-pointed to `.devforge/command-refs/<name>`; (b) the "the emitter rewrites them to
`.claude/commands/<name>/references/<file>.md` at install time" header prose in `spec-check/main.md:28`,
`verify/main.md:18`, `summarize/main.md:18`, `finalize/main.md:20`, `fix/main.md:31`, `review/main.md:18`,
`grill/main.md:22`, `audit/main.md:16`; and (c) `src/commands/spec-check/main.md:141` ("installed at
`.claude/commands/spec-check/references/formalization-guidance.md`"). All of these ship into `.claude/`, so
they route through the **instruction-author → instruction-reviewer + claude-code-guide** loop.

**Verify:** grep each old `/name` across `src/` + repo-root plans → every remaining reference is updated or an
explicitly-noted historical citation; no dangling reference. `grep -rn '\.claude/commands' src/commands/` →
zero (every hit re-pointed at `.devforge/command-refs/`).

### Phase 4c — Helper-emitted command strings (python) — ADDED 2026-08-07 (Phase 4a discovery)
The Phase 4a sweep found that the Blast radius missed a category: Python helpers EMIT user-facing strings
naming bare `/name` commands, and those strings no longer resolve post-namespace. Category A (11 emitter
files, ~26 doc-mirror sites quote their output verbatim): `plan_helper.py:949,956,1244` (`## Manual next
step — run /breakdown`, `/breakdown <plan-path>`, the `recorded at /research` caveat),
`breakdown_helper.py:3494,3501` (`run /implement`), `_specify/_render.py:351,362` (`run /plan`),
`_discover/_cmds_design.py:340` + `_research/_cmds_phase2.py:159` (`/specify "..."`),
`_verify/_report.py:171,209,245,298-306` (report Next-step lines), `_review/_report.py:542`,
`_grill/_report.py:410-434`, `_audit/_report.py:544`, `_generate_docs/_glossary.py:749`. Fix: namespace
every emitted command mention `/name` → `/devforge:name` + update tests; report the exact old→new string
pairs so the ~26 `src/commands/**` doc mirrors (deliberately left byte-true in Phase 4a, with inline
"helper's string, do not rewrite here" attributions) can be synced in a follow-up instruction-author pass.
ALSO: the constitution populate-guard sentinel `Run /constitute to populate` (hardcoded in the
constitution stub template AND 8+ preflight guard modules) is user-facing stale advice post-namespace —
update the STUB template text to `Run /devforge:constitute to populate` and make every guard match BOTH
the old and new sentinel (existing consumer installs carry the old text; a guard matching only the new
form would false-negative on them). Category B (`_implement/_wip.py` `_COMMAND_VALUE = "/implement"`
crash-recovery marker) stays UN-namespaced — internal discriminator, helper-written + helper-read only;
namespacing it would break recovery on existing wip.md files for zero user-facing gain. Route through
**python-engineer → python-reviewer**.

**Verify:** grep the 11 emitter files for bare `/name` command emissions → zero (sentinel guards match
both forms; `_wip.py` marker deliberately unchanged); helper test suites pass; a rendered `## Manual next
step` block names `/devforge:<name>`.

### Phase 4b — Stale-path cleanup + installer path reconcile (code)
`update.sh` ALREADY has the pruner (FIX-B), and left unchanged it silently KEEPS the stale files. At both
sites — the dry-run preview (~`:590-601`) and the execute block (~`:963-980`) — it walks each `*.md`
directly under `.claude/commands/` and prunes it (plus `rm -rf .claude/commands/<name>/`, the old refs dir)
only when the basename is NOT in the canonical name list from `scripts/emitters/claude.py --list`. That list
prints NAMES, which the namespace move does not change, so an upgraded consumer's old flat
`.claude/commands/verify.md` still matches a canonical name and is KEPT.

So this phase does not "add a removal" — it ADAPTS the pruner at both sites: after the move NO canonical
command lives flat at top level, so a top-level `.claude/commands/<name>.md` whose basename IS a canonical
name is by definition stale and must be pruned together with its old `.claude/commands/<name>/references/`
dir; top-level files bearing NON-canonical names keep their current behavior. Give `install.sh` the
equivalent stale-path cleanup on re-install (it has no pruner today). Re-point the `--only` surgical-path
emit-path strings and logic at `update.sh:89` and `update.sh:128`
(`.claude/commands/$ONLY_CMD.md (+ references/)`) to the `devforge/` path. Keep the fail-soft framing
(absent path / non-git → benign no-op). Reconcile the three stale path comments in the same files while they
are open: `install.sh:93` ("Delivers ONLY the emitted command (.claude/commands/<cmd>.md + references/)"),
`install.sh:227-229` (cites `.devforge/commands/<cmd>/references/` — already wrong TODAY, since refs go to
`.claude/commands/<cmd>/references/`, and its near-miss with the new `.devforge/command-refs/` home makes it
actively misleading), and the `update.sh` comment block at ~`:940` ("emitted to
`.claude/commands/<name>.md` by `scripts/emitters/claude.py`"). Route through the **python-engineer →
python-reviewer** loop (shell counts as code here).

**Verify:** a scratch consumer that previously had a flat `.claude/commands/verify.md` plus a
`.claude/commands/verify/references/` dir → run the updated installer/update → the flat file and the old
refs dir are REMOVED and only `.claude/commands/devforge/verify.md` is present, with refs under
`.devforge/command-refs/verify/`; a top-level NON-canonical `.md` is handled exactly as before;
`claude.py --list` still prints names only (semantics unchanged); absent-path / non-git case is a benign
no-op; the three reconciled comments name the paths the code actually writes.

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
edit; needs its own gitignore/untrack per plan 56, Phase 1b). **Two traps re-verified 2026-08-07.** First,
the refs relocation is NOT self-completing: the emitter rewrite (`scripts/lib/command_source.py`
`processed`, fed by `refs_prefix`) covers only author-relative `references/<file>.md` body links, so the 18
hardcoded `--references-dir` defaults in `_review/_cli.py`, `_grill/_cli.py`, `_audit/_cli.py` (Phase 1c,
which MUST land in the same change-set as Phase 1 or `/review`/`/grill`/`/audit` read from a dead path) and
the refs-path literals/prose in eight command bodies (Phase 4a) are hand-work. Second, `update.sh`'s
existing FIX-B pruner keeps any top-level `.claude/commands/*.md` whose basename is in `claude.py --list`,
and the move leaves the names unchanged — so without the Phase 4b pruner adaptation an upgraded consumer
keeps BOTH a stale flat `/verify` and the new `/devforge:verify`, with the typed `/verify` hitting the stale
one. Token `devforge`, prefix-via-flat-subdir-file,
and refs-relocation are SETTLED and evidence-backed (fuzzy menu search = no typing cost; `name:` field is
display-only; documented flat-file naming rule; no reference-exclude mechanism exists). **Phase 0 RATIFIED
2026-08-07:** OQ-2 = carve-out (13 drop the flag; 7 keep: setup 4 + `grill` + `spec-check` + `fix`); OQ-3 =
`/fix` keeps the flag, plan 26 D2 stands; OQ-1 = accept + offset (trim in-scope descriptions to ≤~40 words in
Phase 2, shrink their Command-Details entries in Phase 3, record the measured delta). Path A
(`disableBundledSkills`/`skillOverrides`) is rejected + recorded.

## When resuming work

1. Re-read this file top to bottom.
2. Get maintainer sign-off at Phase 0 on OQ-1 (context cost), OQ-2 (disable-flag scope), OQ-3 (plan 26 D2).
   The naming (D1–D3) is settled — do not re-litigate it.
3. Build phase by phase. The emitter, gitignore/untrack, helper-CLI, and installer changes (Phases 1, 1b,
   1c, 4b) route through **python-engineer → python-reviewer**; every command `main.md` / `src/CLAUDE.md` /
   shipping-`references` edit (Phases 2, 3, 4a) routes through **instruction-author → instruction-reviewer +
   claude-code-guide**. This dual-agent-loop discipline is a hard requirement from the repo `CLAUDE.md`.
   **Phase 1 and Phase 1c ship as ONE change-set** — the emitted reference path and the three helper CLIs'
   `--references-dir` defaults must agree, or `/review`, `/grill`, and `/audit` break at runtime.
   **Do not skip Phase 4b's pruner adaptation** — `update.sh`'s FIX-B pruner (~`:590-601` dry-run,
   ~`:963-980` execute) keeps stale flat command files by default, because it tests basenames against the
   name-only `claude.py --list` output.
4. The form is the DOCUMENTED flat-file rule (`.claude/commands/devforge/<name>.md` → `/devforge:<name>`);
   Phase 1 Verify still includes a 30-second live-confirm as belt-and-suspenders, but it is not the primary
   evidence. Do NOT emit a nested `<name>/main.md` — there is no documented `main.md`-leaf-drop rule.
5. Close with the Phase 6 consumer / testForge20 e2e HARD GATE (user-driven).
