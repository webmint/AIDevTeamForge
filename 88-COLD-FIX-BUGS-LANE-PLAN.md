# 88 — The cold-fix lane: `bugs/NNN-*.md` becomes the third `/devforge:fix` findings source

**Status:** **Phase 0 RATIFIED 2026-08-26 by the maintainer — D1–D7 and OQ-1–OQ-7 all decided, every item AS RECOMMENDED, nothing left open.** The three named forks were picked explicitly: **D3 = fork 1 (a)** (extend `implement_helper wip-commit` with a final-commit mode) **+ fork 2 (i)** (wrapper keeps `[TICKET-ID] - <title>`, the `[develop] - <title>` fallback string seen and accepted); **D4 = (b)** the `close-bug` helper verb over a new `_shared/bug_file.py` function, so **Phase 1 carries TWO deliverables**; **D6 = reading (i)** — the rubric lives in `src/CLAUDE.md`, `/devforge:report-bug` Rule 8 stays byte-unchanged and gains no forward pointer. **Phases 1–4 are ✅ DONE (build) 2026-08-26** — Phase 1 `92592c5`, Phase 2 `bf0c4b9`, Phase 3 `7ec8f69`, Phase 4 `d09b7e2`. **✅ PLAN CLOSED 2026-08-27 by maintainer statement — *"the test is a separate story — mark it as done."*** ⚠ **Phase 5 consumer e2e is DEFERRED AS A SEPARATE EFFORT — NOT WAIVED and NOT RUN.** The close covers the BUILD; it is not a pass, and no sentence in this file may be read as one — everything built is **build-verified, NOT consumer-validated**, and the cold lane has never been observed end to end. The three known-answer anchors in `### Phase 5` remain the recipe whenever that effort runs, **with anchors 1 and 2 scored as a PAIR**. Every counter-argument recorded before ratification survives verbatim; see `## Phase 0 ratification record`.

⚠ **This plan SUPERSEDES `55-STANDALONE-BUG-FIX-LANE-PLAN.md`** (DEFERRED 2026-07-10), which designed this same lane and which this plan's own sweep list did NOT name — it was found by Phase 4's `bugs/` sweep and marked superseded 2026-08-26. Two things plan 55 designed are **NOT built** (its CBM blast-radius tripwire; decoupled standalone firing of stage-coupled floor gates), and **its instrumentation trigger — 3–4 measured bugs — was never satisfied**. Read its note before citing this plan as evidence about the middle band.
**Branch:** `develop-2.0-init`
**Created:** 2026-08-25.

This plan document contains no private-client identifiers and is intended to be
**committed normally**, unlike the deliberately-untracked plans 73/74/75.

## Evidence constraint

The two UNTRACKED private-client evidence files at repo root
(`81-EVIDENCE-V2-BENCHMARK-RUN.md`, `77-EVIDENCE-DISCOVERY-TO-LOCK-INVERSION.md`) are
neither read nor cited by this plan, and no phase may import from them. This plan's
evidentiary base is (a) the live files enumerated in `## Verified mechanics` and (b) one
maintainer statement dated 2026-08-25 recorded in `## Origin`. **There is no incident
artifact, no failing run, and no measurement** — say so wherever this plan is summarized.

---

## Origin — a confirmed friction and a confirmed dead end, decided 2026-08-25

Two facts, neither disputed, and the second is the one nobody had named:

**1. A cold bug has no proportional route in v2.** v1 shipped a lightweight `/fix` — a
free-text small-bug workflow, recorded in `CHANGELOG.md` as *"lightweight bug-fixing
workflow for small, localized bugs (1-5 files)"* with a *"Scope guard — automatically
recommends `/specify` if bug affects more than 5 files"* (fact 24). Plan 21 deliberately
DROPPED it, and plan 26 reintroduced `/devforge:fix` as something else entirely: a gated
remediation of pipeline-surfaced findings inside the post-`/devforge:implement` /
pre-`/devforge:summarize` window. Both moves were correct on their own terms. Their
combined consequence is that a **cold** bug — one noticed independently, outside any
feature's fix window — has exactly two routes today: hand-fix it (bypassing every gate the
framework exists to impose) or take it through the full ~10-command chain
(`/devforge:research` → `specify` → `spec-check` → `plan` → `breakdown` → `implement` →
`review` → `verify` → `summarize` → `finalize`), which is disproportionate for a one-file
defect. `/devforge:fix`'s own empty-list STOP says this out loud today: *"or (for a cold bug
noticed independently) hand-fix it or take it through the full chain"* (fact 7).
**The maintainer confirmed on 2026-08-25 that this friction is already observed** — this is
not a predicted cost.

**2. `bugs/NNN-*.md` files have no consumer.** Two commands WRITE them —
`/devforge:report-bug` (`Source: manual`) and `/devforge:verify` PHASE 9 (`Source: verify`,
NEEDS WORK only) (fact 14) — and **nothing reads them**. `/devforge:report-bug`'s own forward
pointer sends the user to `/devforge:research` or `/devforge:specify` (fact 13a), but
`src/commands/research/main.md` contains **zero** occurrences of `bugs/` (fact 15): the
pointer names a command that does not know the file exists. `storage-rules.md` states the
resolution path plainly — *"the user edits `**Status**: Fixed` after resolving the issue (the
`Open → In Progress → Fixed` lifecycle is not driven by any command)"* (fact 16). So the
corpus grows and nothing ever consumes or closes it.

**The ratified direction, chosen by the maintainer 2026-08-25 over a named alternative:**
`bugs/NNN-*.md` becomes the **THIRD findings source** for `/devforge:fix`, consumed in a new
**feature-less "cold mode"** that ends in one clean `fix(scope):` commit and one Status flip.
The main pipeline is untouched — the light lane is contained inside one command.

### The rejected alternative, with its reasoning (recorded so it is not re-proposed)

The alternative was a **"light lane through the main pipeline"** — a `minor` classification
that a feature could carry, causing `/devforge:research` / `specify` / `plan` / `breakdown` to
emit thinner artifacts. It was rejected on two independent grounds, either of which decides it:

- **Ceremony cost lives in GATE COUNT, not artifact size.** The ~10-command chain's cost is
  ten command invocations, each with its own preflight, its own approval or hard gate, and its
  own artifact commit — `/devforge:plan` alone blocks on a fresh `/devforge:spec-check` report
  whose recorded spec hash still matches `spec.md`. Shrinking each artifact leaves all ten
  gates standing. A lane that does not remove gates does not remove the friction that was
  observed.
- **An "if minor" branch inside the main chain is an escape hatch.** This repo's
  zero-escape-hatch meta-rule forbids exactly the shape it would take: a rule with an
  `unless trivial` / `when minor` clause and a judgment call at its head. Every gate the lane
  skipped would be skippable by mislabelling one field. **Containing the light lane in a
  separate command with a mechanical trigger (D1) keeps the main chain's rules absolute.**

---

## What is actually being added

Three things. **Phase 0 ratifies each independently; a future session must not read any one as
depending on the others.**

1. **A cold mode inside `/devforge:fix`** (Phase 2) — a second front half, entered on an
   explicit `bugs/NNN-<slug>.md` argument (D1), that skips the three feature-bound sub-phases
   (feature resolution, the window gate, and the findings read — D2), code-confirms the
   captured bug against live code before remediating (D1), and then joins the EXISTING back
   half unchanged (OQ-2). **Instruction-only.**
2. **One commit-mode extension** (Phase 1) — the cold lane's terminal commit is a clean
   conventional `fix(scope):` commit rather than a `[WIP]` one, because no
   `/devforge:finalize` run will ever squash it (D3). **This is the only Python the plan
   builds** — except for D4's fork, which if ratified as recommended adds a second small
   Python surface in the same phase (see D4, which records the divergence from this framing
   rather than hiding it).
3. **A three-arm conversational routing rubric** (Phase 3) — `src/CLAUDE.md`'s existing
   two-arm "Conversational fix-or-file offer" grows a third arm for the cold code-confirmed
   defect (D6). **Advisory, never a gate.**

**⚠ Two honest bounds that must survive into every emitted sentence:**

- **The cold lane weakens no gate.** Cold mode drops the two gates that are *meaningless
  without a feature* — feature-dir resolution and `in-fix-window` — plus the feature-bound
  findings READ that is not a gate at all (`read-findings` always exits 0), and keeps every
  gate that is about the CODE: the setup-chain preflight, scope-aware verify with self-repair,
  the four-reviewer panel, the forcing-functions gate, and the two-stage human hard gate
  (OQ-2).
  **If Phase 0 declines OQ-2, this plan's whole proportionality claim changes and must be
  re-argued, not adjusted.**
- **The routing rubric is model judgment, not a mechanism.** D6 makes the model OFFER the
  right route; nothing checks that it did. The only MECHANICAL net in this plan is D5's
  in-command bounce, which fires after the user has already typed `/devforge:fix`.

---

## Verified mechanics (2026-08-25)

Every row was confirmed by opening the named file or by the named fetch. **The quoted token is
the anchor; the digit is a dated hint** — this repo has documented anchor rot, so grep the
string, never the `:NNN`.

⚠ **Dated caution, added 2026-08-26: `src/CLAUDE.md` has been edited since these facts were
gathered** (`/devforge:grill` became mandatory before `/devforge:breakdown`), so the text
surrounding facts **28, 29, 29a and 29b** has moved even where their quoted strings have not.
**Those four rows were verified 2026-08-25 and Phase 3 MUST re-verify all four against the LIVE
file before editing it** — re-derive from what is there, never from a pre-computed position.
The rows themselves are deliberately left as-recorded (not renumbered, not rewritten): they are
the dated observation Phase 3 checks against, and silently refreshing them would destroy the
only record of what changed.

| # | Fact | Evidence |
|---|------|----------|
| 1 | `/devforge:fix`'s frontmatter `description` closes *"Never invents a defect, never accepts a free-text bug description, never writes `bugs/`."* | `src/commands/fix/main.md:3` |
| 2 | Its `argument-hint` is `"[spec-file/feature-dir]"` and `disable-model-invocation: true` is set | `src/commands/fix/main.md:4`, `:5` |
| 3 | `allowed-tools` is **twelve Bash-scoped entries and nothing else** — five `fix_helper` verbs, `artifact_helper commit-artifacts`, four `implement_helper` verbs, `git diff`, `git -C * diff`. **No `Read`, `Write` or `Edit` entry**, although the body directs the orchestrator to use the Write tool at PHASE 4 step 2 | `src/commands/fix/main.md:6`–`:18`; `:236` |
| 4 | **The never-writes-`bugs/` claim appears at FOUR sites in that one file** — the frontmatter description (`:3`), the third intro paragraph (*"And it never writes or closes `bugs/` files"*, `:27`), `## Outputs of this command` (*"does NOT write or close any `bugs/` file"*, `:42`), and Rule 7 (*"writes or closes NO `bugs/` file (D4 …)"*, `:317`) | `src/commands/fix/main.md` |
| 5 | The front half is PHASE 0.1 preflight → 0.2 feature resolution → 0.3 `in-fix-window` + `$WORKDIR` → 0.4 findings intake; PHASE 1 triage + D7 bounce | `src/commands/fix/main.md:70`–`:194` |
| 6 | **The case-3 conversational item is orchestrator-composed, not helper-parsed** — shape `{title, severity, files_cited, evidence, source: "conversation"}`, with `files_cited` *"set to the file(s) you read to confirm it"* and the standing instruction *"Do NOT fabricate this item: it exists only when the user pointed out the defect AND you confirmed it from the actual code"* | `src/commands/fix/main.md:124` |
| 7 | **The command already routes cold bugs away in prose**: the empty-list STOP reads *"or (for a cold bug noticed independently) hand-fix it or take it through the full chain"* | `src/commands/fix/main.md:126` |
| 8 | PHASE 6's approve arm calls `implement_helper wip-commit` in **task-less mode** — only `--files` and `--title`, omitting `--task-file`/`--index`/`--number` | `src/commands/fix/main.md:282`–`:289` |
| 9 | `_compose_message(is_wrapper, ticket_id, title, number, attribution, fix_mode=False)` is the SINGLE message composer. With `fix_mode=True` it emits `"[WIP] fix: {title}"` (standalone) or `"[{ticket_id}] - {title}"` (wrapper), with no `(Task NNN)` suffix | `src/devforge/lib/_implement/_cmds_commit.py:209`–`:237` |
| 10 | In `cmd_wip_commit`: `fix_mode = task_absent`; **wrapper commits target `workspace.source_root` and standalone targets `workspace.install_root`**; the ticket is `_extract_ticket_id(branch)` off the SOURCE branch with the **full branch name as fallback** when no `[A-Z]+-[0-9]+` token matches; attribution is suppressed in wrapper mode (`message_attribution = "" if is_wrapper else attribution`); staging is per-path via `git -C <repo> add --`, **never `git add -A`** | `_cmds_commit.py:475`, `:487`–`:512`, `:515`–`:534`, `:191`–`:206`, `:240`–`:249` |
| 11 | `wip-commit` **always clears `.devforge/wip.md` in the INSTALL root** after a successful commit (non-fatal on error) | `_cmds_commit.py:556`–`:564` |
| 12 | Mixed mode — some but not all of `--task-file`/`--index`/`--number` — is rejected with `EXIT_ERR` and a message naming the missing flags | `_cmds_commit.py:459`–`:473` |
| 13 | **The live bug-file schema**, written by `_format_bug`: `**Status**: Open`, `**Severity**`, `**Source**`, `**Feature**`, `**AC**`, `**Reported**`, and an **empty `**Fixed**: `** line; then `## Description`, `## Expected Behavior`, `## Actual Behavior`, `## File(s)` (a `\| File \| Detail \|` table), `## Evidence`, `## Related Issues`, `## Fix Notes` whose body is the literal `_Filled in after resolution._`. The same shape is documented in `storage-rules.md` | `src/devforge/lib/_shared/bug_file.py:190`–`:245`; `src/devforge/storage-rules.md:329`–`:376` |
| 13a | `--file` is **OPTIONAL** on `report_bug_helper write-bug`; when absent the File(s) table renders the single row `\| (unknown) \| (see evidence) \|`. `/devforge:report-bug`'s closing pointer names `/devforge:research` and `/devforge:specify` — and nothing else | `src/commands/report-bug/main.md:42`, `:88`; `bug_file.py:226` |
| 14 | **Exactly two `bugs/` producers exist**: `/devforge:report-bug` (`Source: manual`) and `/devforge:verify` PHASE 9 `file-bugs` (`Source: verify`, NEEDS WORK only, one file per elected issue) | `storage-rules.md:378`–`:380`; `src/commands/verify/main.md:25`, `:360`–`:371` |
| 15 | **`bugs/` has no consumer.** A `bugs/` grep across `src/commands/` returns hits in exactly six files — `report-bug` (11), `verify` (6), `fix` (5), `configure` (2), `implement` (1), `review` (1). **`src/commands/research/main.md` returns ZERO** | repo grep, 2026-08-25 |
| 16 | `storage-rules.md`'s `### How Bug Files Are Resolved` states *"the `Open → In Progress → Fixed` lifecycle is not driven by any command"* — **D4 falsifies this sentence** | `storage-rules.md:383` |
| 17 | `storage-rules.md`'s File Lifecycle `fix` line closes *"(no bugs/ files written either way)"* — **D4 falsifies this clause** | `storage-rules.md:219` |
| 18 | **`/devforge:report-bug` Rule 8 forbids exactly what D6's arm 2 and Phase 3 propose**: *"**Never call `/devforge:fix` from here** — … It does not propose, invoke, or chain into `/devforge:fix`; a bug captured here is addressed later through the normal pipeline."* ⚠ See D6's `Collision` block | `src/commands/report-bug/main.md:101` |
| 19 | **The framework-wide "the lifecycle is manual" claim sits at THREE sites in `/devforge:report-bug`, not one** — the intro (*"The `Open → In Progress → Fixed` lifecycle in each bug file is maintained MANUALLY by whoever works the bug"*, `:15`), PHASE 4's close (*"the `Open → In Progress → Fixed` transitions in the bug file are made manually"*, `:90`), and **inside Rule 7 itself** (*"The `Open → In Progress → Fixed` lifecycle is maintained manually; this command never edits an existing bug file"*, `:100`). **D4 falsifies the framework-wide clause at all three** | `src/commands/report-bug/main.md:15`, `:90`, `:100` |
| 19a | **The clauses wrapped around them are about `/devforge:report-bug` ITSELF and stay TRUE** — Rule 7's heading *"**Never closes or advances a bug**"*, *"only ever writes a fresh `Open` record"*, *"this command never edits an existing bug file"*, and the intro's *"never touches the `bugs/` lifecycle beyond writing a fresh `Open` file"*. **So Rule 7 needs a SPLIT, not a deletion**: one clause inside it is false, its neighbours are not | `src/commands/report-bug/main.md:15`, `:100` |
| 19b | ⚠ **The three sites share no common wording** — `:15` and `:100` say *"maintained manually"*, `:90` says *"made manually"*, so a `maintained manually` grep **MISSES `:90`**. The greppable anchor that catches all three is the arrow string `Open → In Progress → Fixed` | repo grep, 2026-08-25 |
| 20 | `_fix/_cli.py`'s `_SUBCOMMAND_REGISTRY` holds five verbs (`preflight`, `read-findings`, `resolve-scope`, `in-fix-window`, `write-seed`) and carries a **documented three-step extension point**: write `cmd_<verb>`, append the `(kebab-name, help, cmd_func)` triple, add the argument block in the `elif` chain of `_register_subcommands` | `src/devforge/lib/_fix/_cli.py:286`–`:335`, `:358`–`:498` |
| 20a | **`read-findings` cannot run without a feature dir**: `--feature` is `required=True` on the verb, `cmd_read_findings` exits 2 on an empty value, and `read_findings(feature_dir, …)` resolves `review.md` / `verification.md` relative to it. **So PHASE 0.4 is as feature-bound as PHASE 0.3 is, and `$WORKDIR/findings.json` is never produced on a cold run** | `src/devforge/lib/_fix/_cli.py:377`–`:386`, `:89`–`:94`; `_fix/_findings.py:217` |
| 21 | **The seed path is feature-dir-derived with no feature-less form**: `out_path = os.path.join(feature_dir, "fix-seed.json")`, and `--feature-dir` is `required=True` on the verb | `src/devforge/lib/_fix/_seed.py:156`; `_fix/_cli.py:428`–`:437` |
| 22 | `in_fix_window(feature_dir)` reads `<feature_dir>/summary.md`, `<feature_dir>/spec.md` and `<feature_dir>/tasks/*.md`. **A feature-less call has no meaning** — with no such dir it returns `{"in_window": false, "reason": "no_tasks_dir"}`, i.e. a cold run would be gated OUT by construction | `src/devforge/lib/_fix/_window.py:129`–`:203` |
| 23 | **The advisory-nudge precedent**: `/devforge:plan`'s PHASE-4 stakes-hint is *"ADVISORY and NON-BLOCKING: it never blocks the approve flow, never gates `/devforge:breakdown`, and the user is free to ignore it"* | `src/commands/plan/main.md:640` |
| 24 | **v1's numeric scope cap survives only in `CHANGELOG.md`**: *"`/fix` command — lightweight bug-fixing workflow for small, localized bugs (1-5 files)"* and *"Scope guard — automatically recommends `/specify` if bug affects more than 5 files"*. ⚠ `.claude/commands/` in this working tree holds only `review-helper.md` and `release.md`, so the v1 file is reachable only from git history, **not from the tree** | `CHANGELOG.md:727`, `:730`; `.claude/commands/` listing 2026-08-25 |
| 25 | **Plan 26 explicitly chartered D4's verb as a future plan's work**: *"A `bugs/` `Open → Fixed` consumer (a `close-bug` verb) — explicitly NOT built (D4 chose findings-only …). A future plan could add a `close-bug` verb (to `_verify` or a new helper) if the manual close proves painful in practice."* **This plan is that future plan** | `26-REINTRODUCE-FIX-PLAN.md:369` |
| 26 | Plan 26's D2 ban, verbatim: *"`/fix` is NOT a cold general bug-fixer and does NOT accept a free-form 'describe a bug' input: a standalone cold bug a developer notices independently still goes hand-fix / full-chain."* Its `## Out of scope` repeats it as a bullet | `26-REINTRODUCE-FIX-PLAN.md:21`, `:376` |
| 27 | Plan 26's window rationale, verbatim: *"in-window the feature's WIP commits are still open, so an in-place `/fix` … lands cleanly as another `[WIP]` commit on the open unit. Once `/summarize`/`/finalize` squashes and seals the feature, fixing in place would corrupt a sealed unit"* | `26-REINTRODUCE-FIX-PLAN.md:325` |
| 28 | `src/CLAUDE.md`'s `### Conversational fix-or-file offer` is a single paragraph gating on `fix_helper in-fix-window`, requiring *"All three conditions … (user-raised AND code-confirmed AND in-window)"*, and closing *"if any is absent … offer only `/devforge:report-bug`, never `/devforge:fix`"* | `src/CLAUDE.md`, `### Conversational fix-or-file offer` |
| 29 | **`src/CLAUDE.md`'s `#### /devforge:fix` catalog entry is ONE paragraph carrying FIVE clauses this build falsifies**, not the two a narrow reading finds: (a) *"NOT a linear pipeline step and NOT a cold bug-fixer"*; (b) the trigger list closing *"all inside the post-`/devforge:implement`/pre-`/devforge:summarize` window"*; (c) *"Consumes those already-diagnosed findings (`specs/[feature]/review.md` / `specs/[feature]/verification.md`)"* — two sources where there will be three; (d) *"Writes NO `bugs/` file (`/devforge:report-bug` is the separate 'defer' arm)"*; (e) *"bounces to `/devforge:specify` instead"* and the entire `fix-seed.json` sentence following it — true of the **in-window** bounce only, once D5 ships. Its heading also fixes the argument form as `[spec-file/feature-dir]` | `src/CLAUDE.md:111`–`:112` |
| 29a | **That entry is load-bearing for the model by `src/CLAUDE.md`'s own statement**: the seven human-typed-only commands (`/devforge:fix` among them) *"carry a full description: this section is the only place the model sees what they do"* — so a partially-updated entry **contradicts, in the same file, the three-arm rubric D6 adds** | `src/CLAUDE.md:79` |
| 29b | ⚠ **A SECOND, non-catalog site in the same file repeats the window claim**: the workflow prose says `/devforge:fix` is a proposal-only loop *"run inside the post-`/devforge:implement`/pre-`/devforge:summarize` window"* and *"never appears in the arrow chain above"*. **The arrow-chain half stays true; the window half does not.** A sweep scoped to the catalog paragraph alone misses it | `src/CLAUDE.md:55` |
| 30 | `artifact_helper commit-artifacts` *"stages ONLY the named path and makes a `[WIP] …` commit in the INSTALL repo (never the wrapper-mode source/product repo)"*, is FAIL-SOFT (warn + exit 1 on git failure), and exits 0 silently on nothing-to-commit | `src/commands/fix/main.md:176` |
| 31 | `CHANGELOG.md` carries a `## [Unreleased]` section today whose first subsection is `### Added` | `CHANGELOG.md:8`, `:10` |
| 32 | `/devforge:specify` *"blocks until a pending research or discover handoff exists in a feature directory"* — **so a cold bounce cannot name `/devforge:specify` as its entry point**; the chain must start at `/devforge:research` | `src/CLAUDE.md`, the research/discover precondition paragraph |

### Claude Code authoring surface, verified against current docs

Fetched 2026-08-25 from `https://code.claude.com/docs/en/slash-commands` (which redirects to
the skills page — custom commands were merged into skills, and the page states *"A file at
`.claude/commands/deploy.md` and a skill at `.claude/skills/deploy/SKILL.md` both create
`/deploy` and work the same way. Your existing `.claude/commands/` files keep working."*).
**Cited here so a future author re-verifies rather than trusting this file.**

- **`allowed-tools` is a PRE-APPROVAL grant, not a restriction.** Verbatim: *"Tools Claude can
  use without asking permission during the turn that invokes this skill. The grant clears when
  you send your next message. Accepts a space- or comma-separated string, or a YAML list."*
  **This is why fact 3 is not a defect** — `/devforge:fix` uses the Write tool at PHASE 4
  without a `Write` entry, and that works; the entry would only have removed a permission
  prompt. **Consequence for Phase 2: any new `allowed-tools` line is an ergonomics choice, not
  a correctness requirement, and a missing one cannot break the command.**
- **`disallowed-tools` is the restricting field**, verbatim *"Tools removed from Claude's
  available pool while this skill is active."* This plan proposes none.
- **`disable-model-invocation`**, verbatim: *"Set to `true` to prevent Claude from
  automatically loading this skill. Use for workflows you want to trigger manually with
  `/name`. Also prevents the skill from being preloaded into subagents."* Default `false`.
  **OQ-6 keeps it `true`.**
- **`argument-hint`**, verbatim: *"Hint shown during autocomplete to indicate expected
  arguments."* It is a display string only — **widening it (Phase 2) changes autocomplete text
  and nothing else; it neither validates nor restricts `$ARGUMENTS`.**
- **The docs say NOTHING about a per-command file-write restriction.** There is no frontmatter
  field that could confine cold mode to one `bugs/` file; **D4's narrowness is enforced by the
  helper's contract (D4's recommended arm) or by prose alone (its alternative), never by the
  Claude Code surface.**

---

## Decisions — ALL RATIFIED 2026-08-26, every one as recommended

Each carries the rule, the alternatives, the reasoning, and the strongest counter-argument.
**The counter-arguments are load-bearing: a decision ratified with its counter-argument deleted
cannot be re-opened honestly later** — so every one below is retained verbatim, unedited by the
ratification. **Phase 0 is closed; nothing in this section is open.** The `RECOMMENDED RULE`
lead on each decision is the wording that was ratified; where a decision named a fork, the
picked arm is in its heading marker.

### D1 — Cold-mode trigger + intake: an explicit bugs-file argument, code-confirmed before remediation *(RATIFIED 2026-08-26 — as recommended)*

**RECOMMENDED RULE.** Cold mode is entered by, and only by, an explicit bugs-file argument:
`/devforge:fix bugs/NNN-<slug>.md`. The trigger is **mechanical** — `$ARGUMENTS` names a path
under `bugs/`, or it does not. No judgment call, no heuristic, no severity threshold.

**Plan 26's D2 is EXTENDED, not reversed.** D2 banned a *free-text bug description* (fact 26).
A `bugs/NNN-*.md` file is not free text: it is a **written finding** with a title, a severity,
an evidence section and a file table (fact 13), produced by a command whose whole job is
structured capture. So `/devforge:fix`'s defining sentence — *"consumes findings, never invents
them"* — stays **literally true** with `bugs/` added as a third source, and the ban on typing a
bug description into the command survives untouched. **⚠ Phase 2 must not weaken the ban's
wording while widening the source list; the two are separable and only the source list moves.**

**The confirmation duty, and it is not optional.** A bug FILE is a **capture**, not a
confirmation — `/devforge:report-bug` *"reads no source code to confirm the defect"* by design
(fact 13a's neighbouring rule). So cold-mode triage MUST code-confirm the bug against live code
before any remediation, exactly as the case-3 conversational path already requires (fact 6):
read the cited file(s), quote the offending code, and only then proceed. **A bug file that
cannot be confirmed against live code does not become a working-list item** — see OQ-1 for the
stop.

**Alternatives considered:**

- *(a) A `--cold` flag with a free-text description.* REJECTED — it is plan 26 D2's banned
  intake wearing a flag, and it would make `/devforge:fix` a defect INVENTOR the first time a
  user typed a hunch into it.
- *(b) Auto-detect: no `specs/` dir in range ⇒ cold.* REJECTED — an inferred mode is a mode the
  user cannot see they are in, and the inference silently flips on an unrelated repo state.
- *(c) A separate command (`/devforge:cold-fix`).* Recorded as the real alternative, not
  strawmanned: it would keep `/devforge:fix`'s four never-writes-`bugs/` claims (fact 4)
  byte-true and give the cold lane its own frontmatter. It is NOT recommended because it would
  duplicate the entire back-half orchestration prose — PHASES 2–7 of `fix/main.md` — which is
  precisely the copy-vs-caller staleness plan 26's D6 exists to prevent. **Two entry points
  over one engine is the pattern; two prose copies of the engine is not.**

*Counter-argument, recorded:* a path-shaped trigger is invisible in the frontmatter's
`argument-hint` until Phase 2 widens it, and a user who types `/devforge:fix` bare on a cold
day gets the in-window path's "no findings" STOP instead of a pointer to the cold lane.
**Accepted as a real ergonomics cost**; the mitigation is a one-clause widening of the
empty-list STOP (fact 7) in Phase 2, and it is cheap precisely because that sentence already
talks about cold bugs.

### D2 — Cold mode skips feature resolution (0.2), the window gate (0.3) and the findings read (0.4) *(RATIFIED 2026-08-26 — as recommended, all three bypassed)*

**RECOMMENDED RULE.** On the cold path the orchestrator runs PHASE 0.1's preflight and then
goes straight to establishing `$WORKDIR` and reading the bug file. **Three sub-phases do not
run: PHASE 0.2's feature-dir resolution, PHASE 0.3's `in-fix-window` call, and PHASE 0.4's
`read-findings` call.**

**Why 0.4 is on that list — it is forced, not chosen.** `fix_helper read-findings` takes
`--feature` as `required=True` (fact 20a) and resolves `review.md` / `verification.md` relative
to it. **With no feature dir there is nothing to pass**, so 0.4 cannot run on the cold path any
more than 0.3 can. Consequently **no `$WORKDIR/findings.json` is ever written in cold mode**,
and PHASE 1's triage prose — which today reads *"the `items` from `$WORKDIR/findings.json`"* —
does not describe the cold path.

**What replaces it:** the cold-mode working list is **constructed directly by the orchestrator**
as a SINGLE item in the case-3 shape already documented at PHASE 0.4 (fact 6) —
`{title, severity, files_cited, evidence, source}` — composed from the bug file's own fields
plus D1's code-confirmation, and written straight to `$WORKDIR/items.json` with the Write tool.
**This is the same mechanism the case-3 conversational defect already uses** (fact 6 instructs
the orchestrator to compose that item by hand and append it), so cold mode introduces no new
item shape and no new scratch file — it reuses an existing carve-out rather than inventing one.
`resolve-scope` then consumes `$WORKDIR/items.json` unchanged. **The `source` value for a cold
item is OQ-1's territory**, not decided here.

**This is an explicit, dated amendment to plan 26's in-window rule** (fact 27), and Phase 4
must write it INTO plan 26 rather than leaving plan 26 asserting a rule this build breaks. The
amendment is narrow, and its narrowness is the whole argument:

> Plan 26's window rule binds **feature-scoped** runs. Its rationale (fact 27) is entirely
> about not fixing in place inside a **sealed feature unit** whose WIP commits have been
> squashed. **A cold run has no feature unit at all** — it is not fixing inside one, sealed or
> open. The rule is not weakened; its subject simply does not exist on this path.

**The mechanics force it anyway** (fact 22): `in_fix_window` reads `<feature_dir>/tasks/`,
`spec.md` and `summary.md`. Called with no feature dir it returns
`{"in_window": false, "reason": "no_tasks_dir"}` — so a cold run that DID call it would be
gated out by construction. **Keeping the call and ignoring its answer would be worse than not
calling it**: it would put a gate in the transcript that the spec then instructs the model to
disregard, which is exactly the escape-hatch shape this repo forbids.

**Alternatives considered:**

- *(a) Call `in-fix-window` and treat `no_tasks_dir` as a PASS.* REJECTED per the paragraph
  above — a gate with a documented ignore-arm is not a gate.
- *(b) Resolve a feature dir opportunistically when the bug file's `**Feature**` field names
  one.* REJECTED for this build and recorded: a `Source: verify` bug DOES carry a real
  `**Feature**` path (fact 13), so this is tempting — but binding a cold run to that feature
  re-imports the sealed-unit question the cold lane exists to avoid, and OQ-5 answers it
  without the binding.

*Counter-argument, recorded, and it is the strongest one against this plan:* the window gate is
the mechanism that stops `/devforge:fix` from writing into a feature whose `/devforge:implement`
run is still mid-flight (fact 22 names that arm — `not_all_tasks_complete` — and
`_window.py`'s own comment says a `wip-commit` landing there *"would stomp /implement's
.devforge/wip.md"* `crash-recovery marker, so the window is strictly post-/implement`; the
comment wraps across two lines, so **the greppable contiguous substring is the first half
only**). **A cold run skips that protection.** The mitigation is in D3's
build note (`--final` must not clear the wip marker) and it is a mitigation, **not an
equivalence** — a cold fix run concurrently with a live `/devforge:implement` is an unguarded
state this plan accepts and records rather than closes.

### D3 — The commit path: one clean `fix(scope):` commit, via an extended `wip-commit` *(RATIFIED 2026-08-26 — fork 1 (a), fork 2 (i))*

**RECOMMENDED RULE.** A cold fix ends in exactly **one clean Conventional-Commits
`fix(scope): <description>` commit — no `[WIP]` prefix.** The reason is mechanical, not
stylistic: `[WIP]` commits exist to be squashed by `/devforge:finalize`, and
`/devforge:finalize` is gated on a feature spec being Complete. **A cold run has no feature and
no finalize, so a `[WIP]` commit written here would never be squashed and would sit in the log
forever** wearing a prefix that promises otherwise.

**Fork 1 — where the commit is composed.** RECOMMENDED: **(a) extend
`implement_helper wip-commit` with a final-commit mode**, over **(b) a new `fix_helper` commit
verb**.

The recommendation is grounded in what the code actually does (facts 9–11), and every item is
something cold mode must inherit rather than re-derive:

- **Wrapper-mode repo targeting** — commit into `workspace.source_root` in wrapper mode,
  `workspace.install_root` standalone (fact 10).
- **Ticket derivation** — `_extract_ticket_id` off the SOURCE branch, with the full branch name
  as fallback (fact 10).
- **Attribution suppression** — the wrapper-mode source repo must carry no AI trace regardless
  of `COMMIT_ATTRIBUTION` (fact 10).
- **Precise staging** — per-path `git -C <repo> add --`, never `git add -A` (fact 10).

**Plan 26's own build note already decided this exact question once**, on 2026-06-19, when
`wip-commit` turned out to be task-coupled: it chose *"extending the one binary, NOT adding a
fix-side commit composer … precisely to preserve D6's single-source-of-truth principle: a
second commit composer would duplicate the wrapper/`[TICKET-ID]`/attribution logic and risk
drifting from `wip-commit`."* **Fork 1 is the same question with the same answer available; a
ratifier choosing (b) is reversing a decision this repo already made, and should say so.**

**Files and verbs that change under (a)** — this is the whole Python surface of Fork 1:

- `src/devforge/lib/_implement/_cmds_commit.py` — `add_args_wip_commit` gains two optional
  arguments; `_compose_message` gains a third message shape; `cmd_wip_commit` gains the mode
  branch. **`/devforge:implement` stays byte-identical** — it passes neither new flag, exactly
  as it stayed byte-identical across the 2026-06-19 task-less extension.
- `tests/lib/_implement/` — tests written and RUN in the same turn as the code (repo
  discipline: every function gets its own test that runs), covering standalone final, wrapper
  final, the wip-marker note below, and **an unchanged-behavior test proving the two existing
  modes still compose their existing messages**.

**Shape recommendation, for Phase 1 to accept or diverge from with a stated reason:** a boolean
`--final` plus a `--scope <scope>` string, with `--title` continuing to carry the description.
`--scope` is required when `--final` is passed and rejected otherwise, in the same
all-or-none style `cmd_wip_commit` already uses for the task triple (fact 12).

**Fork 2 — the wrapper-mode message shape.** RECOMMENDED: **(i) `--final` keeps the wrapper
shape `[TICKET-ID] - <title>` and applies `fix(scope):` in standalone only**, over **(ii)
`fix(scope):` in both modes**.

The reasoning for (i): in wrapper mode the commit lands in a **client-owned product repo**
whose log convention is external to this framework and is precisely what fact 10's ticket
derivation exists to honour. Imposing Conventional Commits there is a regression, not an
upgrade. **The honest cost of (i), stated rather than smoothed:** `_extract_ticket_id` falls
back to the full branch name when no `[A-Z]+-[0-9]+` token matches (fact 10), and a cold fix is
by definition not on a ticket branch — so a cold wrapper fix on `develop` produces
`[develop] - <title>`. That is ugly and it is real. **A ratifier who finds it unacceptable
should pick (ii) deliberately, not discover the string in Phase 5.**

*Counter-argument to D3 as a whole, recorded:* after this change the verb named `wip-commit`
can produce a commit that is not a WIP commit — the name becomes a partial lie. **Accepted.**
Renaming was considered and rejected: the verb name appears in `/devforge:implement`'s and
`/devforge:fix`'s `allowed-tools` and in both bodies, and a rename buys accuracy at the cost of
touching every citation. **Recorded as a known naming debt, not fixed here** — the alternative
was a second composer, which fork 1 rejects for stronger reasons than a name.

**Build-shaping note, discovered while grounding this decision — Phase 1 must handle it:**
`wip-commit` **unconditionally clears `.devforge/wip.md`** in the install root after a
successful commit (fact 11). In the in-window path that is safe because the window gate
guarantees `/devforge:implement` has drained (fact 22). **D2 removes that guarantee, so
`--final` mode must NOT clear the wip marker** — a cold run wrote none, and clearing one it did
not write destroys another command's crash-recovery state. **This is a fact about the code, not
an open fork**, and Phase 1's verify criteria pin it.

### D4 — The single `bugs/` write: flip the consumed file to Fixed *(RATIFIED 2026-08-26 — fork (b), the `close-bug` helper verb)*

**RECOMMENDED RULE.** Cold mode gains **exactly one** `bugs/` write, on **exactly one** file —
the bug file passed as the argument — performed **only** after the PHASE-6 hard gate approves
and the commit lands. It writes three things and nothing else, all of which the live schema
already has slots for (fact 13):

1. `**Status**: Open` → `**Status**: Fixed`
2. the empty `**Fixed**: ` line → `**Fixed**: <YYYY-MM-DD>` (the orchestrator supplies the
   date; the helper never calls the clock, matching `report_bug_helper write-bug`)
3. the `## Fix Notes` body — the literal `_Filled in after resolution._` → the root cause, what
   changed, and the commit SHA `wip-commit` returned. ⚠ **The SHA half of this clause was
   NARROWED BY MODE on 2026-08-26** — in standalone the bug file rides the very commit that
   mints the SHA, so it carries the commit SUBJECT line instead; in wrapper the SHA clause holds
   unchanged. See `## Open questions` → OQ-3 → `#### Sequencing resolution`.

**⚠ Read the schema, do not assume it.** The completion fields are `**Fixed**:` and
`## Fix Notes` — **there is no `Fixed date` field and no `Fix Notes` bold field**; those names
appear nowhere in `bug_file.py` or `storage-rules.md`. `**Status**`, `**Severity**`,
`**Source**`, `**Feature**`, `**AC**`, `**Reported**` and every other section are left
byte-unchanged.

**This amends `/devforge:fix` Rule 7, and the amendment is narrow.** Rule 7 today reads
(fact 4): *"`/devforge:fix` writes NO report, mutates NO spec/task/`review.md`/`verification.md`,
and writes or closes NO `bugs/` file (D4 — `/devforge:report-bug` is the separate 'defer'
arm)."* **The recommended amendment adds a cold-mode clause and changes nothing else:** the
in-window path still writes no `bugs/` file, `/devforge:report-bug` remains the only CREATOR,
and cold mode may touch only the one file it was handed. Phase 2 must amend all FOUR sites
(fact 4), not just Rule 7 — a frontmatter description still promising *"never writes `bugs/`"*
while the body writes one is the exact rot this repo's sentence-level check exists to catch.

**⚠ D4 also falsifies a clause in a SECOND command's rules, and the blast radius is wider than
one sentence.** `/devforge:report-bug` asserts the lifecycle is manual at **three** sites
(fact 19), one of which sits **inside its own Rule 7**. **That rule is not left byte-unchanged
and must not be deleted either** — it needs a SPLIT (fact 19a): its heading
*"**Never closes or advances a bug**"* and its neighbouring self-claims (*"only ever writes a
fresh `Open` record"*, *"this command never edits an existing bug file"*) remain TRUE of
`/devforge:report-bug` and survive verbatim; only the embedded framework-wide clause
*"The `Open → In Progress → Fixed` lifecycle is maintained manually"* is corrected, to say that
the manual path remains valid **and** that cold-mode `/devforge:fix` now closes a bug it
remediates. Phase 3 owns all three sites.

**Plan 26 chartered this** (fact 25): it deferred a `close-bug` consumer with the trigger *"if
the manual close proves painful in practice"* — and D4 is that trigger firing, with fact 15's
zero-consumer finding as the evidence. **So this is a deferral being collected, not a decision
being reversed.**

**Fork — who performs the write.** RECOMMENDED: **(b) a helper verb** (a `close-bug` verb on
`fix_helper`, implemented over a new function in `src/devforge/lib/_shared/bug_file.py` beside
the existing writer), over **(a) an orchestrator-side Edit of the three fields.**

**⚠ This recommendation DIVERGES from the drafting brief**, which framed D3 as *"the only
Python in this plan."* The divergence is recorded rather than smoothed, and the reasons are:

- **Helper-owns-shape is this repo's stated principle, and `fix/main.md` states it in its own
  `## Helper interaction model`**: *"The helper owns file structure, validation, and atomic
  writes; the orchestrator owns the agent dispatch, user-facing prose, and phase pacing."* A
  bug file is a **schema'd artifact** (fact 13). An orchestrator string-editing three fields
  inside it is exactly the drift surface the principle exists to prevent — the first
  `**Status**` line it matches might not be the bug's own.
- **`_shared/bug_file.py` is already the single source of truth for the shape** (plan 27's D4
  extracted it there precisely so `/devforge:verify` and `/devforge:report-bug` could not
  drift). A close function belongs beside the write function.
- **`_fix/_cli.py` has a documented three-step extension point** (fact 20), so the verb costs a
  handler, a registry triple and an argument block.
- **The "only Python phase" framing survives**: both surfaces land in Phase 1. What changes is
  that Phase 1 has two deliverables, not one.

*Counter-argument, recorded:* (b) grows the Python surface of a plan whose whole selling point
is that the light lane is cheap, and an orchestrator Edit is genuinely three lines. **Accepted
as the cost.** The reply is that the three lines are three lines *of a file format*, and this
repo has already paid once (plan 27 D4) to stop two commands hand-rolling that format.

### D5 — The cold-mode bounce: to `/devforge:research`, and NO seed *(RATIFIED 2026-08-26 — as recommended)*

**RECOMMENDED RULE.** Cold-mode triage applies the **same** defect-repair-vs-change
classification `references/triage.md` already carries — no second rubric, no cold-specific
table. When a bug triages as a feature/architecture change, cold mode STOPS, names WHICH item
and WHY per that reference, and bounces to the **full chain starting `/devforge:research`**.
**It writes NO `ReEntrySeed`, and it leaves the bug file `Open`.**

**Why `/devforge:research`, not `/devforge:specify`** (and this is mechanical, not a
preference): `/devforge:specify` *"blocks until a pending research or discover handoff exists
in a feature directory"* (fact 32). A cold bug has no feature directory and no handoff, so a
bounce naming `/devforge:specify` would name a command that refuses to run. **The in-window D7
bounce correctly names `/devforge:specify` because its feature dir already exists** — the two
bounces differ for a reason, and Phase 2 must not "harmonize" them.

**Why NO seed, and it is forced rather than preferred.** Plan 83's seed model is
feature-scoped by construction (fact 21): `write_seed` writes
`os.path.join(feature_dir, "fix-seed.json")` and `--feature-dir` is required. **Cold mode has
no feature dir to hold a seed.** Writing one would require inventing a feature-less seed
location, a new consumer glob, and a `/devforge:research` consumer block that does not exist —
three new mechanisms to carry a bounce whose entire content ("this bug is a scope change, here
is why") the model states in prose in the same turn.

**What replaces the seed: nothing, and that is the recorded bound.** The diagnosis is spoken
and then lost, exactly the loss plan 83 fixed for the in-window bounce. **A future session
finding cold bounces re-derived repeatedly has a real plan to write** — a feature-less seed
carrier plus a `/devforge:research` consumer — and it should be argued from observed repetition,
not from symmetry with plan 83.

*Counter-argument, recorded:* leaving the bug `Open` after a bounce means the file's Status
does not distinguish "nobody looked at it" from "triaged and escalated." **Accepted, and no
field is added** — the schema (fact 13) has `In Progress`, but claiming a bounce puts a bug
`In Progress` would be false the moment the user does nothing. **A status the framework cannot
keep true is worse than one it does not set.**

### D6 — A three-arm routing rubric in `src/CLAUDE.md` *(RATIFIED 2026-08-26 — reading (i); counter-argument retained UNRESOLVED)*

> **AMENDED 2026-09-04 by `95-TICKET-CAPTURE-LANE-PLAN.md` (its D6), narrowly.** Arm 3 gained ONE clause: when the user would rather file the change than start the chain now, the model may offer `/devforge:report-ticket` as the **file-it-for-later variant of that same arm**, the item being picked up later with `/devforge:research tickets/NNN-<slug>.md`. **Nothing else in this rubric moved** — the discriminator sentence (repair vs change, never file count) is byte-unchanged, arms 1 and 2 are byte-unchanged, the rubric still has THREE arms on ONE axis, and it is still ADVISORY with nothing checking it. ⚠ **This plan's own reading (i) on `/devforge:report-bug` Rule 8 is NOT reopened**: that plan added no forward pointer there and took no position on the fork. **No build record of this plan is edited and no phase is re-opened.**

**RECOMMENDED RULE.** Extend the existing `### Conversational fix-or-file offer` (fact 28) from
two arms to three:

1. **In-window, code-confirmed defect** → offer `/devforge:fix` now. **UNCHANGED** — same three
   AND-ed conditions, same `in-fix-window` check.
2. **Cold, code-confirmed defect that is a REPAIR** → offer `/devforge:report-bug` to capture
   it, then `/devforge:fix bugs/NNN-<slug>.md` to remediate it under the gates.
3. **Confirmed problem that needs a behavior or architecture change** → recommend the full
   chain from `/devforge:research`.

**The discriminator between arms 2 and 3 is defect-repair-vs-change — the `references/triage.md`
classification — and NEVER file count.** Say it in the emitted text. A file-count criterion
would resurrect v1's cap by the back door (D7) and would misroute both ways: a one-file change
that alters a public contract is arm 3; a five-file null-check repair is arm 2.

**Advisory, never a gate** — the precedent is `/devforge:plan`'s stakes-hint, *"ADVISORY and
NON-BLOCKING: it never blocks the approve flow, never gates `/devforge:breakdown`"* (fact 23).
Nothing checks that the model offered the right arm.

**⚠ Honest bound, and it must appear in this plan's summary wherever this plan is summarized:**
the offer is **model judgment**. The only MECHANICAL net is D5's in-command bounce, which fires
after the user has already typed the command. **A rubric is not an enforcement layer and this
plan does not claim one.**

**⚠ Collision — `/devforge:report-bug` Rule 8 forbids arm 2's second half** (fact 18):
*"**Never call `/devforge:fix` from here** — … It does not propose, invoke, or chain into
`/devforge:fix`; a bug captured here is addressed later through the normal pipeline."*

Two readings, and **Phase 0 must pick one explicitly rather than letting Phase 3 pick by
drift**:

- **(i) No conflict — arm 2 lives in `src/CLAUDE.md`, not in `report-bug`'s body.** Rule 8
  binds what the COMMAND does at its PHASE 4; the rubric is a conversational behavior the
  orchestrator applies. Under (i), Phase 3 adds the arm to `src/CLAUDE.md` and **leaves Rule 8
  byte-unchanged**. **RECOMMENDED**, because it is the reading that requires no rule to be
  weakened. ⚠ **(i) does NOT make `report-bug/main.md` a one-sentence edit** — D4 independently
  falsifies the framework-wide manual-lifecycle clause at three sites there, one of them inside
  Rule 7 (facts 19, 19a). **Rule 8 byte-unchanged is (i)'s claim; "the file is barely touched"
  is not**, and conflating the two undercounts Phase 3.
- **(ii) Rule 8 is amended** to permit naming `/devforge:fix` as the cold consumer in
  `report-bug`'s PHASE-4 forward pointer (fact 13a — which today names only
  `/devforge:research` and `/devforge:specify`). This is what the drafting brief's Phase-3
  "`report-bug` cross-reference" implies. **NOT recommended:** Rule 8's stated purpose is that
  capture and remediation stay deliberately separate arms, and a command that files a bug and
  immediately proposes fixing it has collapsed the defer arm into the fix arm — which is the
  distinction plan 26 D2 and plan 27 D3 both rest on.

**Under (i), Phase 3 adds NO forward pointer to `/devforge:report-bug`** — which is a real
reduction against the drafting brief's Phase-3 framing and is called out here so it is not
discovered mid-build. **It is not a reduction to zero:** D4's three-site correction (facts 19,
19a) lands in that file under BOTH readings, so `report-bug/main.md` is edited either way and
only the *pointer* question turns on (i) vs (ii).

*Counter-argument, recorded:* under (i), a user who files a bug via `/devforge:report-bug` is
told to go to `/devforge:research` (fact 13a) by the command itself, while the conversational
rubric says `/devforge:fix bugs/…` — **two different answers in the same session**, and the
command's answer is the one printed in the transcript. **This is the strongest objection to
(i) and it is not fully answered.** The partial answer is that the two are not contradictory —
`/devforge:research` remains correct for arm 3 — but a Phase-5 observer who sees the pointer
win over the rubric has found a real defect in (i), and the repair is (ii).

### D7 — No numeric scope cap *(RATIFIED 2026-08-26 — as recommended)*

**RECOMMENDED RULE.** v1's *"recommends `/specify` if bug affects more than 5 files"*
(fact 24) is **deliberately NOT reproduced.** The cold lane has no file-count threshold, no LOC
threshold, and no size metric of any kind. The discriminator is D5's defect-vs-change triage
and nothing else.

**Why**, and the reasoning is already in the repo: file count is a **proxy** for the thing that
matters, and it is wrong in both directions — a one-file edit that changes a public API
contract is a scope change (`references/triage.md`'s second row lists exactly that), and a
mechanical null-check repair across eight call sites is a defect repair. Plan 27's D3 already
settled the same question for the file-a-bug proposal: *"the system PROPOSES filing **by routing
state, not a size metric** … No LOC/file-count threshold."* **D7 is that stance applied to the
cold lane, not a new one.**

**Recorded as a deliberate divergence from v1.** A future session reading `CHANGELOG.md:730`
and finding no cap in the cold lane must find HERE that the cap was considered and declined, so
it does not "restore" it as a lost feature.

*Counter-argument, recorded:* a numeric cap is objective and externally checkable, while
"defect vs change" is a judgment the model makes about its own work — the weaker guarantee of
the two. **Accepted.** The reply is that the objective cap is objectively measuring the wrong
quantity, and `references/triage.md`'s "Wide scope" note already tells the reader to treat
breadth as a **signal to re-check the classification**, which is the honest use of the same
information.

---

## Open questions (OQ-N) — ALL ANSWERED 2026-08-26

**Every OQ below was answered as recommended.** Each carries an `**ANSWERED 2026-08-26:**` line
stating the recorded answer; the reasoning beneath it is the reasoning that was ratified, and
the warnings and residuals it records are ratified alongside it rather than discharged by it.

### OQ-1 — A bug file that cites no file

**ANSWERED 2026-08-26:** as recommended — D1's code-confirmation step SUPPLIES `files_cited`,
and a bug whose defect cannot be located in live code STOPS the run rather than degrading to a
prose-driven edit.

`--file` is optional on `/devforge:report-bug` (fact 13a), so a bug file may render
`| (unknown) | (see evidence) |` and carry no usable `files_cited`. `resolve-scope` would then
return `empty: true` and the existing PHASE-1 empty-scope guard would stop the run.

**RECOMMENDATION.** D1's code-confirmation step **supplies** `files_cited` — the file(s) the
model read to confirm the defect — exactly as the case-3 conversational item does today
(fact 6). **If confirmation cannot locate the defect in live code, STOP: no remediation without
a located defect.** Tell the user the bug could not be confirmed against the current code, name
what was searched, and suggest `/devforge:research` to investigate. **This is a stop, not a
degraded mode** — remediating an unlocated defect means editing code on the strength of a prose
description, which is the free-text intake D1 refuses.

### OQ-2 — Does cold mode run the full back half?

**ANSWERED 2026-08-26: YES** — the full back half runs unchanged. **The plan's
proportionality argument therefore stands as written and was not weakened at ratification.**

**RECOMMENDATION: YES, unchanged.** PHASES 2–7 run exactly as they do today — agent dispatch,
scope-aware `verify-touched` with self-repair, the four-reviewer panel, the forcing-functions
gate, and the two-stage hard gate — with only PHASE 6's commit call differing per D3. **This is
the discipline floor and it is the entire reason the cold lane is worth building**: the thing
hand-fixing loses is the gates (plan 21 §5 named exactly two losses — the forced verify gate
and the clean attributed commit — and this lane restores both). **The back half is CALLED, not
copied** (plan 26 D6), so cold mode inherits it at zero maintenance cost.

**⚠ If Phase 0 declines this, the plan's proportionality argument collapses** and must be
re-argued from scratch — a cold lane that skips the panel is a hand-fix with extra steps.

### OQ-3 — Commit vehicle for the bug-file Status flip

**ANSWERED 2026-08-26:** as recommended, mode-dependent — standalone rides the same
`fix(scope):` commit; wrapper rides `artifact_helper commit-artifacts` into the install repo,
**and its `[WIP] ` label prefix is ACCEPTED** (bookkeeping, install-repo, harmless). **No second
commit composer is built for it** — that is the duplication D3 fork 1 refuses.

**RECOMMENDATION: mode-dependent, because the repos differ.**

- **Standalone** — the same `fix(scope):` commit. Code and bug file live in one repo, and the
  fix plus its bookkeeping are one logical change. `--files` simply includes the bug path.
- **Wrapper** — **it needs its own install-repo commit.** `wip-commit` in wrapper mode commits
  into `workspace.source_root` (fact 10), while `bugs/` lives at the **install root** (the
  wrapper), which is a different repo. Staging the bug path into the source-repo commit would
  fail, and even if it did not, it would write a forge artifact into a client product repo —
  the exact pollution PHASE 3's `isolation_failure` status exists to catch. So the flip rides
  `artifact_helper commit-artifacts`, which *"stages ONLY the named path and makes a … commit
  in the INSTALL repo (never the wrapper-mode source/product repo)"* and is FAIL-SOFT
  (fact 30).

**⚠ Note the label consequence, so Phase 2 does not produce a misleading log:**
`commit-artifacts` prefixes `[WIP] `. A cold-lane bug-file flip committed through it therefore
lands as `[WIP] …` **in a repo where nothing will squash it** — the same problem D3 solves for
the code commit. **Phase 0 should decide whether that is acceptable (it is bookkeeping, in the
install repo, and harmless) or whether the wrapper arm needs its own non-WIP path.**
RECOMMENDED: **accept it**, and say why in the plan record — a second commit-composer for a
bookkeeping commit is the duplication D3 fork 1 refuses.

#### Sequencing resolution — D4 ↔ OQ-3 conflict *(discovered by python-reviewer during Phase 1; resolved by the orchestrator 2026-08-26)*

**The conflict.** Ratified D4 says the flip happens *"only after the hard gate approves and the
commit lands"* and that `## Fix Notes` carries *"the commit SHA `wip-commit` returned"*.
Ratified OQ-3 says standalone uses *"the same `fix(scope):` commit — `--files` simply includes
the bug path."* **In standalone those cannot both hold: a SHA cannot be written into a file that
rides the commit which mints that SHA.** Neither item is withdrawn; the conflict is real and was
latent in both ratifications.

**The resolution. OQ-3 controls the VEHICLE; D4's SHA clause is narrowed BY MODE** — because the
vehicle is forced by repo topology (a wrapper's bug file and its code are in different repos)
while the SHA is only a convenience reference:

- **Standalone** — after the Stage-B gate approves, call `close-bug` **FIRST**, then
  `wip-commit --final` with the bug file included in `--files`. **ONE commit**, satisfying OQ-3
  exactly. The fix notes carry root cause + what changed + **the commit SUBJECT line**, not a
  SHA. D4's *"after the hard gate approves"* holds; its *"and the commit lands"* is what
  narrows — the flip precedes the commit it rides in.
- **Wrapper** — the code commit lands in the SOURCE repo first, so `wip-commit --final` returns
  a real `head_sha` before the flip is written. **D4's SHA clause holds unchanged here**: the
  fix notes DO carry the returned source-commit SHA. The flip then rides
  `artifact_helper commit-artifacts` in the install repo, with OQ-3's accepted `[WIP] ` label.

⚠ **State the per-mode difference explicitly wherever it is emitted; do NOT average the two into
one order.** A single averaged instruction is wrong in one mode or the other — in standalone it
would demand a SHA that does not exist yet, and in wrapper it would stage a forge artifact into
the product repo. **Phase 2 shipped it as two separate labelled blocks** in
`src/commands/fix/main.md` PHASE 6's cold arm, and `## Outputs of this command` states the
same split.

⚠ **The standalone order has a non-atomic window Phase 2 must keep visible**: `close-bug` writes
the flip to disk BEFORE the commit exists, so a `wip-commit --final` failure leaves a flipped-but-
uncommitted bug file. That is not a clean rollback point, and re-running `close-bug` exits 2 (the
file is no longer `Open`). The emitted recovery instruction is to resolve the failure and re-run
ONLY the commit call.

### OQ-4 — Memory read in cold mode

**ANSWERED 2026-08-26:** as recommended — the PHASE-2 memory read is UNCHANGED; no new key, no
new read, no change to `_shared/memory.py`.

**RECOMMENDATION: unchanged.** PHASE 2 already reads `memory_excerpt` from the re-captured
preflight JSON and instructs the orchestrator to SELECT the entries bearing on the cited files.
Cold mode inherits it verbatim — nothing about the excerpt is feature-scoped, and *"a fix that
trips a known pitfall is a second finding, not a fix"* applies identically to a cold defect.
**No new key, no new read, no change to `_shared/memory.py`.**

### OQ-5 — Verify-PHASE-9 bugs on sealed features

**ANSWERED 2026-08-26:** as recommended — cold-fixing a sealed feature's CODE is ACCEPTABLE
(the seal is about artifacts, not source), **and the honest residual is ratified alongside it,
not discharged by it**: the sealed feature's `verification.md` keeps asserting ACs proved
against a diff that has since changed, and nothing in this plan updates it.

A `Source: verify` bug carries a real `**Feature**` path (fact 13), and its feature may since
have been sealed by `/devforge:summarize` / `/devforge:finalize`. Cold-fixing it re-touches
that feature's **code** without reopening its `specs/` artifacts.

**RECOMMENDATION: acceptable, and here is the reasoning to record rather than re-derive.** The
seal is about **artifacts**, not code. `/devforge:finalize` squashes WIP commits into a clean
feature commit and the feature's `specs/` dir becomes a permanent record; **it does not freeze
the source files**. A cold fix adds a **fresh, separate `fix(scope):` commit** on top — which
is precisely how a bug in already-shipped code is normally fixed. **What cold mode must NOT do
is touch the sealed feature's `specs/` artifacts**, and D2 guarantees that mechanically: with
no feature resolved, there is no `<feature>` for any path to be built from.

**⚠ The honest residual:** the sealed feature's `verification.md` continues to assert its ACs
passed against a diff that has since changed. Nothing in this plan updates it, and nothing
should — re-proving ACs is `/devforge:verify`'s job and it is feature-scoped.

### OQ-6 — Plan 63's 13/7 model-invocable counts

**ANSWERED 2026-08-26:** as recommended — counts UNCHANGED, `/devforge:fix` stays
`disable-model-invocation: true` and human-typed, no description trim, **no count delta**. The
standing rule below binds: if a future phase ever needs to state the counts, it reads them LIVE.

**RECOMMENDATION: unchanged.** `/devforge:fix` keeps `disable-model-invocation: true` (fact 2)
and stays human-typed. **This plan contributes NO count delta** and owes no description trim.
Cold mode does not make `/devforge:fix` safer to auto-invoke — it makes it reachable in more
situations, which is an argument for keeping the human in the loop, not against it.

**⚠ Standing coordination rule** (plans 82/85 precedent): if any future phase does need to
state the counts, it **reads them LIVE at ship time** and never applies a pre-computed delta.

**(AMENDED 2026-09-03 — plan 93.)** Reversed: `/devforge:fix` DROPS the flag; the counts are
16/4 and the human-typed set is the four setup commands. The argument above — cold mode makes
`/devforge:fix` reachable in more situations, so keep the human in the loop — is answered by
plan 93, not dismissed: the human stays in the loop by agreeing to the offer and at the
command's own two-stage hard gate; the flag guaranteed a keystroke, not a decision.
Consequence for D6: its retained counter-argument (the command's PHASE-4 pointer vs the
rubric) is now LIVE, and `/devforge:report-bug` Rule 8 — byte-unchanged — is the only bar
against an in-command report-bug → fix chain. The standing coordination rule (read the counts
LIVE) is unchanged and is how plan 93 read them.

### OQ-7 — Scratch-dir reuse

**ANSWERED 2026-08-26:** as recommended — the two scratch literals are REUSED unchanged, **and
the serial-runs assumption they rest on is recorded as part of the answer**: a future change
that makes any `/devforge:fix` path concurrent invalidates this answer and re-opens OQ-7.

Cold mode reuses the fixed literals `${TMPDIR:-/tmp}/forge-fix` and
`${TMPDIR:-/tmp}/forge-implement-review` unchanged.

**RECOMMENDATION: acceptable, recorded.** `/devforge:fix` runs are serial within a session — a
run holds the turn from PHASE 0 to PHASE 7 — so a cold run and an in-window run cannot overlap.
Both paths open with `rm -rf "$WORKDIR" && mkdir -p "$WORKDIR"`, which clears stale scratch from
a crashed prior run either way. **No new literal, no per-mode suffix.** ⚠ A future change that
makes any `/devforge:fix` path concurrent invalidates this answer.

---

## Phase 0 ratification record

**Ratification authority: the maintainer's in-session statement of 2026-08-26**, following the
2026-08-25 a-vs-b direction decision recorded in `## Origin`. That statement is the whole
closure authority for Phase 0 — **not a fresh per-item re-derivation**, and not this document's
own recommendations agreeing with themselves.

**Every item was ratified AS RECOMMENDED — D1–D7 and OQ-1–OQ-7, nothing amended, nothing left
open.** The four items Phase 0 flagged as needing an explicit pick were each picked explicitly:

- **D3 fork 1 = (a)** — extend `implement_helper wip-commit` with a final-commit mode, over a
  new `fix_helper` verb. This re-affirms plan 26's own 2026-06-19 "extend the one binary, never
  a second composer" note rather than reversing it. **D3 fork 2 = (i)** — wrapper mode keeps
  `[TICKET-ID] - <title>`; **the `[develop] - <title>` fallback string was seen at ratification
  and ACCEPTED**, so a Phase-5 observer reading it has found the ratified design, not a defect.
  **The `--final` + `--scope` shape is a RECOMMENDATION, not a ratified interface** — Phase 1
  may diverge from it by stating a reason. **The `wip-commit` naming debt stays recorded** and
  was not repaired.
- **D4 fork = (b)** — the `close-bug` helper verb over a new function in
  `_shared/bug_file.py`, on the helper-owns-shape argument and plan 26's chartered deferral.
  **The ratifier acknowledged that this arm diverges from the drafting brief's "only Python is
  D3" framing**; the divergence is accepted, not smoothed. **Consequence: Phase 1 carries TWO
  deliverables**, and remains the only Python phase.
- **D6 = reading (i)** — the three-arm rubric lives in `src/CLAUDE.md`; `/devforge:report-bug`
  Rule 8 stays **byte-unchanged** and **no forward pointer to `/devforge:fix` is added to that
  command**. ⚠ **The pick was made WITH its counter-argument explicitly retained as UNRESOLVED**:
  under (i) the command's own PHASE-4 pointer (naming `/devforge:research` / `/devforge:specify`)
  and the conversational rubric can give a user two different answers in one session, and the
  command's answer is the one printed in the transcript. **A Phase-5 observation of that
  contradiction is the named trigger to re-open D6 as reading (ii)** — see Phase 5's anchor 3.
- **OQ-2 = YES** — the full back half runs unchanged, so the proportionality argument stands as
  written.

**No counter-argument was deleted, softened or answered away by this ratification.** Each
decision's `*Counter-argument, recorded:*` block is the pre-ratification text, verbatim. The
same holds for every `⚠` bound: D2's accepted unguarded concurrent-`/devforge:implement` state,
D3's naming debt and fallback string, D5's lost-diagnosis bound, D6's unresolved objection,
OQ-3's accepted `[WIP] ` label, OQ-5's stale `verification.md`, and OQ-7's serial-runs
assumption are all **ratified as costs, not discharged as concerns.**

**Phases 1–4 are CLEARED for build. Phase 5 has NOT run.**

### Review outcomes that resolved WITHOUT a change *(recorded 2026-08-26)*

Two review findings were raised during the build, judged correct, and closed with no edit. **They
are recorded because an unrecorded no-change outcome is indistinguishable from an unnoticed
finding**, and a later reviewer would otherwise raise each again.

1. **claude-code-guide, Phase 3 — a `CLAUDE.md` instruction to run a Bash check is MODEL-FOLLOWED,
   not guaranteed.** The offer's arm 1 tells the model to verify the window with
   `fix_helper in-fix-window`, and nothing in Claude Code enforces that it actually does.
   **Accepted, no change.** The offer is model judgment by design (D6's own honest bound says so),
   the fail-closed clause is already present — any non-zero result, helper-unavailable included,
   is treated as not-in-window — and the mechanical net is D5's in-command bounce, which runs
   inside the command where a helper call IS deterministic. **Making the rubric enforceable would
   mean a gate, which D6 explicitly refuses.**
2. **Phase-3 nit — arm 3's "in or out of window" wording.** Flagged as possibly loose.
   **Accepted as-is, no change.** Arm 3 is the change-not-a-repair route, and its correctness is
   genuinely window-independent: a behavior or architecture change needs the full chain whether or
   not a feature happens to be open. Narrowing the clause would have implied a window condition
   that does not exist.

---

## Phases

### Phase 0 — Ratification *(doc-only — CLOSED 2026-08-26)*

**Objective:** ratify or amend D1–D7 and answer OQ-1–OQ-7, recording each answer in this file
with its reasoning. **Nothing else may start.** **Discharged 2026-08-26** — see
`## Phase 0 ratification record` above.

Four items needed an explicit pick rather than a nod, because each has a named fork whose arms
lead to different builds. **All four were picked — see the record above:**

- **D3 fork 1** (extend `wip-commit` vs a new `fix_helper` verb) and **fork 2** (wrapper
  message shape) — fork 2's cost is a literal string a Phase-5 observer will read.
- **D4's fork** (helper verb vs orchestrator Edit) — and the ratifier should note that the
  RECOMMENDED arm **diverges from the drafting brief's "only Python is D3" framing**, which is
  recorded in D4 rather than smoothed.
- **D6's collision** with `/devforge:report-bug` Rule 8 (fact 18) — reading (i) or (ii). What
  turns on the pick is **only whether a forward pointer to `/devforge:fix` is added there**:
  D4's three-site manual-lifecycle correction (facts 19, 19a) lands in that file under BOTH
  readings, so neither pick makes it a no-op file.
- **OQ-2** — declining it invalidates the plan's proportionality argument rather than trimming
  it.

**Verify:**

**All criteria below were checked and PASS on 2026-08-26.**

- `grep -n "^### D[1-7] " 88-COLD-FIX-BUGS-LANE-PLAN.md` returns seven lines and **every one
  carries a `*(RATIFIED 2026-08-26 …)*` marker**. ✔
- `grep -n "^### OQ-[1-7] " 88-COLD-FIX-BUGS-LANE-PLAN.md` returns seven lines, and **each
  section opens with an `**ANSWERED 2026-08-26:**` line**. ✔
- **No open marker survives on any heading or in either section title** — check with
  `grep -n "OPEN" 88-COLD-FIX-BUGS-LANE-PLAN.md`, which must return **only** the three lines
  that QUOTE the token while describing this criterion, plus prose uses of the word in the
  decision bodies. ⚠ **This criterion cannot be written as "the string `(OPEN` appears zero
  times", because stating the criterion creates an occurrence of it** — score it on the
  headings and the two section titles, not on a raw count. ✔
- **Every decision still carries its counter-argument, verbatim and unedited.** A ratified
  decision with its counter-argument deleted cannot be re-opened honestly. ✔ — and the same
  holds for the `⚠` bounds, which are ratified as costs rather than discharged.
- The status line at the top names the ratification date and which phases are cleared. ✔
- **D6's collision is resolved by a stated reading, not by silence.** A Phase 0 that ratifies
  D6 without naming (i) or (ii) has left Phase 3 to pick by drift. ✔ — **(i)**, with the
  counter-argument retained UNRESOLVED and Phase 5's anchor 3 named as the re-open trigger.

---

### Phase 1 — The commit mode *(the ONLY Python phase)* — ✅ DONE 2026-08-26 (`92592c5`)

**Route: python-engineer → python-reviewer, test-first.** No `.claude/`-shipping file changes
here, so no claude-code-guide pass is owed by this phase.

**Deliverable 1 — D3's final-commit mode.** Under fork-1 arm (a), in
`src/devforge/lib/_implement/_cmds_commit.py`: two optional arguments on
`add_args_wip_commit`, a third shape in `_compose_message`, and the mode branch in
`cmd_wip_commit`. **`/devforge:implement` stays byte-identical** — it passes neither new flag.

**⚠ Three build constraints, each a fact rather than a fork:**

1. **`--final` must NOT clear `.devforge/wip.md`** (fact 11 + D2's counter-argument). A cold
   run wrote no marker; clearing one it did not write destroys `/devforge:implement`'s
   crash-recovery state.
2. **The all-or-none argument discipline is already in the file** (fact 12) — mirror it, do not
   invent a second style.
3. **Staging stays per-path** (fact 10). Nothing here may reach `git add -A`.

**Deliverable 2 — D4's `close-bug`** (only if D4's recommended arm ratifies): a function in
`src/devforge/lib/_shared/bug_file.py` beside the existing writer, and a `close-bug` verb
registered through `_fix/_cli.py`'s documented three-step extension point (fact 20). **The
function owns the shape**: it locates the bug file's OWN `**Status**:` and `**Fixed**:` lines
and its `## Fix Notes` body, rejects a file whose Status is not `Open` or `In Progress` with a
non-zero exit rather than writing, and writes atomically (`tempfile.mkstemp` + `os.replace`),
matching the package's convention.

**Tests — written and RUN in the same turn as the code**, per repo discipline (every function
gets its own test that runs), and **round-tripped through the real producers, never
hand-authored fixtures**: a `close-bug` test builds its input by calling
`_shared.bug_file.file_bugs(...)` — the same writer `/devforge:report-bug` and
`/devforge:verify` use — then closes it and asserts the three changed fields and that every
other line is byte-identical.

**Verify:**

- python-reviewer clean; the `tests/lib/_implement/` and `tests/lib/_shared/` suites green.
- **Every pre-existing test in both files passes unchanged.** This phase adds tests; it edits
  none. A failure in an existing `wip-commit` test means the two shipped modes moved.
- **A test proves `--final` leaves an existing `.devforge/wip.md` in place**, and a sibling
  test proves the task and fix modes still clear it (constraint 1).
- **`grep -n "add -A" src/devforge/lib/_implement/_cmds_commit.py` returns zero lines**
  (constraint 3). Capture the pre-change output first.
- **The `close-bug` round-trip asserts byte-identity outside the three changed fields** — a
  close that reflows the file has rewritten an artifact it was asked to amend.
- **`close-bug` on a file already `Fixed` exits non-zero and writes nothing** — verified by
  reading the file back.
- `git status` shows zero files modified under `src/commands/` or `src/agents/` — this phase is
  Python-only.

---

### Phase 2 — `src/commands/fix/` — the cold-mode arm — ✅ DONE 2026-08-26 (`bf0c4b9`)

**Route: instruction-author → instruction-reviewer + claude-code-guide.** `main.md` ships into
`.claude/commands/devforge/` and this phase touches its frontmatter, so the integration pass is
owed. **The `allowed-tools` semantics verified 2026-08-25 (see `### Claude Code authoring
surface`) are the starting point, not a substitute for that pass.**

Scope, three files:

- **`src/commands/fix/main.md` — frontmatter.** Widen `argument-hint` to admit the bugs-file
  form (a display string only — it validates nothing). Amend the `description`'s closing
  sentence (fact 1) so its `bugs/` claim matches D4 while its **free-text ban stays verbatim**
  (D1). Add `allowed-tools` entries for any new verb — **`fix_helper close-bug` under D4's
  recommended arm**, and note that under the alternative arm an `Edit` entry is an ergonomics
  choice, not a correctness requirement.
- **`src/commands/fix/main.md` — body.** A cold-mode arm at PHASE 0 that branches on the D1
  trigger and names **all three** bypassed sub-phases — 0.2, 0.3 **and 0.4** (D2) — with the
  amendment reasoning inline; the D1 code-confirmation step and OQ-1's stop; the PHASE-6
  commit-call fork per D3; the D4 flip after the commit lands; the D5 bounce naming
  `/devforge:research` and stating that **no seed is written and the bug stays Open**. Widen the
  empty-list STOP's cold-bug clause (fact 7) to point at the new lane.
- **`src/commands/fix/main.md` — PHASE 1's triage inputs (easy to miss, and it breaks the run if
  missed).** PHASE 1 today opens on *"the `items` from `$WORKDIR/findings.json`"* and its
  no-bounce arm shells out to `python3` to extract that array. **Cold mode produces no
  `findings.json`** (fact 20a), so both sentences need a cold carve-out: the cold working list
  is the SINGLE orchestrator-composed item of D2, written straight to `$WORKDIR/items.json`
  with the Write tool — which is the branch the existing case-3 parenthetical already describes
  (its greppable contiguous line: *"write the combined array yourself with the Write tool
  instead of this line"*). **`resolve-scope`, the empty-scope guard and
  everything downstream are untouched** — they consume `items.json`, not `findings.json`. Also
  update the `### Intermediate scratch files` list, which currently states unconditionally that
  `findings.json` is *"Written in PHASE 0"*.
- **`src/commands/fix/references/triage.md`.** The cold additions: that the SAME table and the
  SAME discriminator apply, that a cold bounce goes to `/devforge:research` (not
  `/devforge:specify`) and why (fact 32), and that a captured bug is not a confirmed bug.

**⚠ Four sites carry the never-writes-`bugs/` claim** (fact 4). All four move together or the
file contradicts itself.

**Verify:**

- Instruction-reviewer clean; claude-code-guide clean, with the fetched URLs recorded.
- **`grep -n "bugs/" src/commands/fix/main.md` returns every one of the four claim sites in its
  amended form**, and no site still promises `never writes bugs/` without the cold-mode
  qualification. Capture the pre-change output first.
- **The free-text ban survives verbatim** — `grep -n "free-text\|free-form"` still returns the
  refusal, and instruction-reviewer confirms the amended source list cannot be read as
  admitting a typed description.
- **The cold arm never calls `in-fix-window`** — `grep -n "in-fix-window" src/commands/fix/main.md`
  returns only the in-window PHASE-0.3 block.
- **The cold arm never calls `read-findings` and never reads `findings.json`** (fact 20a) —
  `grep -n "read-findings\|findings.json" src/commands/fix/main.md` returns only sites that are
  explicitly scoped to the in-window path, **including the `### Intermediate scratch files`
  entry**. A cold arm citing `findings.json` describes a file that run never wrote.
- **The cold bounce names `/devforge:research`, and the in-window D7 bounce still names
  `/devforge:specify`.** Both greps return their own command; neither returns the other's.
- **No `{{` placeholder leaks**: `grep -rl "{{" src/commands/fix/` returns nothing.
- **The cold arm's every helper verb exists** — each `.devforge/lib/…` call in the new prose
  resolves to a registered verb in `_fix/_cli.py` or `_implement/_cli.py`. A spec citing a verb
  that Phase 1 did not build is the failure mode this criterion exists for.

---

### Phase 3 — `src/CLAUDE.md` + the catalog + the `report-bug` reconciliation — ✅ DONE 2026-08-26 (`7ec8f69`)

**Route: instruction-author → instruction-reviewer + claude-code-guide** (`src/CLAUDE.md` ships
as the consumer's root `CLAUDE.md`).

Scope:

- **`src/CLAUDE.md` — the three-arm offer.** Rewrite `### Conversational fix-or-file offer`
  (fact 28) per D6. **Keep it TIGHT** — plan 08's always-on-trim discipline binds this section;
  every line costs tokens in every session. Arm 1 is **semantically preserved, restructured to
  bullets** — its three AND-ed conditions and its `in-fix-window` invocation (including the
  fail-closed clause treating any non-zero result, helper-unavailable included, as not-in-window)
  carry over verbatim, but the section moved from one paragraph to a lead sentence plus three
  bullets plus a closing constraint, so "byte-unchanged" would overclaim. ⚠ **The closing
  fallback clause legitimately NARROWED from three conditions to two**: it used to read *"if any
  is absent (the defect is unconfirmed, you originated it, or no feature is in that window),
  offer only `/devforge:report-bug`"*, and window-absence is now ABSORBED BY ARM 2 rather than
  routed to file-only — that is the change this plan exists to make, not a regression. Arms 2
  and 3 are added; the discriminator sentence
  names defect-repair-vs-change and **explicitly not file count**.
- **`src/CLAUDE.md` — the `#### /devforge:fix` catalog entry: a FULL-PARAGRAPH REWRITE, not a
  two-clause patch.** That one paragraph carries **five** falsified clauses (fact 29), and it
  is *"the only place the model sees what they do"* for a human-typed-only command (fact 29a) —
  so a partially-updated entry contradicts the three-arm rubric added a few lines above it in
  the same file. The rewrite must land all five: (a) drop *"NOT a cold bug-fixer"*; (b) state
  **four** trigger situations, the fourth being an explicit `bugs/NNN-<slug>.md` argument, and
  scope the *"all inside the post-implement/pre-summarize window"* clause to the first three;
  (c) list **three** findings sources — `review.md`, `verification.md`, `bugs/NNN-*.md`; (d)
  replace *"Writes NO `bugs/` file"* with D4's narrow truth (creates none; flips exactly the one
  cold-mode file it was handed, and `/devforge:report-bug` remains the only creator); (e) mark
  the `/devforge:specify`-bounce sentence and the whole `fix-seed.json` clause as **in-window
  only**, and name the cold bounce's different behavior (→ `/devforge:research`, no seed, bug
  stays `Open`). **Widen the entry's heading argument form** (`:111`) in step with Phase 2's
  `argument-hint`. The entry stays a purpose description (plan 08) — mechanics live in
  `main.md`, so this rewrite must not grow into a second spec.
- **`src/CLAUDE.md` — the workflow-prose window claim** (fact 29b). A second, non-catalog site
  says `/devforge:fix` is *"run inside the post-`/devforge:implement`/pre-`/devforge:summarize`
  window"*. **The neighbouring *"never appears in the arrow chain above"* stays true and must
  survive** — only the window half is qualified.
- **`src/commands/report-bug/main.md` — THREE sites, not one** (facts 19, 19a). Open this scope
  with `grep -n "Open → In Progress → Fixed" src/commands/report-bug/main.md`, **not** a
  `bugs/` grep and **not** a `maintained manually` grep — the three sites share the arrow string
  but not their wording, so a `maintained manually` grep silently misses `:90` (fact 19b). The
  three: the intro (`:15`), PHASE 4's close (`:90`), and the clause **inside Rule 7** (`:100`).
  **Rule 7 is SPLIT, not deleted:** its heading and its `/devforge:report-bug`-self claims
  survive verbatim; only the embedded framework-wide clause is corrected. The manual path stays
  valid at all three — what changes is that it is no longer the *only* path. **Rule 8 stays
  byte-unchanged under D6 reading (i);** under reading (ii) it is amended too, and Phase 0 said
  which.

**Verify:**

- Instruction-reviewer clean; claude-code-guide clean.
- **The offer section is three arms and still one tight block** — record its line count before
  and after; a rubric that doubled the section has failed plan 08's discipline.
- **`grep -n "file count\|number of files\|more than" src/CLAUDE.md`** returns no
  cold-lane size criterion (D7).
- **`grep -n "cold bug-fixer" src/CLAUDE.md` returns nothing**, and a read of the rewritten
  catalog paragraph confirms **all five** of fact 29's clauses moved — a rewrite that fixed (a)
  and (d) while leaving the window, the two-source list or the bounce sentence standing has
  produced an entry that contradicts the rubric three headings above it.
- **`grep -n "post-\`/devforge:implement\`/pre-\`/devforge:summarize\` window" src/CLAUDE.md`**
  returns only occurrences that are explicitly scoped to the in-window path — fact 29b's
  workflow-prose site included. Capture the pre-change output first.
- **`grep -n "Open → In Progress → Fixed" src/commands/report-bug/main.md` returns all THREE
  sites in their amended form** (facts 19, 19b). Capture the pre-change output first. **A run
  that returns two amended sites and one untouched has hit the wording trap.**
- **Rule 7 was SPLIT, not deleted** (fact 19a): its heading *"**Never closes or advances a
  bug**"* and its `/devforge:report-bug`-self claims are byte-identical, and only the embedded
  framework-wide clause changed. Instruction-reviewer confirms the amended rule cannot be read
  as licensing `/devforge:report-bug` itself to close a bug.
- **Under reading (i), Rule 8 is byte-identical** — and the rest of the file is NOT expected to
  be, so this criterion is scored on Rule 8 alone.
- **No plan vocabulary in emitted text** — "D1", "OQ-3", "Phase 2" and this plan's number are
  maintainer vocabulary. Emitted text names only commands, files and behaviors.

---

### Phase 4 — Docs sweep + dated reconciliation notes — ✅ DONE 2026-08-26 (`d09b7e2`)

**Route: instruction-author → instruction-reviewer** for every `src/` and plan-document edit.

Open the phase with `grep -rn "bugs/" src/ *.md` and reconcile every hit against what this
build made true. **This sweep list is NOT certified exhaustive** — treat a hit not named below
as an omission in this plan, not as a new defect.

Scope:

- **`src/devforge/storage-rules.md` — two falsified statements** (facts 16, 17): the
  `### How Bug Files Are Resolved` line *"the `Open → In Progress → Fixed` lifecycle is not
  driven by any command"*, and the File Lifecycle `fix` line's *"(no bugs/ files written either
  way)"*. Both are amended in place, narrowly — the manual path REMAINS valid; what changes is
  that it is no longer the only one.
- **Repo-root `CLAUDE.md`** — the plan-88 one-liner appended to the active-plans index, matching
  the neighbouring entries' density. **Read the file live for the append point**; the index
  grows and a pre-computed position rots.
- **`PLAN-STATUS-ARCHIVE.md`** — the mirrored full entry, per this repo's index/archive split.
- **`CHANGELOG.md`** — an entry under the existing `## [Unreleased]` → `### Added` (fact 31).
  **Read the file live** rather than creating a heading on the strength of this note.
- **`26-REINTRODUCE-FIX-PLAN.md`** — dated reconciliation notes at **three** sites: D2 (the
  free-text ban is EXTENDED, not reversed — D1), the window rule and its rationale (amended for
  feature-less runs — D2), and D4 + the `## Deferrals / follow-ups` `close-bug` bullet (the
  deferral is COLLECTED — fact 25). **Do not delete plan 26's reasoning**; it is still the
  record for the in-window path.
- **`83-DOWNSTREAM-REENTRY-SEED-PLAN.md`** — a dated note that cold mode is deliberately NOT a
  fourth seed producer, with D5's forced reasoning (fact 21).
- **`27-REPORT-BUG-COMMAND-PLAN.md`** — a dated note **only if** its text asserts that `bugs/`
  has no consumer or that the lifecycle is manual-only. **Read it and record the result either
  way** — "checked, no claim to amend" is a finding, and recording it stops the next session
  re-checking.
- **`21-DROP-FIX-REFACTOR-PLAN.md`** — **check only, and record the no-op as deliberate.** Its
  §4 replacement workflow and §5 accepted cost describe the *pre-plan-26* world and its D1
  already carries a supersession banner. **Deciding not to touch it is the decision; leaving it
  unmentioned is how a later session "harmonizes" it by mistake.**

#### Phase-4 check results *(recorded 2026-08-26)*

- **The three executable checks were RUN by the orchestrator on 2026-08-26, before the Phase-4 commit `d09b7e2`, and all three PASSED:** `scripts/verify-agent-reachability.py` exit 0 · `scripts/verify-memory-lane.py` exit 0 · the full `tests/` suite **11153 passed, 16 skipped, 175 subtests passed**. (Recorded from the orchestrator's report — the instruction-author who wrote this section had no shell and had flagged them as unrun; that flag is now CLOSED, not still open.)
- **`27-REPORT-BUG-COMMAND-PLAN.md` — CHECKED, NO EDIT.** The trigger condition was not met: it
  asserts neither *"`bugs/` has no consumer"* nor *"the lifecycle is manual-only"*. Its one
  now-narrowed sentence reports what plan 26 D4 says (*"`/fix` writes NO `bugs/` file"*) as the
  PREMISE for building `/devforge:report-bug` — and plan 26 D4 is itself amended in place by this
  build, so a reader following that pointer lands on the amended text. **Recorded so the check is
  not repeated.**
- **`21-DROP-FIX-REFACTOR-PLAN.md` — CHECKED, NO EDIT, deliberate.** Its three `bugs/` hits are
  all inside removal instructions describing v1 text being deleted (`/fix bugs/NNN-*.md` usage
  examples). They are historical records of a removal, not live claims, and its D1 already
  carries the plan-26 supersession banner.
- **`55-STANDALONE-BUG-FIX-LANE-PLAN.md` — NOT IN THIS PLAN'S SWEEP LIST; found by the sweep and
  EDITED.** See the ⚠ note in the status line at the top of this file. **This is the plan
  omission the sweep instruction anticipated**, and it is the most consequential one: plan 55
  designed this same lane in July and was sitting DEFERRED with four open decisions, so a future
  session could have built it a second time.
- **`91-FEATURE-DIR-IDENTITY-AND-PROVENANCE-PLAN.md` — NOT IN THIS PLAN'S SWEEP LIST; found by
  the sweep and EDITED (status only).** It referred to plan 88 as `NOT STARTED` at two sites, one
  of them inside its OQ-4 statement. Only the status parentheticals and a one-sentence
  corroboration were added; **OQ-4's substance and recommendation are untouched** and remain
  correct — this build changed no
  bug-file naming, and the cold lane resolves a bug file by the path the user types, so a rename
  would break a user-facing argument form.
- **`README.md`, `src/manifest.json`, `/devforge:implement`, `/devforge:review`,
  `/devforge:verify`, `/devforge:configure` — CHECKED, NO EDIT.** Every `bugs/` hit in these is
  still true after the build: the artifact-directory note, the `projectOwned` "NEVER overwrite"
  pattern, the wrapper-isolation artifact list, `/devforge:review`'s findings-only claim (it
  still writes no `bugs/` file), `/devforge:verify` PHASE 9 as a creator (unchanged), and the
  lint-ignore exclusion list.

**Commits: one per phase, no AI-attribution trailer** (this repo's commits carry none — match
the trailer-free convention), lowercase terse subject with a scope prefix matching
`git log --oneline`.

**Verify:**

- The sweep returns zero dangling references; the `tests/` suite is green.
- **`grep -n "not driven by any command\|no bugs/ files written" src/devforge/storage-rules.md`
  returns nothing** (facts 16, 17).
- **The `CHANGELOG.md` entry states the honest bound**: a cold lane inside one command, gated
  by the same back half, with an advisory conversational rubric. **An entry claiming the
  framework now closes bugs automatically has over-claimed by two layers.**
- **The repo-root one-liner names D6's honest bound** — the rubric is advisory and the only
  mechanical net is the in-command bounce.
- `scripts/verify-agent-reachability.py` and `scripts/verify-memory-lane.py` pass (nothing here
  touches either, so a failure means something unintended moved).
- **The plan-87 index bullet is byte-unchanged** — this is an append, not an edit of its
  neighbour.

---

### Phase 5 — Consumer e2e *(user-driven HARD GATE)* — DEFERRED AS A SEPARATE EFFORT 2026-08-27, NOT WAIVED, NOT RUN

⚠ **Dated note, 2026-08-27.** The plan was CLOSED on this date by maintainer statement — *"the
test is a separate story — mark it as done."* **That close covers the BUILD only. This phase was
NOT run and was NOT waived**: the maintainer moved it to a separate effort rather than
cancelling it, so the anchors below stay live as that effort's recipe. **A reader landing here
must not read the plan's CLOSED status as this phase having passed** — nothing below has ever
been observed, and a closed plan with an unrun hard gate is exactly the state this note exists
to keep visible.

**Everything above is build-verified, NOT consumer-validated.** No phase above may claim the
cold lane has been observed.

**Known-answer anchors**, so this is a regression anchor rather than an exploratory run:

1. **The happy path.** File a real defect with `/devforge:report-bug`, then run
   `/devforge:fix bugs/NNN-<slug>.md`. **MUST** produce: the D1 code-confirmation visible in the
   transcript (the quoted live code, not the bug file's own words); the full back half (OQ-2)
   running; **ONE clean `fix(scope):` commit with no `[WIP]` prefix**; and the bug file's
   `**Status**` flipped to `Fixed`, its `**Fixed**` date filled, and `## Fix Notes` written —
   **with every other field byte-unchanged.**
2. **The bounce.** Run cold mode on a bug whose repair is a behavior/architecture change.
   **MUST** bounce naming `/devforge:research` (not `/devforge:specify`), **MUST** write NO
   seed anywhere, and **MUST** leave the bug file `Open` and otherwise byte-unchanged.
3. **The rubric.** Observe the three-arm offer in conversation: a cold code-confirmed repair
   gets arm 2, and a confirmed problem needing a behavior change gets arm 3.

**Verify:**

- All three anchors are scored **explicitly** — stated, not summarized.
- **Anchors 1 and 2 are scored as a PAIR.** A triage that routes everything to the bounce
  passes 2 and fails 1; a triage that never bounces passes 1 and fails 2. **Neither is
  meaningful alone.**
- **Anchor 1 records the exact commit subject line as a STRING**, not as "looked right" — under
  D3 fork 2 arm (i), the wrapper case's subject is a known-ugly `[<branch>] - <title>` when the
  branch carries no ticket token, and Phase 5 is where a ratifier sees it.
- **Anchor 1 diffs the bug file** and confirms only the three D4 fields changed.
- **Anchor 3 records whether `/devforge:report-bug`'s own PHASE-4 pointer contradicted the
  rubric** (D6's counter-argument to reading (i), fact 13a). **A contradiction observed here is
  the trigger to re-open D6 as reading (ii)** — record it as such rather than as a nit.
- **If it fails**, record the negative here with the artifacts and identify which mechanism
  produced it before proposing anything: a missing confirmation is a D1 finding, a `[WIP]`
  prefix is a D3 finding, a wrong bounce target is a D5 finding, a mangled bug file is a D4
  finding. **They have different fixes.**
- **A clean run is NOT evidence the lane reduces ceremony.** It is evidence the lane works.
  **The friction claim rests on the 2026-08-25 maintainer statement and on nothing this phase
  can produce** — one run measures no ceremony delta.

---

## Non-goals

- **Reviving v1's free-text intake.** D1 admits a written `bugs/` FILE and nothing else. Plan
  26's D2 ban on typing a bug description into the command **survives verbatim** (fact 26), and
  a future session must not read the widened source list as reopening it.
- **Any change to the main pipeline commands.** `/devforge:research`, `specify`, `spec-check`,
  `plan`, `breakdown`, `implement`, `review`, `verify`, `summarize` and `finalize` are
  byte-unchanged. **The rejected "light lane" alternative is what a change there would have
  been**, and `## Origin` records why it was rejected.
- **A `ReEntrySeed` in cold mode.** D5 — forced by plan 83's feature-scoped seed path (fact 21),
  not preferred. **A feature-less seed carrier is a separate plan** and needs observed
  repetition as its trigger.
- **A numeric scope cap.** D7 — v1's 1-5-file guard is deliberately not reproduced, and plan
  27's D3 already settled the same question the same way.
- **Any change to `implement_helper`'s in-window behavior for `/devforge:implement`.** The D3
  extension is reachable only through a flag `/devforge:implement` never passes, exactly as the
  2026-06-19 task-less extension was. **`/devforge:implement` stays byte-identical.**
- **`/devforge:fix` becoming model-invocable.** OQ-6 — `disable-model-invocation: true` stays,
  the 13/7 counts are unchanged, and this plan contributes no delta. *(Amended 2026-09-03:
  done by plan 93, not by this plan — this bullet stays true as a statement about plan 88's
  own scope.)*
- **Creating `bugs/` files from `/devforge:fix`.** D4 permits exactly one write to exactly one
  already-existing file. `/devforge:report-bug` and `/devforge:verify` PHASE 9 remain the only
  CREATORS (fact 14).
- **A bulk or batch cold mode.** One bug file per run. Multi-file cold remediation is not
  designed, not argued, and not built.
- **Retro-closing the existing `bugs/` corpus.** This plan gives new cold fixes a route; it
  makes no claim about, and runs no pass over, bugs already on disk.
- **Any new mechanical check, `verify-*` gate, or hard-fail validator.** Plan 75's tripwire
  holds in both halves: **the cold lane adds a MODE, not a gate.** D4's `close-bug` is a writer
  with an input precondition, which is neither a check number nor a validator.

---

## Dependencies + related

- **`26-REINTRODUCE-FIX-PLAN.md`** — the plan this AMENDS, in three places and no more: D2's
  free-text ban is EXTENDED (D1), the in-window rule is amended for feature-less runs (D2), and
  the `close-bug` deferral is COLLECTED (D4, fact 25). **Everything else in plan 26 stands** —
  D3's back-half reuse, D5's `/refactor` drop, D6's thin-caller guarantee, D7's bounce.
- **`21-DROP-FIX-REFACTOR-PLAN.md`** — the historic record. Its §1 duplication argument, §4
  replacement workflow and §5 accepted cost describe the world before plan 26 reversed its D1.
  **Read, not edited** (Phase 4 records the no-op). ⚠ Its §4 workflow — hand-fix, one-off test,
  run verify commands, `/code-review` — **is the very thing this plan's cold lane replaces with
  a gated route**, so a session reading §4 as current guidance after this build has read a
  superseded page.
- **`27-REPORT-BUG-COMMAND-PLAN.md`** — the producer of the files this lane consumes, and the
  source of the schema D4 amends (its D4 extracted `_shared/bug_file.py`). Its **D3 stance —
  *"routing state, not a size metric"*, no LOC/file-count threshold — is D7's precedent.**
- **`83-DOWNSTREAM-REENTRY-SEED-PLAN.md`** — the seed model whose feature-scoping FORCES D5's
  no-seed answer (fact 21). **Nothing in it changes**; Phase 4 adds one dated note recording
  that cold mode is deliberately not a fourth producer.
- **`63-SKILL-COLLISION-SUPPRESSION-PLAN.md`** — the 13/7 model-invocable carve-out.
  **Untouched and unaffected** (OQ-6): no frontmatter invocation route changes. **Recorded so a
  Phase-4 sweep does not go hunting a count to update** — there is none.
- **`75-INVESTIGATION-SEARCH-HARNESS-PLAN.md`** — the no-new-check-number / no-new-validator
  tripwire. **Both halves hold.**
- **`87-ARTIFACT-LANGUAGE-GUARD-PLAN.md`** — its advisory-WARN detector rides
  `artifact_helper commit-artifacts` and **explicitly not `implement_helper wip-commit`**. **D3
  extends the uncovered path**, so a cold `fix(scope):` commit is outside the language guard
  exactly as a per-task commit already is. **No coverage regression — but no new coverage
  either**, and Phase 4's CHANGELOG entry must not imply otherwise.
- **`34-VERIFY-HYGIENE-FALSE-POSITIVE-PLAN.md` and plan 44** — the ADVISORY / WARN-only family
  D6's non-gating stance joins, alongside `/devforge:plan`'s stakes-hint (fact 23). **Cited for
  the stance; neither is touched.**
- **`37-PER-STEP-ARTIFACT-COMMIT-PLAN.md`** — the shared `commit-artifacts` chokepoint OQ-3's
  wrapper arm rides. **No behavior of it changes.**

---

## Context for next session

**The one sentence that governs everything here:** a cold bug gets a proportional route by
becoming a THIRD findings source for `/devforge:fix` — same back half, same gates, one clean
`fix(scope):` commit, one bug-file flip — and the main pipeline is not touched at all.

**Trap 1 — reading D1 as reopening plan 26's D2.** It does not. D2 banned a **free-text
description**; D1 admits a **written file with a schema**. `/devforge:fix` still consumes
findings and never invents them. **A session that widens the intake to typed prose has left
this plan**, and Phase 2's verify criteria exist to catch it.

**Trap 2 — treating a bug FILE as a confirmed defect.** `/devforge:report-bug` explicitly
*"reads no source code to confirm the defect."* D1's code-confirmation step is not ceremony —
**it is the only thing standing between a captured hunch and an edit to live code**, and OQ-1's
stop is where an unconfirmable bug ends.

**Trap 3 — calling `in-fix-window` on the cold path.** It returns `no_tasks_dir` and gates the
run OUT (fact 22). Keeping the call and instructing the model to ignore its answer is worse
than not calling it: it is a gate with a documented ignore-arm, which is the escape-hatch shape
this repo forbids by name. **The same trap has a quieter twin one sub-phase later:**
`read-findings` is equally feature-bound (fact 20a), so **cold mode produces no
`findings.json`** and every PHASE-1 sentence that reads *"the `items` from
`$WORKDIR/findings.json`"* must gain a cold carve-out. A cold arm that names that file
describes a file the run never wrote.

**Trap 4 — letting `--final` clear `.devforge/wip.md`.** `wip-commit` clears it
unconditionally today (fact 11), and the in-window path is safe only because the window gate
guarantees `/devforge:implement` has drained. **D2 removes that guarantee.** This is the single
most likely implementation defect in Phase 1.

**Trap 5 — undercounting the sites D4 falsifies.** The claim is not in one place in any of the
four files that carry it: **FOUR** sites in `fix/main.md` (fact 4), **FIVE clauses in a single
paragraph** plus a sixth workflow-prose site in `src/CLAUDE.md` (facts 29, 29b), **TWO** in
`storage-rules.md` (facts 16, 17), and **THREE** in `report-bug/main.md` (fact 19) — one of
which is embedded in Rule 7 and needs that rule SPLIT rather than deleted (fact 19a). **A
frontmatter description still promising `never writes bugs/` while the body writes one is
exactly the sentence-level rot this repo's discipline exists to prevent.** ⚠ **And the greps
differ per file**: `bugs/` finds the `fix/main.md` sites, but the `report-bug/main.md` sites
share only the arrow string `Open → In Progress → Fixed` — *"maintained manually"* misses one of
the three (fact 19b).

**Trap 6 — pointing the cold bounce at `/devforge:specify`.** It blocks until a research or
discover handoff exists in a feature directory (fact 32), and a cold bug has neither. **The two
bounces name different commands for a mechanical reason**, and "harmonizing" them breaks the
cold one.

**Trap 7 — reading D6 as a mechanism.** It is a conversational nudge with no check behind it
(fact 23's precedent). **The only mechanical net in this plan is D5's in-command bounce**,
which fires after the user has already typed the command.

**Trap 8 — editing `/devforge:report-bug` Rule 8** (fact 18). Rule 8 forbids that command from
chaining into `/devforge:fix`, and **Phase 0 ratified reading (i) on 2026-08-26: Rule 8 stays
BYTE-UNCHANGED and no forward pointer is added there.** A Phase 3 that touches it has left the
ratified design. ⚠ **This does not make `report-bug/main.md` a no-op file** — D4's three-site
manual-lifecycle correction lands in it under either reading (Trap 5).

**Trap 9 — treating fact rows 28/29/29a/29b as still-current.** `src/CLAUDE.md` was edited
after 2026-08-25 (grill became mandatory before `/devforge:breakdown`), so the text around
those anchors has moved. **Phase 3 re-verifies all four against the LIVE file** and re-derives
its edit from what it finds — see the dated caution under `## Verified mechanics`. The rows are
deliberately NOT refreshed: they are the dated observation the re-verification checks against.

**The working tree is uncommitted throughout**, and several plans this file cites are
working-tree state, so any "shipped" claim about them means reviewed-but-uncommitted rather
than released. Re-check each from the code rather than from a Status line.

**Discovered while drafting, NOT owned by this plan and not fixed here:**

1. **`/devforge:fix`'s `allowed-tools` omits `Read` and `Write`** while its body directs the
   orchestrator to use the Write tool (fact 3). **This is not a defect** — the field is a
   pre-approval grant, not a restriction (verified against current docs 2026-08-25) — but it
   means the command prompts for permission mid-run at PHASE 4. **Recorded as an ergonomics
   observation about the existing command**, not a bug this plan repairs.
2. **`/devforge:report-bug`'s forward pointer names a command that cannot consume its output**
   (facts 13a, 15): it sends the user to `/devforge:research`, which has zero `bugs/` awareness.
   **This plan gives the file a consumer but does not repair that pointer** — under D6 reading
   (i) the pointer is deliberately left alone, and D6's own counter-argument names the resulting
   two-answers-in-one-session problem as unresolved.

---

## When resuming work

1. **Read this file in full, then `## Verified mechanics` again** — thirty-three rows (1–32
   plus 13a, 19a, 19b, 20a, 29a, 29b), each checkable in under a minute. **If rows 3, 4, 9, 10,
   11, 13, 18, 19, 19a, 20a, 21, 22 or 29 no longer hold, stop and re-derive**: they are D3's
   whole basis, D4's schema and its blast radius, D5's forcing constraint, D6's collision, and
   D2's mechanical argument for bypassing all three of 0.2/0.3/0.4.
2. **Read `src/commands/fix/main.md` in full before touching it** — not just PHASE 0. The
   scratch-chain contract, the `$WORKDIR` re-derivation rule, the case-3 item shape and the
   four `bugs/` claim sites all constrain what Phase 2 may write.
3. **Read `src/devforge/lib/_implement/_cmds_commit.py` in full before touching it** — the
   module docstring's numbered rules, the two existing modes, the mixed-mode rejection and the
   unconditional wip-marker clear all constrain Phase 1.
4. **Read `src/devforge/lib/_shared/bug_file.py`'s `_format_bug` before writing `close-bug`.**
   The field names are `**Fixed**` and `## Fix Notes` — **not** `Fixed date`, **not** a bold
   `Fix Notes` field. Grep the strings.
5. **Re-verify every anchor before use. Grep the quoted string, never the `:NNN`** —
   `in-fix-window`, `fix_mode`, `clear_wip_marker`, `_Filled in after resolution._`,
   `not driven by any command`, `Never call`, `no bugs/ files written either way`,
   `Open → In Progress → Fixed`, `cold bug-fixer`, `## [Unreleased]`. ⚠ **Two anchors in this
   file are deliberately trimmed to a contiguous substring** because the source wraps across
   lines: `_window.py`'s `would stomp /implement's .devforge/wip.md` (D2) and `fix/main.md`'s
   `write the combined array yourself with the Write tool instead of this line` (Phase 2).
   **Do not "restore" the full sentence into the grep — it will not match.**
6. **Re-fetch the Claude Code authoring page before writing or amending any frontmatter**
   (`https://code.claude.com/docs/en/slash-commands`, which redirects to the skills page). The
   load-bearing fact is that **`allowed-tools` grants rather than restricts**; if a future
   version makes it restrictive, Phase 2's frontmatter reasoning changes and must be re-derived,
   not extended.
7. **Route every edit through the house loops:** **python-engineer → python-reviewer,
   test-first** for Phase 1; **instruction-author → instruction-reviewer + claude-code-guide**
   for Phase 2 (`main.md` ships and this phase touches its frontmatter) and Phase 3
   (`src/CLAUDE.md` ships as the consumer's root `CLAUDE.md`); **instruction-author →
   instruction-reviewer** for Phase 4's plan-document and docs edits. **Phase 1 dispatches no
   instruction-author and Phases 2–4 dispatch no python-engineer** — a phase that finds itself
   needing the other has crossed its own boundary and must stop.
8. **Do not let Phase 2's momentum turn the cold lane into a skip lane.** OQ-2 keeps the entire
   back half. The gates cold mode drops are the two that have no meaning without a feature
   (D2); **every gate about the CODE stays.** A cold lane that skips the panel is a hand-fix
   with extra steps, and the friction it was built to relieve was never the panel's.
