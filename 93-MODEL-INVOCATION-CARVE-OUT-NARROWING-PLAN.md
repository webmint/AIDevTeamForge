# 93 — Narrow the model-invocation carve-out to the setup chain (16/4)

**Status:** **✅ Phases 0–4 COMPLETE 2026-09-03.** Phase 0 CLOSED 2026-09-03 — D1–D4 ratified by the maintainer in-session, as recommended. Phase 1 `9cc0c91` (seven command files + `src/devforge/storage-rules.md`), Phase 2 `21d7211` (`src/CLAUDE.md`), Phase 3 `7c0b796` (six ledgers, root docs, **three** docstrings — including `breakdown_helper.py`'s `verify-grill-ran`, which that commit's message names). **Phase 0's record and Phase 4's install-ride + suite record ride in the closing commit that adds THIS FILE to git — that SHA cannot be known from inside the file it commits; re-derive it with `git log --oneline -1 -- 93-MODEL-INVOCATION-CARVE-OUT-NARROWING-PLAN.md`.** **Phase 5 DEFERRED — user-driven consumer e2e HARD GATE, NOT run and NOT waived.** **Build-verified only, NOT consumer-validated.**
**Branch:** `develop-2.0-init`
**Created:** 2026-09-03.

---

## Origin — the maintainer asked whether the seven-command carve-out is still justified

On **2026-09-03** the maintainer questioned whether keeping `disable-model-invocation: true` on
seven emitted commands was still justified, and asked for the pros, the cons and the scenarios.

The analysis that followed found this. Plan 63 (2026-08-07) resolved its OQ-2 as a **13/7**
carve-out — 13 commands model-invocable, 7 human-typed only: the four setup commands
(`init-forge`, `generate-docs`, `configure`, `constitute`), the two adversarial checks (`grill`,
`spec-check`) and `fix`. **That split rested on THREE different criteria, not one:** one-time
project mutation (the setup four), *"opt-in, never an auto-gate"* (`grill`, `spec-check`), and
plan 26 D2's *"proposal-only"* (`fix`).

**Two of the three have since expired or were never argued on their own.**

- **Plan 82** (2026-08-19) made `/devforge:spec-check` a required precondition of
  `/devforge:plan`, and **plan 85** (2026-08-26) made `/devforge:grill` a required precondition
  of `/devforge:breakdown`. *"Opt-in"* is false for both, and has been for months.
- Plan 26 D2's *"never auto-invoked"* sentence was written when **EVERY** forge command carried
  the flag — its own text says so: *"The model NEVER auto-invokes `/fix` (every forge command
  sets `disable-model-invocation: true`)"*. It therefore **inherited the then-universal flag
  rather than arguing a `fix`-specific reason.** Plan 63's OQ-3 then kept `fix` flagged
  *because it is in the keep-7 set*, and plan 88's OQ-6 (2026-08-26) kept it with the argument
  that cold mode makes it reachable in more situations.

**The maintainer's stated goal is narrow: stop having to TYPE these three commands by hand.**
An autonomous end-to-end cycle is explicitly **NOT** wanted now, and is recorded in
`## Non-goals` rather than left to be inferred.

---

## What is actually being added

Nothing is added. **Three frontmatter lines are removed**, and every sentence in the emitted
corpus that describes those three commands as human-typed is rewritten to the shape D2 ratifies:
run on the user's say-so — typed, or agreed to when offered — never on a command's own
initiative, one agreement per command.

**This is a permissions narrowing, not a feature.** It ships **no Python logic** — three docstring
corrections and nothing else — no gate, no validator and no check number. Its entire content is
(a) three deleted lines, (b) prose that stops asserting a fact that would no longer be true, and
(c) dated amendments to the six plan files and the root documents that recorded the 13/7 split.
**(The docstring count was drafted as two and is three as built — see the inventory addendum and
the amended `## Non-goals` entry.)**

**⚠ It also removes the LAST mechanical human-presence stop inside the feature pipeline.** That
is stated plainly in `## What mechanically stops the model today` below, it was accepted
explicitly by the maintainer, and no phase may describe this change as cost-free.

---

## Measured facts — the context arithmetic (measured 2026-09-03 against the live tree)

The consumer overlay `src/CLAUDE.md` is loaded in **every** consumer session and is **never**
subject to the skill-listing budget. It compensates for the seven invisible descriptions with
full catalog entries. Sizes in characters:

| Command | `src/CLAUDE.md` catalog entry | frontmatter `description` |
|---|---:|---:|
| `spec-check` | 2,239 | 1,247 |
| `grill` | 2,669 | 859 |
| `fix` | 2,911 | 819 |
| **Three-command total** | **7,819** | **2,925** |

| Group | Catalog-entry total |
|---|---:|
| The 7 human-typed commands | 9,021 |
| The 13 model-invocable commands | 2,137 |

**Conclusion, recorded because it reverses the documented rationale:** the docs' *"saves
context"* claim for the flag is **INVERTED in this framework**. The three flagged commands cost
roughly **2.7×** more always-on context through their catalog entries (7,819 chars in every
session) than their descriptions would cost in the skill listing (2,925 chars, and only while
the listing has budget). The flag saves context in a project that does not compensate for it;
this project compensates for it in the one file that is always loaded.

---

## Verified mechanics — Claude Code authoring surface (2026-09-03)

Verified via the **`claude-code-guide`** agent against
`https://code.claude.com/docs/en/skills.md` and
`https://code.claude.com/docs/en/features-overview.md`. Quoted here so a future author
re-verifies rather than trusting this file.

**THREE verification passes were performed in the authoring session:** one for the key's
semantics, one for the listing budget, and **a third during Phase 1**, when the author fetched
`https://code.claude.com/docs/en/slash-commands` — which **301-redirects to the skills page** —
and re-confirmed three things: the default `false` restores model invocation **and** puts the
`description` into the skill listing; **`argument-hint` and `allowed-tools` are unaffected** by
the key, so removing it changes neither; and the **1,536-character cap** and the **1% listing
budget** are exactly as recorded in facts 6–8.

**⚠ Dated correction, 2026-09-03 (recorded after the build, never silently).** An earlier
revision of this paragraph read *"the verification pass was performed TWICE … no third pass is
claimed."* **That is false** — the third pass happened, and it is recorded above. The sentence
is replaced rather than deleted so the correction stays visible to a reader who saw the earlier
form.

| # | Fact | Source |
|---|------|--------|
| 1 | `disable-model-invocation`: *"Set to `true` to prevent Claude from automatically loading this skill. Use for workflows you want to trigger manually with `/name`."* Default `false` | skills reference |
| 2 | *"Skills with `disable-model-invocation: true` are invisible to Claude until you invoke them manually."* and *"Use `disable-model-invocation: true` for skills with side effects. This saves context and ensures only you trigger them."* | features overview |
| 3 | From **v2.1.196** such skills are also **not preloaded into subagents** and **do not run on scheduled-task triggers** | features overview |
| 4 | An inverse key exists — `user-invocable: false` hides a skill from the `/` menu (Claude-only). **Not used by this plan** | skills reference |
| 5 | *"For model-invocable skills, Claude sees names and descriptions in every request."* | skills reference |
| 6 | The listing *"budget scales at 1% of the model's context window"*; *"When the listing overflows, Claude Code drops descriptions starting with the skills you invoke least, so the skills you use most keep their full text."* | skills reference |
| 7 | **"The listing always contains every skill name."** | skills reference |
| 8 | Each entry's combined `description` + `when_to_use` is capped at **1,536** characters (`skillListingMaxDescChars`); budget tunables are `skillListingBudgetFraction` and `SLASH_COMMAND_TOOL_CHAR_BUDGET`; `/doctor` estimates the listing cost | skills reference |
| 9 | Frontmatter fields are **all optional** — removing the key yields the documented default (`false`) | skills reference |

**Consequence for D3, derived from facts 6 and 7 together.** After the flip, `grill` and
`spec-check` — invoked once per feature — are **first in line to lose their DESCRIPTION** under
listing pressure, **but never their NAME**. And the `/devforge:plan` and `/devforge:breakdown`
gates name both commands in their BLOCKED stderr anyway. **So awareness of the name is
reliable, and the description is a convenience.** This is the answer to plan 85 D6's
*"unreliable awareness"* argument, and it is the reason D3's trim is safe rather than merely
cheap.

---

## What mechanically stops the model today, and what does not

**This subsection is the load-bearing honesty of the plan.** It is the reason D1 could be
ratified without a long argument, and the reason nobody may later describe this change as
merely cosmetic.

**MECHANICAL, un-bypassable by the model — exactly one thing:** `disable-model-invocation: true`
(the Skill tool refuses). Today it sits on the setup four plus `grill`, `spec-check` and `fix`.

**PROSE, bypassable by the model — everything else:**

- **Spec approval and plan approval are IMPLICIT.** `plan_helper check-status-and-flip` and
  `breakdown_helper check-status-and-flip` flip Draft → Approved on invocation of the NEXT
  command, and both print an implicit-approval notice —
  `"Spec status: Draft → Approved (implicit approval via /devforge:plan invocation)."`
  (`src/commands/plan/main.md:160`) and
  `"Plan status: Draft → Approved (implicit approval via /devforge:breakdown)."`
  (`src/commands/breakdown/main.md:113`). **Both of those commands have been model-invocable
  since plan 63.**
- Task-list approval in `/devforge:breakdown`, the per-task hard gate in `/devforge:implement`,
  the squash confirmation in `/devforge:finalize` (`finalize_helper squash --confirm`, a flag
  **the orchestrator itself passes**) and intake's `--accept-gaps` (`FINDINGS.md` finding 2) are
  all *end the turn* / `AskUserQuestion` instructions, or flags the orchestrator supplies.
- Helper preflights that read files — the spec-check hash, `grill.md` presence, the handoffs,
  the `**Status**:` fields — **enforce ORDER, not human presence.** The orchestrator produces
  those files by running the earlier command.

**Therefore this plan removes the last mechanical human-presence stop between
`/devforge:research` and `/devforge:finalize`.** The setup chain keeps its own. After this
change, human-first in the feature pipeline is **prose plus `AskUserQuestion`** and nothing
else. **The maintainer accepted this explicitly on 2026-09-03.**

---

## Decisions — ratified 2026-09-03

Each carries its recommendation, its reasoning, its rejected alternatives and a retained
counter-argument. **Phase 0 is closed; nothing below is open.** The counter-arguments are
retained deliberately — they are what a future session needs in order to re-open a decision
honestly rather than by drift.

### D1 — Scope: flip `grill`, `spec-check`, `fix`; keep the setup four. 13/7 → 16/4 *(RATIFIED 2026-09-03)*

**The rule.** A command keeps `disable-model-invocation: true` if and only if it performs a
**ONE-TIME mutation of the framework's own basis under `.devforge/`** — config, constitution,
docs knowledge base — **with NO feature scope**. That is a single objective criterion, and it
selects exactly `init-forge`, `generate-docs`, `configure`, `constitute`. Every other command
operates on a feature or on a written finding, and carries an internal human gate.

**Reasoning.** The 13/7 placement is historical rather than designed: three criteria, two of
which have expired (`grill`, `spec-check` are no longer opt-in) or were inherited rather than
argued (`fix`). Replacing three criteria with one removes the drift surface — a future command
is classified by asking one question, not by asking which of three families it resembles.

**Rejected alternatives:**

- **(a) Flip all 20.** A spontaneous re-run of `/devforge:generate-docs` or
  `/devforge:configure` on an ordinary request like *"update the docs"* is a real misfire with a
  long wall-clock and a project-wide write. The setup chain's cost of being wrong is
  qualitatively different from a feature command's.
- **(b) Keep 13/7.** Its placement is historical, not designed, and two of its three reasons
  have expired. Keeping it means keeping three criteria to maintain.
- **(c) 15/5, re-flagging `finalize` as the one irreversible step.** A coherent alternative —
  *"autonomous up to the irreversible squash"* — **REJECTED by the maintainer because it ADDS a
  keystroke where the stated goal is to remove them.** **Recorded as the named re-open shape**
  if an autonomous cycle is ever wanted with one mandatory stop.

*Counter-argument, retained:* `/devforge:fix` writes code and commits. **Accepted as true.** The
defence is symmetry and staging: `/devforge:implement` also writes code and commits and has been
model-invocable since plan 63; and `fix`'s worst case is an **unsolicited PROPOSAL** rejected at
its own two-stage hard gate, **with no write before that gate**. A ratifier who found that
unpersuasive would have had to explain why `implement` is safe and `fix` is not.

### D2 — One agreement per command; no bundling *(RATIFIED 2026-09-03)*

**The rule.** On the BLOCKED path of `/devforge:plan` (missing or stale `spec-check.md`) and of
`/devforge:breakdown` (missing `grill.md` or a non-complete recorded adversary status), the
orchestrator **copies the helper stderr verbatim (unchanged)**, **OFFERS** to run the named
command now, and **ends the turn**. On agreement it runs **that ONE command**. When that command
finishes, the next command — the `/devforge:plan` or `/devforge:breakdown` re-run — is proposed
as **its OWN agreement**. **Never two commands on one "yes."**

For `fix`: the fix-or-file offer's **arm (A)** is executed by the orchestrator on agreement,
instead of asking the user to type it. **`fix` is still never self-initiated** — it is offered
only for a user-raised, code-confirmed defect or for written findings, and `src/CLAUDE.md`'s
rule *"If the defect is unconfirmed or you originated it, offer only `/devforge:report-bug`"*
is **unchanged**.

**Reasoning.** This is exactly the maintainer's line: no hand-typing, no autonomous cycle. One
agreement per command keeps the human in the loop at every stage transition while removing the
keystroke, which is the whole ask.

**Rejected alternative:** chaining *"run spec-check then re-run plan"* on one agreement. **That
is the first step toward the autonomous cycle the maintainer declined**, and it is rejected for
that reason and not for a technical one.

*Counter-argument, retained, and it is the honest bound:* **this rule is prose, and nothing
mechanical enforces it.** A model that chains two commands on one "yes" violates an instruction,
not a gate. There is no proposal here to mechanize it — mechanizing it would require exactly the
flag this plan removes.

### D3 — Descriptions trimmed to plan 63 OQ-1's ≈40-word budget; catalog entries take the short form of the other thirteen *(RATIFIED 2026-09-03)*

**The rule.** Each of the three `description:` lines is rewritten to plan 63 OQ-1's ≈40-word
budget (**≈40–60 words**; the hard cap is fact 8's 1,536 characters, which is not the binding
constraint). Each of the three `src/CLAUDE.md` catalog entries is rewritten to the **short form
the other thirteen already use**.

**⚠ Dated reconciliation, 2026-09-03 (amended in place after the build, never silently).** This
rule was drafted as *"≈40–50 words"*. **The shipped descriptions are 56 / 59 / 55 words** —
`grill` / `spec-check` / `fix` — at **430 / 423 / 409 characters**, all far under fact 8's
1,536-character cap. The band is widened to **≈40–60 words** to match what the five mandatory
content elements (Phase 1, scope item 2) actually cost, rather than leaving a criterion the
build could not meet. **The band moved; nothing else in D3 did**, and the catalog-entry bar is
reconciled separately under Phase 2.

**⚠ YAML note, recorded after the build (2026-09-03).** The literal description wording the
drafting brief proposed contained a **colon-space (`: `) inside a plain YAML scalar**, which is
not permissible in an unquoted value — **the frontmatter would not have parsed.** The shipped
descriptions use **the file's own em-dash connector style** instead, and the build verified this
with a colon-space scan across all three `description:` lines. **A future rewrite that
reintroduces `: ` inside an unquoted `description:` breaks the frontmatter, not just the
prose** — quote the scalar or keep the em-dash.

**Reasoning, three parts:**

1. The three descriptions now **enter the 1% listing budget**, and as the least-invoked commands
   they are **first in line to be dropped** (fact 6). A long description is the first thing cut
   anyway; a short one may survive.
2. The catalog entries were long **ONLY because** `src/CLAUDE.md:77` declared that section *"the
   only place the model sees what they do"*. **That stops being true for these three**, so the
   reason for their length evaporates with the flag.
3. The short form is not an invention — it is what thirteen sibling entries already do
   (2,137 chars across thirteen, against 9,021 across seven).

**Rejected alternative:** keep the long entries *"for reliability"*. The gates name the commands
in their BLOCKED stderr, the NAME never evicts (fact 7), and the long entries are ~7,800 chars
of always-on context in every consumer session.

*Counter-argument, retained:* after the trim, **a consumer whose skill listing is over budget
sees these three commands by name plus a one-line catalog entry — not their full contract —
until the command loads.** That is a real reduction in what the model knows before invocation.
It is accepted because invocation loads the full body, and because the pre-trim alternative
charged every session for a contract most sessions never use.

### D4 — Vehicle: this plan file, with dated in-place amendments to every ledger that recorded 13/7 *(RATIFIED 2026-09-03)*

**The rule.** This plan file is the vehicle, and every plan document that recorded the 13/7
split receives a **dated in-place amendment** rather than a rewrite. **Nothing is deleted.**

**Reasoning.** Plans 82, 85 and 88 each amended plan 63's OQ-2 in place when they touched the
split — that is the established house move for this particular record. **Six plan files carry
statements that become false** on the day the flag comes off, and each is a statement a future
session would read as ground truth.

**Rejected alternative:** amend plan 63 OQ-2 only. Cheaper, but it breaks the plan-per-change
convention and **leaves plan 26 D2, plan 82 D5(a-ii), plan 83 fact 12, plan 85 D6 and plan 88
OQ-6 each asserting a flag that no longer exists** — five separate seeds for exactly the
future-session hallucination this repo's discipline rules name.

*Counter-argument, retained:* eleven dated amendment blocks across eleven files is a large,
low-value diff for a three-line change. **Accepted as the price**: the alternative is a corpus in
which the cheapest thing to read is the wrong thing.

---

## Complete inventory

**All line numbers verified 2026-09-03 against the live tree.** ⚠ **Grep the quoted text, never
the digits** — this repo has documented anchor rot. **This inventory is NOT certified
exhaustive**: a hit not named here is an omission in this plan, not a new defect.

### Group 1 — frontmatter, 3 files

| File | Flag | `description:` |
|---|---|---|
| `src/commands/grill/main.md` | `:5` | `:3`, ends *"Human-typed only — `/devforge:breakdown` requires that it RAN, never that its disposition binds."* |
| `src/commands/spec-check/main.md` | `:5` | `:3`, ends *"Runs only when the USER invokes it — never auto-invoked — and `/devforge:plan` requires a fresh report from it: …"* |
| `src/commands/fix/main.md` | `:5` | `:3`, opens *"Proposal-only gated remediation … OFFERED (never auto-invoked) …"* |

### Group 2 — command bodies, 7 files

- `grill/main.md:76` — *"runs only when the USER types it — nothing auto-runs it"*; `:447`
  Rule 1 — *"is still typed by the USER and never auto-runs — a blocked `/devforge:breakdown`
  NAMES this command for the user to run, it does not run it"*.
- `spec-check/main.md:10` — *"each is typed by the user, never auto-runs"*; `:22` —
  *"**User-invoked, …** … runs because the USER invoked it … it NEVER auto-runs … names
  `/devforge:spec-check` for the user to run"*; `:313` Rule 1 — *"**User-invoked, never
  auto-invoked …**"*.
- `fix/main.md:25` — *"never auto-invoked (this command sets `disable-model-invocation: true` in
  its own frontmatter, so the model cannot invoke it)"*; `:242` — *"Both are human-typed only,
  so name them for the user rather than running them."*; `:482` Rule 1 — *"**Proposal-only,
  never auto-invoked** … the user types `/devforge:fix`. The model never runs it autonomously
  (`disable-model-invocation: true`)."*
- `plan/main.md:144` — *"`/devforge:spec-check` is user-invoked: name it, never run it
  yourself. …"*
- `breakdown/main.md:93` — *"`/devforge:grill` is user-invoked: name it, never run it
  yourself. …"*
- `review/main.md:376` and `verify/main.md:386` — *"the user types `/devforge:fix` to take
  arm A"*.

### Group 3 — `src/CLAUDE.md`, 1 file, TEN sites as drafted (ELEVEN as built)

`:47` (*"Seven are **human-typed only**"* … *"Never invoke those seven"*), `:51` (the
`/devforge:spec-check` step paragraph — *"It never auto-runs: the USER types it"*), `:53` (the
`/devforge:fix` paragraph — *"The model OFFERS either lane, the user invokes it"*), `:58` (the
command-list bullet — *"**Required before `/devforge:plan`, typed by the user**"*), `:60` (the
command-list bullet — *"**Required before `/devforge:breakdown`, typed by the user**"*), `:77`
(*"Seven commands … this section is the only place the model sees what they do"*), `:89`
(spec-check catalog entry), `:98` (grill catalog entry), `:110` (fix catalog entry), `:144`
(*"Never auto-run `/devforge:fix`: it is human-typed only"*).

⚠ **`:51`, `:53`, `:58` and `:60` were discovered during this plan's authoring sweep and are
NOT in the drafting brief's list.** They are recorded here because a Phase-2 sweep that greps
only for the word *"seven"* misses all four. ⚠ **An ELEVENTH site, `:92`, was found by the
build** and is recorded in the addendum — **two independent sweeps, each missing sites the next
one found.**

### Group 4 — ledgers, 6 plan files (dated in-place amendments, nothing deleted)

`26-REINTRODUCE-FIX-PLAN.md` D2 (`:21`); `63-SKILL-COLLISION-SUPPRESSION-PLAN.md` OQ-2
(`:221`ff — **two prior amendments already sit there**) + OQ-3 (`:281`) + its
`disable-model-invocation` count facts; `82-SPEC-CHECK-SUBJECT-RESOLUTION-MANDATORY-PLAN.md`
D5(a-ii) (grep *"blocked message names the command for the USER to type"*) + `:345`–`:351`;
`83-DOWNSTREAM-REENTRY-SEED-PLAN.md` fact 12 (`:49`) + `:301` (*"present by construction"*);
`85-GRILL-MANDATORY-AUTO-ACCEPT-PLAN.md` D6 (grep *"13 model-invocable / 7
human-typed-only"*) + `:178`–`:190`; `88-COLD-FIX-BUGS-LANE-PLAN.md` OQ-6 (`:727`–`:737`) +
`:1219`–`:1220`.

### Group 5 — root docs, 5 files

Repo-root `CLAUDE.md` router row (`:111` — *"13 commands model-invocable, 7 human-typed-only
(`disable-model-invocation: true`: …)"*) plus the index one-liners for plans 63, 82, 85 and 88
that state 13/7; `PLAN-STATUS-ARCHIVE.md` (**8** matching lines for `13/7|human-typed`, counted
live 2026-09-03 — **re-derive this number, never quote it**); `README.md:54`
(*"Thirteen of the twenty are model-invocable … Seven are human-typed only …"*);
`DEVELOPMENT-STATUS.md:11` (*"Thirteen commands are model-invocable; seven keep
`disable-model-invocation: true` …"*); `CHANGELOG.md` `## [Unreleased]`.

### Group 6 — Python docstrings only, 2 files as drafted (3 as built), no logic

⚠ **The build touched a THIRD docstring** — `src/devforge/lib/breakdown_helper.py` — recorded in
the addendum below. **No logic, no signature and no stderr string moved in any of the three.**


`scripts/lib/memory_lane.py:69`–`:73` (*"The 20 `_PROMOTED` commands also split 13
model-invocable / 7 human-typed-only … `grill` and `fix` are human-typed-only yet READS here"*)
and `tests/lib/test_memory_lane.py:233`. ⚠ **The memory-lane 13/7 is a DIFFERENT split**
(READS / N/A) that merely **coincided numerically** with the invocation split. Say so in the
correction; do not renumber it to 16/4.

### Addendum — sites the BUILD found beyond the tables *(2026-09-03, recorded after the build)*

**The six group tables above were composed before the build. The build found more.** They are
recorded here rather than folded into the tables, so the gap between what a pre-build sweep sees
and what a build touches stays visible. **The "not certified exhaustive" disclaimer at the top of
this section still stands and is not weakened by this addendum.**

- **`src/commands/grill/main.md:17`** and **`src/commands/spec-check/main.md:67`** — two further
  body sentences carrying the human-typed framing, invisible to the Group-2 anchors.
- **`src/CLAUDE.md:51`, `:53`, `:58`, `:60`** — already named in Group 3 from this plan's own
  authoring sweep — **plus `:92`**, which the build found and Group 3 does not list.
- **`src/devforge/storage-rules.md:258`** — the `spec-check` row, *"user-invoked"* → *"run on the
  user's agreement"*. **This file is named in NO group table**; it rode Phase 1's commit
  `9cc0c91`.
- **`README.md:56`, `:72`, `:74`, `:86`** and **`DEVELOPMENT-STATUS.md:17`, `:41`** — beyond the
  single line each that Group 5 names.
- **`CHANGELOG.md:19`, `:41`, `:53`** — supersession notes and one inline correction on the
  plan-85, plan-74 and plan-63 bullets. Group 5 named only the `## [Unreleased]` section.
- **`src/devforge/lib/breakdown_helper.py`** — the `verify-grill-ran` docstring, **in Phase 3's
  commit `7c0b796`**, whose own message names it alongside
  `tests/lib/test_breakdown_helper.py 431 passed`. **Prose only; the verb's stderr is
  byte-unchanged.** ⚠ **This is a THIRD Python docstring**, beyond Group 6's two, and it forces
  the dated amendment recorded under `## Non-goals`.

### Verified NO-OPs — do NOT edit these

- **No Python, script or test reads the key.** `grep -rln disable-model-invocation src/devforge
  scripts tests` returns **empty**; a repo-wide `*.py` grep for `disable-model-invocation` /
  `disable_model_invocation` returns **no files**. `scripts/emitters/claude.py` passes
  frontmatter through — plan 63 Phase 2 removed the flag from 13 `main.md` files and the emit
  followed.
- `src/commands/report-bug/main.md:94` already describes model-invocation
  (*"It may be model-invoked … as well as typed by the user"*) — **no edit**.
- **`report-bug/main.md` Rule 8** (*"Never call `/devforge:fix` from here"*) stays
  **byte-unchanged**. ⚠ It is now the **only** bar against an in-command chain report-bug → fix,
  and **plan 88 D6's retained counter-argument becomes live**.
- `src/commands/discover/main.md:691` and `src/commands/research/main.md:1240` — both say
  *"name `/devforge:configure` for them to type … that command is human-typed only, so never
  run it yourself."* **True under D1 and correct as written.** Recorded so a Phase-1 sweep for
  *"human-typed only"* does not "fix" them.
- `src/devforge/lib/_plan/_stakes.py:300`–`:304`'s hint —
  *"/devforge:grill is required before /devforge:breakdown will decompose"* — **stays true.**
- Plans 70, 74, 81, 87, 89, 90 and 92 each state *"this plan contributes no 13/7 delta"*. **True
  as dated history. NOT edited.**
- Plan 92's *"`configure` stays human-typed"* is **still true** under D1.

---

## Phases

### Phase 0 — Ratification *(CLOSED 2026-09-03)*

D1–D4 ratified **as recommended**, by the maintainer's in-session pick.

**Verify:**

- `grep -n "^### D[1-4] " 93-MODEL-INVOCATION-CARVE-OUT-NARROWING-PLAN.md` returns four lines and
  **every one carries `*(RATIFIED 2026-09-03)*`** — no decision heading in this file is marked
  open.
- **Each decision still carries its counter-argument.** A ratified decision with its
  counter-argument deleted cannot be re-opened honestly.
- **D1's rejected alternative (c) is recorded as the named re-open shape**, not deleted.

---

### Phase 1 — Command files *(instruction-only)*

**Route: instruction-author → instruction-reviewer.** ⚠ **The `claude-code-guide` frontmatter
verification was PERFORMED in-session on 2026-09-03** — facts 1–9 are its output — **and this
phase's author performed the THIRD fetch recorded under `## Verified mechanics`**
(`https://code.claude.com/docs/en/slash-commands`, 301 → the skills page), confirming that
removing the key restores model invocation, puts the `description` into the listing, and leaves
`argument-hint` and `allowed-tools` untouched. **A phase that finds itself needing a fact not in
that table owes a fresh pass.**

Scope:

1. **Remove the three flag lines** (Group 1).
2. **Rewrite the three `description:` lines** to ≈40–60 words. Each MUST state: what the command
   does, where it sits in the chain, what it writes, that the downstream gate requires it **RAN**
   / requires a **fresh report** and **never the verdict**, and that a clean run ends without a
   question.
3. **Rewrite every Group-2 sentence to D2's shape** — run on the user's say-so (typed, or agreed
   to when offered); never on a command's own initiative; one agreement per command.
4. **⚠ Added during the build, 2026-09-03 (recorded, not silent): `src/devforge/storage-rules.md`
   `:258`** — the `spec-check` row's *"user-invoked"* → *"run on the user's agreement"*. **That
   file is named in no group table above**; it is in the addendum, and it rode this phase's
   commit `9cc0c91`. **Its `## File Lifecycle` block is deliberately NOT otherwise touched** —
   see the known residual under `## Context for next session`.

**Verify:**

- `grep -n disable-model-invocation src/commands/*/main.md` returns **exactly the four setup
  files** (`init-forge`, `generate-docs`, `configure`, `constitute`). **MET** — see Phase 4's
  recorded run.
- `grep -rn -i "human-typed\|never auto-invoked\|never run it yourself\|user types \`/devforge"
  src/commands/{grill,spec-check,fix,plan,breakdown,review,verify}/main.md` returns **zero
  hits**. **⚠ Dated reconciliation, 2026-09-03: this criterion is MET with ONE expected,
  CORRECT match** — `src/commands/fix/main.md:481`, *"the user types `/devforge:fix` **or agrees
  to the offer**"*. **Typing remains one of two routes**, so the sentence is true post-flip and
  must NOT be "fixed"; `src/commands/spec-check/main.md:312` carries the same shape. **A future
  sweep that drives this grep to literal zero would delete a correct sentence.**
- Each new `description` is **≤ 1,536 characters** (fact 8) and **≈40–60 words**. **MET** —
  shipped at **56 / 59 / 55 words** and **430 / 423 / 409 characters** (`grill` / `spec-check` /
  `fix`). ⚠ **The band was widened from the drafted ≈40–50 during this reconciliation; the
  reasoning is under D3, not here.**
- **`src/commands/report-bug/main.md` is byte-unchanged**, Rule 8 included.
- **`src/commands/discover/main.md` and `src/commands/research/main.md` are byte-unchanged** —
  their `/devforge:configure` sentences are verified no-ops.
- `git status` shows **zero** files modified under `src/devforge/lib/` — this phase is
  instruction-only. **⚠ Dated reconciliation, 2026-09-03: MET for Phase 1's own commit
  `9cc0c91`**, whose file list is the seven command files plus `src/devforge/storage-rules.md` —
  which sits **beside** `src/devforge/lib/`, not inside it. **The third Python docstring the
  addendum records (`breakdown_helper.py`) is NOT in this commit.**

---

### Phase 2 — `src/CLAUDE.md`

**Route: instruction-author → instruction-reviewer.** This file ships as a consumer project's
root `CLAUDE.md`.

Scope — the ten Group-3 sites, **plus `:92`, which the build found** (eleven in total):

- **`:47`** → *"Four are human-typed only …"*, naming the setup four, **plus D2's
  one-agreement-per-command sentence.**
- **`:51`, `:53`, `:58`, `:60`** → the four sites discovered in this plan's sweep: drop the
  *typed by the user* / *never auto-runs* / *the user invokes it* clauses; **keep every gate
  predicate sentence intact.**
- **`:77`** → *"Four commands — the setup chain — …"*. The clause *"this section is the only
  place the model sees what they do"* narrows to the four.
- **`:89` / `:98` / `:110`** → short entries in the shape of the other thirteen. **The gate
  predicate survives in one clause each**: presence + freshness for `spec-check`, presence +
  recorded adversary status for `grill`. `fix` keeps *"consumes written findings only"* and both
  lanes. ⚠ **Dated reconciliation, 2026-09-03: the drafted *"offer it; run it once the user
  agrees"* tail was DROPPED on the second cut** — `:47` states that rule once for every command,
  so repeating it three times bought nothing and cost the ≤ 400-char bar. See this phase's Verify
  block.
- **`:92`** → **found by the build, in no group table above.** Recorded in the inventory
  addendum.
- **`:144`** → *"Never run `/devforge:fix` unoffered: propose it, and run it only once the user
  agrees."*

**Verify:**

- `grep -n -i "seven\|human-typed\|never auto" src/CLAUDE.md` returns **only the four-setup
  sentences**.
- The three rewritten catalog entries are each **≤ 400 characters** (the thirteen siblings
  average 164). **MET at 385 / 386 / 394 characters** (`spec-check` / `grill` / `fix`). ⚠ **Dated
  reconciliation, 2026-09-03: the bar was met on the SECOND cut, not the first.** The first cut
  landed at roughly **520 / 525 / 650** characters; **the instruction-reviewer caught it** and
  the phase re-trimmed. Two things were dropped to get there, and both are recorded so nobody
  restores them as "missing": (a) the per-entry *"propose it, run it once the user agrees"* tail,
  **redundant because `src/CLAUDE.md:47` already states that rule for every command**; and (b)
  from the `fix` entry, the *"not a pipeline step"* clause — **stated twice, and it survives at
  `:53`** — plus the names of the bounce artifacts and the `/devforge:finalize` squash, **which
  survive at `:65`**. **Nothing dropped is stated nowhere else.**
- **Every gate predicate is preserved verbatim in substance** — presence + freshness
  (`/devforge:plan`), presence + recorded adversary status (`/devforge:breakdown`), **never the
  verdict, no override, no skip.** Plans 82 and 85 are untouched by this phase.
- **The `/devforge:report-bug`-before-`/devforge:fix` rule at `:144`'s first sentence is
  unchanged** — only the second sentence moves.

---

### Phase 3 — Ledgers, root docs, docstrings *(Groups 4–6)*

**Route: instruction-author → instruction-reviewer** for every plan-document and root-doc edit.

Scope:

- **Dated `**(AMENDED 2026-09-03 — plan 93)**` blocks appended at each Group-4 site. NOTHING
  deleted** (D4).
- **Repo-root `CLAUDE.md`**: the plan-93 index one-liner (pure append), and the router row's
  counts → **16/4** with the four names.
- **`PLAN-STATUS-ARCHIVE.md`**: the mirrored full plan-93 entry, per this repo's index/archive
  split.
- **`README.md:54`** and **`DEVELOPMENT-STATUS.md:11`**: counts → sixteen / four. ⚠ **Dated
  reconciliation, 2026-09-03: one line each was NOT enough** — the build also edited
  `README.md:56`, `:72`, `:74`, `:86` and `DEVELOPMENT-STATUS.md:17`, `:41`. See the inventory
  addendum.
- **`CHANGELOG.md`**: an entry under the existing `## [Unreleased]`. **Read the file live; do not
  create a stray heading on the strength of this note.** ⚠ **Dated reconciliation, 2026-09-03:
  the build also touched `:19`, `:41` and `:53`** — supersession notes on the plan-85 and plan-74
  bullets, and an inline correction of a stale seven-keep claim on the plan-63 bullet (an
  instruction-reviewer finding, fixed in this phase).
- **Group 6**: the two docstrings corrected — **prose only**, and each must say that the
  memory-lane 13/7 was a **different** split that coincided numerically. **⚠ A THIRD docstring —
  `breakdown_helper.py`'s `verify-grill-ran` — rode this same commit `7c0b796`; see the
  addendum.**

**Verify:**

- `grep -rn "13/7" *.md CLAUDE.md PLAN-STATUS-ARCHIVE.md README.md DEVELOPMENT-STATUS.md` — every
  remaining hit is **either a dated historical statement or sits beside a 2026-09-03
  amendment**.
- `pytest tests/lib/test_memory_lane.py -q` **green** — **MET, `28 passed`**, recorded under
  Phase 4.
- `scripts/verify-agent-reachability.py` and `scripts/verify-memory-lane.py` pass — nothing here
  touches either, so a failure means something unintended moved. **MET.** ⚠ **State the evidence
  exactly as it is: this is suite-INCLUSION, not a separate script run.** Per the repo's
  `CLAUDE.md`, **the live-`src/` tests ARE those two gates** — `tests/lib/test_memory_lane.py`
  and `tests/lib/test_agent_reachability.py`, with no CI job and no Makefile target behind them.
  The first ran **alone** (`28 passed`) and **both ran inside the full-suite run** recorded under
  Phase 4, whose **only** failure is the plan-92-attributed `tests/scripts/test_generate_agents.py:534`
  case. **Neither gate is among the failures, which is what "pass" means here.**
- **No plan vocabulary in emitted text.** "D1", "Phase 2" and this plan's number are maintainer
  vocabulary; emitted text names only the commands and the rule.

---

### Phase 4 — Install ride + suite *(RUN 2026-09-03; record below)*

Ran `scripts/generate.sh <scratch>` into a **scratch** target and asserted the emitted layout.
**This phase's Verify block demanded that the greps and the pytest lines live IN this file
rather than in a transcript — so they are recorded verbatim here.**

**Verify:**

- **Source tree.** `grep -ln disable-model-invocation src/commands/*/main.md` → **`configure`,
  `constitute`, `generate-docs`, `init-forge` ONLY**. **MET.**
- **Install ride.** `scripts/generate.sh <scratch>` → **20 commands emitted** to
  `.claude/commands/devforge/`. The flag is present in **exactly**
  `configure.md constitute.md generate-docs.md init-forge.md`, and **absent from**
  `grill.md spec-check.md fix.md`. **MET — both halves, and they are scored together**: a run
  that stripped the flag from all twenty would satisfy the second half and fail the first.
- **`tests/scripts/test_claude_emitter.py`** → `14 passed`.
- **`tests/lib/test_memory_lane.py`** → `28 passed` (Phase 3's docstring edits changed no logic).
- **`tests/lib/test_breakdown_helper.py`** → `431 passed`.
- **Full suite.** `python3 -m pytest tests/ -q` →
  `1 failed, 11565 passed, 16 skipped, 27 warnings, 227 subtests passed in 896.79s`.

**⚠ The suite is NOT green, and this is an ATTRIBUTION, not a pass.** The single failure is
`tests/scripts/test_generate_agents.py:534` —
`'model_pin' unexpectedly found in {'name': 'security-reviewer' …}`. It is **attributed to the
CONCURRENT plan-92 session**, whose uncommitted edits to `src/agents/security-reviewer.md` and to
that test file were sitting in the working tree during the run. **The basis for the attribution
is stated rather than assumed: plan 93 touched no agent file and no `generate-agents` test.**

**What that attribution does NOT establish**, said plainly so no later summary upgrades it:
**nobody re-ran the suite on a tree with plan 92's edits removed.** The attribution is an
inference from disjoint file sets, not an observation of a green suite. **A session that needs a
clean baseline must produce one** — `git stash` plan 92's edits, or re-run after plan 92 lands —
and must not cite this record as if it already had.

---

### Phase 5 — Consumer e2e *(user-driven HARD GATE, NOT run)*

**Everything above is build-verified, NOT consumer-validated.** No consumer install has run
under the flipped carve-out, and no phase above may claim otherwise.

Three known-answer anchors. **Anchors 1 and 2 are scored as a PAIR** — a model that runs the
named command by ALSO re-running the blocked one passes half and fails half.

1. On a consumer install, `/devforge:plan` **BLOCKS** on a missing `spec-check.md`; the model
   **OFFERS** `/devforge:spec-check`; the user says yes; **the model runs it itself** (no
   *"please type"*); and **does NOT re-run `/devforge:plan` on that same yes.**
2. The same at `/devforge:breakdown` with `/devforge:grill`.
3. After `/devforge:review` produces findings, the user agrees to arm (A) and **the model runs
   `/devforge:fix <feature>` itself.**

Plus, in the same session: the `/` menu **still lists** the three commands, and the four setup
commands **still answer** *"name it for the user to type."*

**Verify:**

- All three anchors scored **explicitly** — stated, not summarized. **Record the observed
  strings.**
- **If it fails**, record the negative here with the transcript and identify which layer produced
  it before proposing anything: a *"please type it"* response is a Phase-1/Phase-2 prose finding;
  a two-commands-on-one-yes response is a **D2 finding with no mechanical remedy short of
  reverting the flag**; a missing `/` menu entry is a Claude Code surface finding (fact 4's
  `user-invocable` was never set). **They have different fixes.**
- **A clean run is NOT evidence that removing the flag was safe.** It is evidence that the three
  commands became reachable and that the offer shape held for one session. **D2's bound stands:
  nothing mechanical enforces one-agreement-per-command.**

---

## Review record *(2026-09-03)*

**Recorded because two of the six findings below are the ONLY reason two shipped criteria are
met.** A plan whose review history is invisible reads as though its first draft was correct.

**instruction-reviewer, pass 1** — the nine `src/` files of Phases 1–2. **One MEDIUM finding:
catalog-entry length** (the first cut landed at roughly 520 / 525 / 650 characters against a
≤ 400 bar). **Fixed** — the second cut is what shipped at 385 / 386 / 394. **The bar was met
because the reviewer caught it, not because the first draft hit it.**

**instruction-reviewer, pass 2** — this file plus the six ledgers and the root docs. **Six
findings:**

1. **Catalog-entry length** — already fixed at read time (pass 1's finding, re-observed).
2. **`CHANGELOG.md:53` carried a stale seven-keep claim.** **Fixed** in Phase 3.
3. **Status line and Phase-4 evidence gap** — the plan asserted phases it did not record.
   **Fixed by this update** (the Status line's SHAs; Phase 4's verbatim record).
4. **Inventory gaps** — sites the build touched that no group table named. **Fixed by this
   update** (the inventory addendum).
5. **The expected grep match** — Phase 1's zero-hit criterion has one correct match.
   **Fixed by this update** (reconciled in place, dated).
6. **The word-count nit** — the shipped descriptions exceed the drafted ≈40–50 band.
   **Fixed by this update** (D3's band widened to ≈40–60, dated).

**python-reviewer** — **clean on both docstrings after one nit.** No logic, no signature and no
stderr string was touched by either.

⚠ **Findings 3–6 were open at the moment the build was called done.** They are closed by this
update and by nothing earlier, which is why the update exists.

---

## Non-goals

- **An autonomous end-to-end cycle.** Explicitly declined 2026-09-03; **D2's one-agreement rule
  is the line.** A future session that wants one owes its own plan and its own argument.
- **Any change to the setup four.** They keep the flag under D1's single criterion.
- **Any change to the gate PREDICATES** of `/devforge:plan` PHASE 0a.8 or `/devforge:breakdown`
  PHASE 0a.6 — presence + freshness, and presence + recorded adversary status. **No verdict, no
  override flag, no skip arm. Plans 82 and 85 stand untouched.**
- **Any change to `/devforge:grill`'s or `/devforge:spec-check`'s verdict ownership, their
  dispositions, their seeds or their consumers.**
- **`report-bug` Rule 8.** Byte-unchanged, and now load-bearing.
- **`user-invocable`** (fact 4). Not set anywhere by this plan.
- **`skillOverrides` / `disableBundledSkills`.** Plan 63's Path A stays rejected.
- **Any Python beyond the docstrings.** ⚠ **Dated amendment, 2026-09-03: this non-goal was
  drafted as *"beyond the TWO docstrings of Group 6"* and the build touched a THIRD** — the
  `verify-grill-ran` docstring in `src/devforge/lib/breakdown_helper.py` (inventory addendum).
  **The non-goal is widened to "docstrings" and is otherwise unchanged: still zero logic, zero
  signatures, zero behavior.** `verify-grill-ran`'s stderr is byte-unchanged, which is the
  property that mattered — plans 82 and 85 read that stderr. **The count moved; the constraint
  did not.**
- **Any new gate, validator or check number.** Plan 75's tripwire, both halves.
- **Back-porting into shipped installs.** They arrive through `install.sh` / `update.sh`.
- **Measuring the listing-eviction rate on consumers.** Facts 6–8 describe the mechanism; this
  plan measures no consumer.

---

## Dependencies + related

- **Plan 26** — D2 **amended** (its *"every forge command sets `disable-model-invocation: true`"*
  premise is falsified by this change). The proposal-only two-stage gate itself is unchanged.
- **Plan 63** — OQ-2 and OQ-3 **amended**. ⚠ **Its Path B logic — that invisibility caused the
  hijack — is the same logic this plan applies to three more commands**, so this is a
  continuation of plan 63's reasoning rather than a reversal of it.
- **Plan 82** — D5(a-ii) **amended** (its blocked message no longer names a command *"for the
  USER to type"*). **Its gate is untouched.**
- **Plan 83** — fact 12 and its *"present by construction"* claim **weakened to "present by
  agreement"**. **No mechanism changes**; the seed model, its filename convention and its
  consumers are unaffected.
- **Plan 85** — D6 **amended** (it read the 13/7 counts live and recorded no delta; this plan
  produces one). **D1–D5, D7 and D8 are untouched** — the grill gate, its predicate, its
  dispositions and its cost line all stand.
- **Plan 88** — OQ-6 **amended**. ⚠ **Its D6 counter-argument becomes live**: the command's own
  PHASE-4 pointer and the conversational rubric can now give a user two different answers in one
  session, and `report-bug` Rule 8 is the only bar left.
- **Plan 92** — concurrent, **unaffected**: `/devforge:configure` stays human-typed under D1.
- **`FINDINGS.md` finding 2** (the intake rubrics' blanket `--accept-gaps` escape) — **cited as
  an existing prose escape, not changed.** It is one of the prose-only stops this plan's
  `## What mechanically stops the model today` section enumerates.

---

## Context for next session

**Commit state.** **Phase 1 `9cc0c91`** (seven command files + `src/devforge/storage-rules.md`),
**Phase 2 `21d7211`** (`src/CLAUDE.md`), **Phase 3 `7c0b796`** (six ledgers, root docs, **three**
docstrings — `memory_lane.py`, `test_memory_lane.py` and `breakdown_helper.py`'s
`verify-grill-ran`, all three named in that commit's message alongside
`tests/lib/test_breakdown_helper.py 431 passed`).
**Phase 0's ratification record and Phase 4's install-ride + suite record ride in
the closing commit that adds THIS FILE to git** — that SHA is not written here because it cannot
be known from inside the file it commits; re-derive it with
`git log --oneline -1 -- 93-MODEL-INVOCATION-CARVE-OUT-NARROWING-PLAN.md`. **Phase 5 is NOT run
and NOT waived.**

**⚠ The full suite was NOT green on the Phase-4 run** — one failure, attributed to the concurrent
plan-92 session and never re-run on a clean tree. **Read Phase 4's record before citing the
suite**, and do not shorten *"attributed"* to *"unrelated"*.

**The one sentence that governs everything here:** after this change, `disable-model-invocation`
guards the setup chain and nothing else, so **every remaining human-first guarantee in the
feature pipeline is prose plus `AskUserQuestion`** — and D2's one-agreement rule, the load-bearing
behavioral rule of this plan, is itself prose.

**Rule for every anchor in this file: grep the quoted sentence, never the line number.**

**Trap 1 — reading plan 63's OQ-2 without its 2026-09-03 amendment.** A fresh session doing so
believes the split is 13/7, and will "restore" a flag this plan deliberately removed. The same
trap sits in plans 26, 82, 83, 85 and 88.

**Trap 2 — reading `src/CLAUDE.md:77`'s pre-change sentence.** *"This section is the only place
the model sees what they do"* was the entire justification for the long catalog entries. **A
session that reads it post-flip will believe the long entries are load-bearing** and will
restore ~7,800 chars of always-on context that the skill listing now carries for free.

**Trap 3 — treating a clean Phase 5 as proof the change is safe.** It shows three commands became
reachable and that one session's offer shape held. **It cannot show that no future session
chains two commands on one "yes"**, because nothing mechanical prevents that.

**Trap 4 — believing the six group tables are the site list.** `src/CLAUDE.md` `:51`, `:53`,
`:58` and `:60` carry *typed by the user* / *never auto-runs* / *the user invokes it* claims and
are invisible to a grep for *"seven"*; **this plan's own authoring sweep found them, and the
BUILD then found more still** — `src/CLAUDE.md:92`, `grill/main.md:17`,
`spec-check/main.md:67`, `storage-rules.md:258`, four more `README.md` lines, two more
`DEVELOPMENT-STATUS.md` lines, three more `CHANGELOG.md` lines and a third Python docstring.
**They are in the inventory addendum, and the "NOT certified exhaustive" disclaimer is literal:
two independent sweeps each missed sites the next one found.**

**Trap 7 — the "two docstrings" count.** Group 6 names two; the build touched **three**
(`breakdown_helper.py`'s `verify-grill-ran` docstring). **The `## Non-goals` entry was amended in
place rather than left contradicting the addendum.** ⚠ **The constraint that matters is not the
count** — it is that **no logic, no signature and no stderr string moved**, because plans 82 and
85 read `verify-grill-ran`'s stderr.

**Trap 5 — "harmonizing" the two `/devforge:configure` sentences.** `discover/main.md:691` and
`research/main.md:1240` say *"that command is human-typed only, so never run it yourself"* —
**still true under D1.** They look exactly like the Group-2 targets and must not be edited.

**Trap 6 — renumbering the memory-lane docstring to 16/4.** `scripts/lib/memory_lane.py:69`–`:73`
describes a **different** 13/7 (READS / N/A) that coincided numerically with the invocation
split. **The correction is prose about the coincidence, not an arithmetic update.**

**Known residual — OWED and NOT done.** `src/devforge/storage-rules.md`'s `## File Lifecycle`
block has **NO `grill` row**, although `/devforge:grill` writes three artifacts —
`grill.md`, `grill-seed.json` and `grill-state.json` — and that same block **declares the exact
analogues for `spec-check` and for `fix`**. **This gap PREDATES plan 93** and was found while
editing `:258` in Phase 1. **It is deliberately not fixed here**: adding the row is a new
artifact declaration, not a wording fix, and this plan's whole scope is wording plus three
deleted frontmatter lines. **Recorded so the next session finds it as a known omission rather
than as a fresh discovery** — and so nobody credits plan 93 with having closed it.

**Discovered while drafting, NOT owned by this plan and not fixed here:** spec and plan approval
have been **implicit** since plan 63 — the status flip rides the NEXT command's invocation
(`src/commands/plan/main.md:160`, `src/commands/breakdown/main.md:113`) and both of those
commands are model-invocable. **So the "approval" a reader imagines guarding those artifacts was
already a side effect of the model invoking the next stage, before this plan touched anything.**
Recorded, not owned.

---

## When resuming work

1. **Read this file in full, then `## Verified mechanics` again** — nine rows, each checkable in
   under a minute. **If facts 1, 2, 6, 7, 8 or 9 no longer hold, stop and re-derive**: D1 rests
   on 1–2, D3 rests on 6–8, and Phase 1's removal rests on 9.
2. **Re-verify every anchor before use. Grep the quoted string, never the `:NNN`** —
   `disable-model-invocation`, `human-typed only`, `never run it yourself`,
   `this section is the only place the model sees what they do`, `implicit approval via`,
   `13 model-invocable`.
3. **Read `src/CLAUDE.md` in full before touching it**, not just the eleven named sites. **The
   inventory is not certified exhaustive, and two independent sweeps each missed sites the next
   one found** — four by this plan's authoring sweep, more by the build (Trap 4, and the
   inventory addendum).
4. **Route every edit through the house loops:** **instruction-author → instruction-reviewer**
   for Phases 1–3 (Phase 1 additionally rests on the three `claude-code-guide` / doc-fetch passes
   recorded under `## Verified mechanics`); **python-engineer → python-reviewer** for anything in
   Python — **which this build already owed and performed on all THREE docstrings** (clean after
   one nit). ⚠ **An earlier revision of this step said the Python route "would be owed only if
   Group 6 grew past two docstrings, which it must not." It did grow, the route WAS taken, and
   the sentence is corrected rather than deleted.**
5. **Do not let Phase 5's convenience turn D2's one-agreement rule into a chain.** The rule is
   the whole reason D1 was ratifiable: the maintainer asked to stop typing three commands, **not**
   for an autonomous cycle. **D1's rejected alternative (c) is the named re-open shape** if that
   ever changes — and it costs a keystroke, which is exactly why it was declined here.
6. **Do not re-add the flag to fix a symptom.** If a consumer session misbehaves, the finding is
   a prose finding in Phases 1–2 or a D2 finding; **re-flagging is a D1 re-open, and it owes the
   context arithmetic in `## Measured facts` a rebuttal**, not just a preference.
7. **Two things are open and both are named above, not hidden here.** (a) **The suite has no
   clean baseline** — Phase 4's one failure is attributed to plan 92 and was never re-run without
   plan 92's working-tree edits; produce that baseline before citing the suite as green. (b) **The
   `storage-rules.md` `## File Lifecycle` `grill` row is OWED and predates this plan**; it is a
   new artifact declaration, so it needs its own change, and plan 93 must not be credited with
   closing it.
