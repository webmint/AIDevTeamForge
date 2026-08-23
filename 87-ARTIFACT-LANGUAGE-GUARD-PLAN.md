# 87 — Artifact language guard: every byte written to a file stays English

**Status:** ✅ DONE (build) 2026-08-23 — **Phases 0–3 complete.** Phase 0 RATIFIED 2026-08-23 (by the maintainer, in-session — D1–D5 all decided, no item left open); Phase 1 (`src/CLAUDE.md` item 15 + the `README.md` note) and Phase 2 (the advisory Cyrillic detector + its tests) were built and committed the same day; Phase 3 (sweep + records) is this pass. **Phase 4 consumer observation is DEFERRED — a user-driven HARD GATE that has NOT run. Build-verified, NOT consumer-validated.**
**Branch:** `develop-2.0-init`
**Created:** 2026-08-23.

This plan document contains no private-client identifiers and is intended to be
**committed normally**, unlike the deliberately-untracked plans 73/74/75.

## Evidence constraint

The two UNTRACKED private-client evidence files at repo root
(`81-EVIDENCE-V2-BENCHMARK-RUN.md`, `77-EVIDENCE-DISCOVERY-TO-LOCK-INVERSION.md`) are
neither read nor cited by this plan, and no phase may import from them.

**This plan needs neither.** Its motivation is a configuration change the maintainer made on
this machine on 2026-08-23 plus the consequence that follows from it mechanically. **There is
no incident, no failing run, and no observed leak** — and the plan is written so a reader can
see that plainly rather than inferring an evidentiary base that does not exist. **D1's
strengthening trigger is the first OBSERVED leak**, and until one exists nothing in this plan
may be described as having caught anything.

---

## Origin — the maintainer enabled Claude Code's `language` setting

The maintainer reads English as a second language and, on **2026-08-23**, set the Claude Code
user-level `language` key in `~/.claude/settings.json` to `uk`, so terminal prose renders in
Ukrainian. That is a legitimate, documented use of an official settings key (fact 1) and this
plan does not propose reversing it or discouraging it.

**The consequence is mechanical, and it is the whole problem.** The `language` key is an
INSTRUCTION TO THE MODEL, not a filter over anything the model writes. Nothing in Claude Code
partitions "prose the user reads in the terminal" from "prose the model writes into a file."
So every prose artifact this framework produces — `spec.md`, `plan.md`, task files,
`research-report.md`, `grill.md`, code comments, and commit messages — sits in the blast
radius, at a nonzero and unquantified rate.

**Why an English-only file corpus is worth defending at all**, stated once so no phase has to
re-derive it:

- The corpus is a MACHINE INPUT before it is a human one. Every downstream command re-reads
  these artifacts, and the whole framework's prompts, agent personas, checklists and rule
  names are English.
- Mechanical checks match English tokens. `verify-dead-code-coverage` matches anchor tokens
  verbatim; `/devforge:verify`'s rubric selects a memory bucket by matching `## What Failed` /
  `## What Worked` / `## Known Pitfalls`; the constitution splitter recognises bold English
  headers.
- Commits and specs outlive the session that produced them and are read by people who did not
  set the key.

**⚠ Nothing above is evidence that a leak has occurred.** It is the argument for why the
exposure is worth a cheap guard, and D1's severity choice is calibrated to exactly that: an
argued exposure, not a measured one.

---

## What is actually being added

Two things, and they are separable — Phase 0 ratified both, but a future session must not
read either as depending on the other:

1. **An instruction guard** (Phase 1) — one new `src/CLAUDE.md` Key Rule that ships into every
   consumer install, plus a README note telling a non-English operator where to put the key.
   **Instruction-only, zero Python.** This is the layer that actually shapes what the model
   writes.
2. **An advisory detector** (Phase 2) — a Cyrillic scan inside
   `artifact_helper commit-artifacts` that WARNS on stderr and changes nothing else. **This is
   a tripwire, not a control.** It cannot prevent a leak; it can only make one visible at the
   moment it is committed.

**(1) without (2) is the guard with no observation.** **(2) without (1) is a warning about a
rule nobody was told.** Both shipped together is the ratified shape.

**⚠ The detector covers ONE commit path, not all of them.** `artifact_helper commit-artifacts`
is the chokepoint every pipeline command's artifact WIP-commit rides (plan 37), but
`implement_helper wip-commit` is a SECOND, independent commit path (fact 21) and this plan does
not touch it. **So "every byte written to a file" is this plan's GOAL, stated in its title;
the detector's actual coverage is narrower and is named in `## Non-goals`.** A future session
must not read the title as a description of what Phase 2 built.

---

## Verified mechanics (2026-08-23)

Every row was confirmed by opening the named file or by the named fetch. **The quoted token is
the anchor; the digit is a dated hint** — this repo has documented anchor rot, so grep the
string, never the `:NNN`.

| # | Fact | Evidence |
|---|------|----------|
| 1 | **`language` is an official Claude Code settings key**, described as *"Have Claude respond in a language other than English"*, filed under topic *"Model and responses"*, with scope *"Any file"* | `https://code.claude.com/docs/en/settings-reference`, fetched 2026-08-23 |
| 2 | Settings precedence, highest first: **Managed** (`managed-settings.json`, MDM, or the claude.ai console) → **Command line** (`claude --settings`) → **Project local** (`.claude/settings.local.json`) → **Shared project** (`.claude/settings.json`) → **User** (`~/.claude/settings.json`) | `https://code.claude.com/docs/en/settings`, fetched 2026-08-23 |
| 3 | `.claude/settings.local.json` reaches *"You, in this one project only. Claude Code keeps it out of git when it creates the file; if you create it by hand, add it to `.gitignore` yourself"* — **so it is git-excluded only when Claude Code itself created it** | same page |
| 4 | `~/.claude/settings.json` reaches *"You, in every project on this machine"*, and its stated purpose is *"Personal preferences"*. `.claude/settings.json` reaches *"Everyone who starts Claude Code in the folder that contains it"* | same page |
| 5 | **NO `language` settings key exists anywhere in this repo.** A repo-wide grep for `"language"` returns only unrelated hits — the `--sample-files-json` shape in `/devforge:constitute`, two done-plan shape docs, and a `"language"` dict key in the `_audit` / `_summarize` / `_review` preflight parsers | repo-wide grep, 2026-08-23 |
| 6 | **`.claude/settings.local.json` appears exactly ONCE in this repo**, at `src/manifest.json:40`, inside the `projectOwned.patterns` list described as *"Files generated/customized per-project — NEVER overwrite"* | `src/manifest.json:33`–`:48` |
| 7 | **No shell script writes `.claude/settings.local.json`** — a repo-wide `*.sh` grep for it returns **zero** hits. The only two `settings.json` hits are `install.sh:438` (a comment) and `install.sh:442` (the copy) | repo-wide `*.sh` grep, 2026-08-23 |
| 8 | **`install.sh` UNCONDITIONALLY overwrites `.claude/settings.json`** — `cp "$TEMPLATE_DIR/src/settings.template.json" "$TARGET_DIR/.claude/settings.json"` — while `update.sh` reads `projectOwned.patterns[]` from the manifest and skips them. **So the shared-project file is the WRONG carrier for a personal key on an install ride, and the two carriers D5 names are touched by neither script** (fact 7) | `install.sh:442`; `update.sh:418` |
| 9 | **`install.sh` reads `manifest.json` for `version` ONLY** (`:466`) and never consults `projectOwned` — that list is an `update.sh`-only contract, which is why fact 8's asymmetry exists | `install.sh:466`, `:471`; grep for `projectOwned` in `install.sh` returns zero hits |
| 10 | `_cmd_commit_artifacts` spans `_cli.py:197`–`:311`. **The commit message is CONSTRUCTED there** — `message = "[WIP] {0}".format(label)` — and `[WIP] ` is pure ASCII, so **scanning `label` scans the entire commit message** | `src/devforge/lib/_artifact/_cli.py:250` |
| 11 | **The in-function stderr-warning precedent already exists**: `sys.stderr.write("commit-artifacts: warning: {0}\n".format(err))`, emitted once per partially-failed staging path while the run continues to a successful commit and exit 0 | `src/devforge/lib/_artifact/_cli.py:285`–`:287` |
| 12 | **The verb has exactly TWO stdout JSON shapes**: `{"committed": false, "skipped": "nothing to commit"}` and `{"committed": true, "head_sha": ..., "message": ...}` | `src/devforge/lib/_artifact/_cli.py:276`–`:280`, `:305`–`:310` |
| 13 | **`stage_errors` is a load-bearing exit-1 channel** — non-empty AND nothing staged returns `EXIT_ERR`. **A new warning appended to that list would turn an advisory into a failure** | `src/devforge/lib/_artifact/_cli.py:272`–`:275` |
| 14 | **The happy-path test asserts the exact stdout object** — `committed` true, `message` equal to `"[WIP] spec: 001-foo"`, `head_sha` matching `^[0-9a-f]{40}$` — so any stdout addition breaks it | `tests/lib/_artifact/test_commit_artifacts.py:173`–`:213` (`TestCommitArtifactsStandaloneHappyPath.test_stages_named_files_and_commits`) |
| 15 | **`--paths` may name a DIRECTORY**, whose whole subtree is staged. **So the detector cannot enumerate files from `--paths`; it must ask git what actually got staged** | `tests/lib/_artifact/test_commit_artifacts.py:404`–`:442` (`TestCommitArtifactsDirectoryPath.test_directory_path_stages_all_files_under_it`) |
| 16 | `_GIT_TIMEOUT = 30`, and all four `_git_*` primitives bound their subprocess with it; the module docstring states the rule: *"Bound every git call with _GIT_TIMEOUT (30 s)."* | `src/devforge/lib/_artifact/_cli.py:86`, `:31`, `:117`, `:139`, `:161`, `:183` |
| 17 | **`src/CLAUDE.md`'s `### Always` list ends at item 14** (`14. **Crash recovery** — …`), followed by a blank line and the `### Never` heading. Every item's shape is `N. **Bold lead** — sentence` | `src/CLAUDE.md:216`, `:218` |
| 18 | **Plan 34's ADVISORY precedent, in the code**: *"hygiene_flags (scope_creep / leftover_artifacts) are ADVISORY and are intentionally NOT in the blocker list above. They appear in reasons for visibility; they never cause NEEDS WORK on an otherwise-clean feature."* | `src/devforge/lib/_verify/_verdict.py:112`–`:114` |
| 19 | **Plan 44's WARN-only fail-soft precedent**: the drift check is headed *"WARN-ONLY"* and its checks are *"both advisory + fail-soft (D5): any unexpected error prints a"* note rather than failing | `scripts/constitution-drift-check.sh:5`, `:12` |
| 20 | **The known legitimate false-positive class is already ratified elsewhere**: plan 83's `fix-seed.json` carries the provenance literal `conversational (in-window user report; no report file)`, whose `invalidating_evidence` may quote a user's own words | repo-root `CLAUDE.md`'s plan-83 index line; `CHANGELOG.md:12` |
| 21 | **A SECOND commit path exists and this plan does not cover it** — `implement_helper wip-commit`, registered in the `_implement` CLI, is what writes the `[WIP] fix:` and per-task commits | `src/devforge/lib/_implement/_cli.py:138` |
| 22 | The README `## Install` section's line-32 paragraph is the one describing what `install.sh` copies and closing *"Then open the project in Claude Code and run the one-time setup chain."* | `README.md:26`–`:32` |
| 23 | **`CHANGELOG.md` carries a `## [Unreleased]` section today**, holding `### Changed` and `### Fixed` and **no `### Added`**. The released `## [2.0.9]` section below it opens with `### Added`, so Keep-a-Changelog ordering (Added before Changed) has an in-file precedent | `CHANGELOG.md:8`, `:10`, `:16`, `:20`, `:22` |
| 24 | Repo-root `CLAUDE.md`'s active-plans index ends with the plan-86 one-liner, followed by a blank line and the five-FINDINGS paragraph — **so a plan-87 one-liner is a pure append with nothing to renumber** | `CLAUDE.md:79`, `:80`, `:81` |
| 25 | **NOTHING in this repo counts the `### Always` items, so the item-15 append breaks no assertion.** The only citations INTO that list are two `Key Rules #4` references in an already-shipped plan document, and item 4 (`**Memory is persistent**`) is unmoved by an append. ⚠ **One near-miss a careless sweep will hit and must NOT edit**: an ABORTED, archived plan's measurement table carries a `Key Rules (Always/Never one-liners) \| 317` WORD count — a dated historical measurement, not a live assertion | repo-wide grep 2026-08-23; `22-VERIFY-COMMAND-REDESIGN-PLAN.md:51`, `:393`; `done-plans/06-CONDITIONAL-CONTEXT-PLAN.md:80` |

### Claude Code authoring surface, verified against current docs

Fetched 2026-08-23 from `https://code.claude.com/docs/en/settings-reference` and
`https://code.claude.com/docs/en/settings`. **Cited here so a future author can re-verify
rather than trusting this file** (facts 1–4). Three things those pages establish and one thing
they do NOT:

- The key is `language`, its documented effect is *"Have Claude respond in a language other
  than English"*, and its scope is **"Any file"** — it is valid in every settings tier,
  including the two personal ones.
- Two personal carriers exist and neither is shared: `~/.claude/settings.json` (*"You, in
  every project on this machine"*) and `.claude/settings.local.json` (*"You, in this one
  project only"*). **Two developers sharing this repo therefore never conflict over the key**,
  which is what makes D5's advice safe to publish.
- `.claude/settings.local.json` is kept out of git **by Claude Code, and only when Claude Code
  created it** — *"if you create it by hand, add it to `.gitignore` yourself"* (fact 3). **The
  README note must not flatten this into "it's gitignored."**
- **The docs say NOTHING about the key's effect on file writes.** They describe it as
  something Claude *responds* in. **The absence of a documented file-write guarantee is the
  entire premise of this plan, and it is an absence, not a documented negative** — a future
  version of Claude Code could scope the key to conversation explicitly, at which point D1's
  detector becomes redundant rather than wrong. Re-read these pages before extending anything
  here.

---

## Decisions — ratified 2026-08-23

Each carries the recommendation, the argument against it, and the ratification. **Phase 0 is
closed; nothing below is open.** The counter-arguments are retained deliberately — they are
what a future session needs in order to re-open a decision honestly rather than by drift.

### D1 — ADVISORY WARN, never a block *(RATIFIED 2026-08-23)*

**The rule.** The detector writes one or more warning lines to stderr and **changes nothing
else**: not the exit code, not either stdout JSON shape (fact 12), not whether the commit
happens.

**Two precedents in this repo, both load-bearing rather than decorative.** Plan 34's hygiene
scans were demoted to ADVISORY and are *"intentionally NOT in the blocker list"* (fact 18),
and plan 44's drift check is WARN-ONLY and fail-soft by design (fact 19). **This plan is the
third member of that family, not a new stance.**

**Why not fail-closed, and this is the argument that decides it.** **A known legitimate
non-English content class already exists in the ratified design** (fact 20): plan 83's
`fix-seed.json` records a `conversational (in-window user report; no report file)` provenance
whose `invalidating_evidence` may quote a Ukrainian-speaking user verbatim, and
`/devforge:grill` findings may likewise quote a user's own statement. **A hard fail would
block legitimate, correctly-authored content on day one, and the only repair would be a
carve-out — which this repo's zero-escape-hatch meta-rule forbids by name.** An advisory
warning has no such problem: a false positive costs one line of stderr and nothing else.

**Strengthening trigger, recorded explicitly so it is not re-argued from feel.** The FIRST
CONFIRMED LEAK re-opens severity: an artifact carrying non-English prose that reached a commit
either despite the warning firing, or with the warning never firing at all. **Until such an
observation exists, fail-closed is NOT built and this plan may not be cited as evidence that
the warning works** — an unfired warning on a corpus with no leak in it demonstrates nothing.

*Counter-argument, recorded:* a warning that nothing reads is theatre, and this one prints into
a stderr stream an orchestrator may summarize away. **Accepted, and it is the honest bound:
Phase 1's instruction rule is the mechanism that actually shapes behavior; Phase 2 is a
tripwire whose only claim is visibility at the commit moment.** A ratifier who wanted
enforcement would have had to accept the carve-out this decision refuses.

### D2 — Cyrillic-only detection, stdlib `re` *(RATIFIED 2026-08-23)*

**The rule.** One regex over the Cyrillic Unicode range **U+0400–U+052F** — Cyrillic (Basic)
plus Cyrillic Supplement — using the stdlib `re` module and nothing else. Plan 62's D10
stdlib-clean stance holds: this plan adds no dependency and `install.sh` is untouched.

**Why the range is right for the observed case, and where it stops.** Every letter modern
Ukrainian needs beyond the shared Cyrillic set — **і (U+0456), ї (U+0457), є (U+0454), ґ
(U+0491)** — is inside U+0400–U+04FF, and the Supplement block (U+0500–U+052F) rides along for
free. **The historic Cyrillic Extended blocks are deliberately OUT** (Extended-A U+2DE0–U+2DFF,
Extended-B U+A640–U+A69F, Extended-C U+1C80–U+1C8F): they carry no modern Ukrainian letter,
and including them would widen the surface for no gain.

**Why NOT general non-Latin detection.** "Any script that is not Latin" is not expressible
cleanly in stdlib `re` — Python's `re` has no `\p{Script=...}` support — so a general detector
means either a hand-maintained range table or a third-party Unicode dependency. **The observed
operator language is Ukrainian and nothing else is observed.** Extending to a second script is
RECORDED as a possibility and is NOT built; the extension shape is one more range in the same
character class, which is why deferring it costs nothing.

*Counter-argument, recorded:* a Cyrillic-only detector is silent for an operator who sets
`language` to Greek, Japanese, Arabic or Hindi, and this framework has more than one user. **So
the detector's coverage is narrower than Phase 1's rule, permanently and by construction.**
That asymmetry is accepted rather than smoothed: the rule is universal, the tripwire is
scoped to the one script anybody has actually configured, and the day a second script is
configured is the day the range list grows.

### D3 — Output channel: stderr plain lines, matching the in-function precedent *(RATIFIED 2026-08-23)*

**The rule.** Warnings are plain stderr lines in the exact shape the function already uses one
branch away (fact 11): `commit-artifacts: warning: <text>`. **No new output channel, no new
prefix vocabulary.**

**Why NOT a stdout-JSON key**, and this is forced rather than preferred. Two independent
reasons, either of which decides it:

1. **The happy-path test asserts the exact stdout object** (fact 14). A new key is a test edit
   in a test whose whole job is to pin that object.
2. **The two stdout shapes ARE the machine contract** (fact 12). Every caller in the pipeline
   reads `committed` / `head_sha` / `skipped`; adding an advisory field to a machine contract
   invites a future caller to gate on it, which is precisely the fail-closed behavior D1
   refuses.

**⚠ The detector must NOT reuse `stage_errors`** (fact 13). That list is an exit-1 channel: a
non-empty `stage_errors` with nothing staged returns `EXIT_ERR`. **Appending a language
warning to it would convert an advisory into a failure silently**, which is the single most
likely implementation defect in Phase 2 and is why the fact is recorded here rather than left
to be discovered.

*Counter-argument, recorded:* a stderr-only signal is invisible to any programmatic consumer,
so nothing downstream can ever count leaks or trend them. **Accepted** — D1 already establishes
that this is a tripwire for a human reading a turn's output, and a countable signal is what a
future strengthening would add, on the evidence D1's trigger demands.

### D4 — Guard sentence lands at `src/CLAUDE.md` `## Key Rules` → `### Always`, as item 15 *(RATIFIED 2026-08-23)*

**The rule.** One new numbered item appended to `### Always`. The list ends at item 14 and is
immediately followed by `### Never` (fact 17), so **this is a pure append with nothing to
renumber** — the same append-never-renumber discipline plans 05/10/86 established for
`code-reviewer`'s checks.

**The ratified wording** (Phase 1 may polish the prose, never the shape — a numbered
bold-lead-em-dash line carrying **one or more sentences** after the dash, matching all fourteen
siblings). **The two-sentence form below FOLLOWS the list rather than departing from it**:
items 13 (`**Session state**`) and 14 (`**Crash recovery**`) each already carry a second
clarifying sentence, and items 1–12 carry one sentence with no terminal period. **A
"one sentence only" constraint would be false against both the siblings and the wording it
introduces**:

> 15. **English in files** — all file content and commit messages stay in English (specs,
>     plans, code, comments, docs), regardless of any operator response-language setting; a
>     non-English response language applies to conversation only. Verbatim quotes of
>     user-reported words may keep their original language.

**Three properties of that wording are deliberate and Phase 1 must preserve all three:**

1. **It names no settings key.** `src/CLAUDE.md` is consumer-facing and outlives any
   particular Claude Code surface; hard-coding `language` there would rot the moment that key
   is renamed. *"any operator response-language setting"* is durable and needs no doc fetch to
   remain true.
2. **It names the artifact classes explicitly** — specs, plans, code, comments, docs — because
   a rule stating only "files" invites the reading that a code comment is not a file.
3. **The final clause exists to make the rule and the detector tell the SAME story.** It names
   plan 83's ratified content class (fact 20). Without it, the rule would forbid exactly what
   the framework's own design requires an artifact to carry, and the WARN would be firing on
   compliant content with the rule saying otherwise.

**Why not `## Artifact Storage`.** That section's bullets scope **where files live** — feature
dir naming, task file naming, wrapper-mode paths — not what they contain, and it says nothing
about code comments or commit messages, which are two of the classes most at risk. A rule
about content in a section about location would be found by nobody looking for it.

*Counter-argument, recorded, and it is the strongest one in this file:* **any carve-out
written into an absolute rule is a crack**, and this repo's zero-escape-hatch policy exists
because cracks get widened — an LLM that reads *"verbatim quotes … may keep their original
language"* can reclassify a paragraph of its own prose as quoting the user. **The defence is
that the clause's condition is OBJECTIVE rather than a judgment call**: the text is a
quotation, attributed and delimited, or it is not — unlike "when reasonable" or "unless
trivial", which have no external referent. **The clause is also narrow by construction**: its
subject is *quotes of user-reported words*, and its permission is *keep their original
language*, not *be non-English*. **Phase 1 must keep both narrowings load-bearing**; a version
reading "quotes may be non-English" is the crack the counter-argument predicts.

### D5 — Docs note lands in `README.md` `## Install`, after the line-32 paragraph *(RATIFIED 2026-08-23)*

**The rule.** One short paragraph immediately after the paragraph describing what `install.sh`
copies (fact 22), telling a non-English operator to set the `language` key in **their own**
`~/.claude/settings.json` (all projects on this machine) or in `.claude/settings.local.json`
(this project only), and stating that the framework's guard keeps file artifacts English
either way.

**Why those two carriers and not the third.** Facts 2–4 and 8 together decide it: the two
named files are personal and unshared, so a team never conflicts over the key — **and
`install.sh:442` unconditionally overwrites `.claude/settings.json`, so a key placed there is
destroyed on the next install ride.** Naming the shared file would be advice that silently
stops working.

**Phase 1 must carry fact 3's nuance, not flatten it.** `.claude/settings.local.json` is kept
out of git *"when [Claude Code] creates the file"*; a hand-created one must be gitignored by
the operator. **A README sentence claiming the file is gitignored is false for exactly the
operator most likely to be reading it** — someone creating it by hand because they just read
this paragraph.

**Why NOT an extra `echo` in `install.sh`'s closing message.** The alternative — a line after
`install.sh:476`'s CBM-sync notice, inside the Next-steps block — was considered and
**REJECTED for this plan**: `install.sh` was recently touched by plan 72's repair-guard work,
and a docs-only phase that stays zero-script has a trivially reviewable diff. **Recorded as the
named fallback**: if the README note proves unseen (an operator on a Ukrainian-configured
machine whose artifacts drift while the README sits unread), the closing-message `echo` is the
next cut, and it needs no new argument — only this sentence.

*Counter-argument, recorded:* a README paragraph is read once at install time and never again,
while the setting is typically enabled later, so the note lands months before the moment it is
needed. **Accepted.** The defence is placement rather than repetition: the note sits in the
one section an operator re-reads when re-installing or onboarding a second machine, and
Phase 2's warning is what covers the case where the note was never read at all. **The two
layers are complementary, and neither is claimed to be sufficient alone.**

---

## Phases

### Phase 0 — Ratification *(CLOSED 2026-08-23)*

**All five decisions were ratified in-session by the maintainer on 2026-08-23**, as recorded
under each heading above: D1 advisory-WARN with the first-confirmed-leak strengthening
trigger, D2 Cyrillic-only over U+0400–U+052F with stdlib `re`, D3 stderr lines in the existing
`commit-artifacts: warning:` shape with no stdout-JSON key, D4 the `### Always` item-15 append
with its three deliberate wording properties, D5 the README `## Install` note naming the two
personal carriers.

**No open questions were left.** Three items that a reader might expect to be open are settled
by facts rather than by decision and are recorded as facts, not as forks: the detector cannot
enumerate from `--paths` (fact 15), it must not reuse `stage_errors` (fact 13), and scanning
`label` scans the whole commit message (fact 10).

**Verify:**

- `grep -n "^### D[1-5] " 87-ARTIFACT-LANGUAGE-GUARD-PLAN.md` returns five lines and **every
  one carries `*(RATIFIED 2026-08-23)*`** — no `(OPEN` marker anywhere in this file.
- The status line at the top names the ratification date and states that Phases 1–3 are
  cleared.
- **D1's strengthening trigger is recorded as a named observation**, not as a threshold or a
  rate — a ratification that reads "we will fail closed if this gets bad" has invented a dial
  this plan does not have.
- **Each decision still carries its counter-argument.** A ratified decision with its
  counter-argument deleted cannot be re-opened honestly.

---

### Phase 1 — The instruction guard *(zero Python)*

**Route: instruction-author → instruction-reviewer + claude-code-guide, for BOTH files.**
`src/CLAUDE.md` ships into a consumer project as its root `CLAUDE.md`, and **`README.md`'s D5
paragraph DESCRIBES Claude Code integration** — a settings key, its carriers, and its
git-exclusion behavior — which is exactly the class root `CLAUDE.md`'s meta-rule routes through
claude-code-guide. **Documentation about the integration surface is integration surface**; a
route that checked only the shipping file would leave the paragraph making the more specific
external claims unchecked. **The fetched-doc citations belong in the phase record** (facts 1–4).

**⚠ That verification pass was PERFORMED this session — 2026-08-23, live fetches of
`https://code.claude.com/docs/en/settings-reference` and `https://code.claude.com/docs/en/settings`,
independently re-fetched by the reviewer.** Its results are facts 1–4 and the
`### Claude Code authoring surface` section. **Phase 1 quotes VERBATIM every fact that is lossy
under paraphrase, and paraphrases the rest** — a paraphrase of a verified external quote is an
unverified claim wearing a verified claim's authority wherever that quote carries a conditional
or a nuance.

**⚠ As shipped 2026-08-23, that rule resolved to exactly ONE verbatim quote, and the split is a
decision rather than a drift.** **Fact 3 is quoted word-for-word** — *"keeps it out of git when
it creates the file; if you create it by hand, add it to `.gitignore` yourself"* — because its
entire content IS a conditional, and every paraphrase of it collapses to "it's gitignored,"
which is false for exactly the operator most likely to be reading the sentence. **Facts 1 and 4
are paraphrased**: *"can have Claude reply in another language"* for fact 1's *"Have Claude
respond in a language other than English"*, and *"every project on your machine"* for fact 4's
*"You, in every project on this machine"*. Each is a single low-nuance scope statement with no
conditional to lose, so a paraphrase costs nothing checkable. **Quoting all four would have
pushed the paragraph past the register of the section it sits in** — three sentences of terse
prose with backticked paths — which is the competing constraint D5 already imposes on this
same text. **The rule is quote-what-is-lossy, never quote-everything.**

Scope, two files:

- **`src/CLAUDE.md`** — the `### Always` item 15 of D4, appended after item 14 and before the
  blank line preceding `### Never` (fact 17). **Shape must match the fourteen siblings**:
  `15. **Bold lead** — <one or more sentences>`. Bold lead: `English in files`. **Items 13 and
  14 are two sentences each**, so D4's two-sentence wording is the list's own form.
- **`README.md`** — the D5 paragraph, placed after the `## Install` section's line-32
  paragraph (fact 22) and before the `## Flow` heading's preceding `update.sh` block. **One
  short paragraph, matching the section's existing register** (terse, backticked paths,
  no bullet list).

**Verify:**

- Instruction-reviewer clean; claude-code-guide clean, with the fetched URLs recorded.
- **`grep -n "^1[0-5]\. \*\*" src/CLAUDE.md` returns items 10–15 with item 14 still
  `**Crash recovery**` and item 15 the new rule** — nothing renumbered. Capture the pre-change
  output first.
- **`grep -n "^### Never" src/CLAUDE.md` returns exactly one line and the six `### Never`
  items are byte-unchanged.** This phase appends to one list and touches no other.
- **Fact 25 is RE-VERIFIED rather than assumed**: a repo-wide grep confirms no file counts the
  `### Always` items and the only citations into that list are by item NUMBER (`Key Rules #4`),
  which an append leaves true. **Report the result inline.** A hit that asserts a count is
  falsified by this phase and is part of THIS change, not the next audit's finding — and the
  archived word-count table fact 25 names is **not** such a hit.
- **The item-15 sentence names no settings key** (D4 property 1) — `grep -n "language" src/CLAUDE.md`
  returns no line naming a Claude Code settings key.
- **The final clause reads "keep their original language", not "be non-English"** (D4's
  counter-argument). Instruction-reviewer confirms the clause cannot be read as licensing
  non-English authored prose.
- **The README paragraph does NOT claim `.claude/settings.local.json` is gitignored
  unconditionally** (fact 3) — it states Claude Code excludes it when Claude Code creates it,
  and that a hand-created file needs the operator's own `.gitignore` entry.
- **The README paragraph does not name `.claude/settings.json` as an option** (fact 8) —
  `install.sh` overwrites it.
- `git status` shows **zero** files modified under `src/devforge/lib/` — this phase is
  instruction-only. **⚠ Dated note, 2026-08-23: Phases 1 and 2 were built IN PARALLEL, so this
  criterion is satisfied at the COMMIT level, not against the working tree.** Phase 1's commit
  contains only `src/CLAUDE.md` + `README.md`; Phase 2's contains only
  `src/devforge/lib/_artifact/_cli.py` + `tests/lib/_artifact/test_commit_artifacts.py`. **The
  phase-isolation reading applies to each phase's committed diff** — a mid-build shared tree
  carrying both phases falsifies the literal `git status` reading without falsifying the
  isolation the criterion exists to enforce.

---

### Phase 2 — The advisory Cyrillic detector in `artifact_helper commit-artifacts`

**Route: python-engineer → python-reviewer, test-first.** No `.claude/`-shipping file changes
here, so no claude-code-guide pass is owed by this phase.

**Implementation home: `src/devforge/lib/_artifact/_cli.py`, inside `_cmd_commit_artifacts`
(fact 10).** The package is deliberately two files (`__init__.py` + `_cli.py`), and unlike
plan 83's `_fix/_seed.py` this scan **owns no artifact shape** — it produces no file and
validates no schema — so a third module would add a file for a predicate. **RECOMMENDATION:
module-private functions in `_cli.py`**, with a pure `str -> bool` predicate separated from the
enumerate-and-read scan so the predicate gets its own direct unit test. **A new module is the
recorded alternative if the scan grows past the range check.**

**Hook point, and the ordering is forced rather than preferred.** After staging succeeds and
`_git_has_staged_changes` returns true (`_cli.py:266`), and **before** `_git_commit`
(`:290`) — i.e. between the staged-changes check and the commit. Two reasons: the warning must
describe what is about to be committed rather than what already was, and it must land in the
same output block a human reads for that turn.

Scope:

- **Enumerate the staged set from git, never from `--paths`** (fact 15): `git diff --cached
  --name-only -z` run in `commit_repo`, bounded by `_GIT_TIMEOUT` in the same shape as the four
  existing `_git_*` primitives (fact 16). `-z` gives NUL-separated, unquoted, repo-relative
  paths.
- **Read each staged file's worktree bytes and decode UTF-8 with `errors="replace"`**, then
  scan with the D2 range class. **A staged DELETION has no worktree file — skip it; that is a
  fact, not a fork.**
- **Scan `label` too** — which covers the whole commit message, since `[WIP] ` is ASCII
  (fact 10).
- **One stderr line per offending staged file:**
  `commit-artifacts: warning: non-English (Cyrillic) text in <relpath> — artifacts must be English (advisory, commit proceeds)`
  and one analogous line naming the commit label when the label is what matched. **Both open
  with the exact `commit-artifacts: warning: ` prefix the function already emits** (fact 11,
  D3).
- **Fail-soft wrapper: the ENTIRE detector body in one try/except.** On any exception, emit a
  single `commit-artifacts: warning: language check skipped: <err>` and continue (plan 44's
  fail-soft pattern, fact 19). **The detector must be structurally incapable of changing the
  exit code**: the call site inside `_cmd_commit_artifacts` is a bare statement whose value is
  discarded, no branch of the detector returns from the caller, and the exception handler
  catches broadly on purpose.
- **Exit codes and both stdout JSON shapes UNCHANGED** (facts 12, 14; D3).
- **⚠ Do NOT append to `stage_errors`** (fact 13) — that is the exit-1 channel.

**Three build-shaping notes, recorded so Phase 2 does not discover them late. None is an open
decision; each names a fork with a recommendation the build may diverge from by saying so.**

1. **Worktree read vs index read.** Reading the worktree can in principle diverge from the
   staged blob; `git show :<path>` reads the index exactly but costs one subprocess per file.
   **RECOMMENDATION: worktree read** — `commit-artifacts` stages and commits inside one call,
   so the divergence window is microseconds wide and requires an external writer racing the
   helper.
2. **Binary and large files.** `errors="replace"` turns invalid bytes into U+FFFD, never into
   Cyrillic, so a binary blob cannot false-positive through decoding damage — but a valid
   UTF-8 Cyrillic sequence embedded in a binary artifact would match. **Under D1 that costs one
   stderr line and nothing else.** No size cap is proposed for v1; a cap is the fork, and the
   fail-soft wrapper absorbs an `OSError` on an unreadable file either way.
3. **The scan runs once per `commit-artifacts` call** over a staged set that is, in this
   pipeline, feature-directory markdown and JSON. **No wall-clock number exists for it and none
   is claimed** — if the cost is ever surprising, measure it rather than assuming this note
   predicted it.

**Tests — written and RUN in the same turn as the code** (repo discipline: every function gets
its own test that runs). Extend `tests/lib/_artifact/test_commit_artifacts.py`:

1. **Cyrillic in a staged file** → commit succeeds, exit 0, stdout JSON byte-identical to the
   ASCII case, and stderr contains the warning **naming that file**.
2. **Pure-ASCII run** → **no language warning on stderr at all**. This is the false-positive
   floor and it is scored with (1), never alone.
3. **Cyrillic in `--label`** → warning fires and the commit still proceeds; the committed
   message is unchanged.
4. **Detector exception** (e.g. monkeypatched enumeration failure) → exactly ONE
   `language check skipped` warning, and the commit still succeeds with exit 0.

Plus a direct unit test of the pure predicate: at minimum an ASCII string, a string containing
`і`/`ї`/`є`/`ґ`, and a string in the Supplement block.

**Verify:**

- python-reviewer clean; `python3 -m unittest` over `tests/lib/_artifact/` green.
- **`TestCommitArtifactsStandaloneHappyPath` passes BYTE-UNCHANGED** (fact 14). **A failure
  there means the stdout contract moved** — which D3 forbids — not that the test is stale.
- **Every pre-existing test in the file passes unchanged.** This phase adds tests; it edits
  none.
- **`grep -n "stage_errors" src/devforge/lib/_artifact/_cli.py` returns the same lines as
  before the change** (fact 13). Capture the pre-change output first. This is the single most
  important mechanical check in the phase.
- **The detector's call site in `_cmd_commit_artifacts` is a bare statement** — python-reviewer
  confirms no `return`, `raise` or `sys.exit` inside the detector can reach the caller, and
  that the caller does not branch on the detector's value. **A detector wired into an `if` is
  the fail-closed defect D1 refuses, arriving by wiring rather than by decision.**
- **Every new git call is bounded by `_GIT_TIMEOUT`** (fact 16) — `grep -n "timeout=" src/devforge/lib/_artifact/_cli.py`
  returns one more line than before and it names `_GIT_TIMEOUT`, never a literal.
- Cases (1) and (2) are scored **as a PAIR**. A detector that catches (1) by warning on
  everything fails (2), and the two are only meaningful together.
- `git status` shows **zero** files modified under `src/commands/` or `src/agents/` — this
  phase is Python-only.

---

### Phase 3 — Cross-reference sweep + records

**Route: instruction-author → instruction-reviewer** for every `src/` and plan-document edit.

Open the phase with `grep -rn "English\|non-English\|Cyrillic\|language" src/ *.md` and
reconcile the result against the sites Phases 1–2 touched. **This sweep list is NOT certified
exhaustive** — treat a hit not named in this plan as an omission in this plan, not as a new
defect. **Expect fact 5's unrelated hits** (the `"language"` dict key in the `_audit` /
`_summarize` / `_review` preflight parsers, and `/devforge:constitute`'s `--sample-files-json`
shape); **check what each hit is about before treating it as a target.**

Scope:

- **`CHANGELOG.md`** — a new `### Added` subsection under the existing `## [Unreleased]`
  (fact 23), **placed ABOVE the existing `### Changed`**, matching Keep-a-Changelog ordering
  and the in-file precedent of `## [2.0.9]`'s own `### Added`. **Read the file live; do not
  create a stray heading on the strength of this note** — `## [Unreleased]` existed on
  2026-08-23 and an older plan in this repo recorded that it did not, six days earlier.
- **Repo-root `CLAUDE.md`** — the plan-87 one-liner, appended after the plan-86 bullet and
  before the blank line preceding the five-FINDINGS paragraph (fact 24). **Pure append.**
- **`PLAN-STATUS-ARCHIVE.md`** — the mirrored full entry, per this repo's index/archive split.
- **`src/devforge/storage-rules.md` — check only, and record the no-op as deliberate.** This
  plan creates no artifact and changes no artifact's shape, so that file has nothing to gain;
  **recording that explicitly is what stops a later session from "harmonizing" it in.**

**Commits: one per phase, no AI-attribution trailer** (this repo's commits carry none — match
the trailer-free convention), lowercase terse subject with a scope prefix matching
`git log --oneline`.

**Verify:**

- The sweep returns zero dangling references; `python3 -m unittest` over `tests/` is green.
- **The `CHANGELOG.md` entry states the honest bound** — an advisory warning on one commit
  path, and **not** a guarantee that artifacts are English. An entry claiming the framework
  now enforces English has over-claimed by two layers.
- **The repo-root `CLAUDE.md` one-liner names the coverage gap** (fact 21): the guard rides
  `artifact_helper commit-artifacts` and **not** `implement_helper wip-commit`.
- **No plan vocabulary in emitted text** — "D1", "D4", "Phase 2" and this plan's number are
  maintainer vocabulary. Emitted text names only the rule, the command and the warning.
- `scripts/verify-agent-reachability.py` and `scripts/verify-memory-lane.py` pass (nothing here
  touches either, so a failure means something unintended moved).
- **The plan-86 bullet is byte-unchanged** — this is an append, not an edit of its neighbour.

---

### Phase 4 — Consumer observation *(user-driven HARD GATE)*

**Everything above is build-verified, NOT consumer-validated.** Phase 2's behavior has never
been observed in a real pipeline commit, and no phase above may claim otherwise.

**Known-answer anchor**, so this is a regression anchor rather than an exploratory run:

1. **The warning case.** Commit an artifact containing exactly one Cyrillic word through
   `artifact_helper commit-artifacts`. **MUST** print the warning naming that file on stderr,
   **MUST** exit 0, and **MUST** land the commit with its stdout JSON unchanged.
2. **The clean case.** A normal pipeline artifact commit — an ASCII-only `spec.md` or `plan.md`
   — **MUST** print no language warning at all. **Scored as a PAIR with (1)**; a detector that
   passes (1) by warning on everything fails here.

**Verify:**

- Both cases are scored **explicitly** — stated, not summarized.
- **Case 2 is run on a REAL pipeline commit**, not a synthetic ASCII fixture. The synthetic
  version is already covered by Phase 2's test (2); what this case adds is the real staged set,
  including the directory-path arm (fact 15).
- Record the result in `REGRESSION-ANCHORS.md`, naming the Phase-2 tests alongside the observed
  behavior.
- **If it fails**, record the negative here with the artifacts and identify which mechanism
  produced it before proposing anything further — a missed word in case 1 is a D2 range or
  enumeration finding, a spurious warning in case 2 is a D2 or decode finding, and a nonzero
  exit is a D1/D3 finding (the fail-soft wrapper leaked). **They have different fixes.**
- **A clean run is NOT evidence the guard works.** It is evidence the detector does not fire on
  clean input. **D1's strengthening trigger is an observed LEAK, and this phase cannot produce
  one** — say so in the record rather than letting a green Phase 4 read as validation.

---

## Non-goals

- **A fail-closed mode, an override flag, or a skip arm.** D1 is advisory and the strengthening
  trigger is an OBSERVED leak. **A future session that finds the warning ignored has a D1
  re-open with a named trigger, not a licence to block a commit** — and a fail-closed detector
  would immediately owe the quote carve-out (fact 20) that this repo's zero-escape-hatch policy
  forbids.
- **General non-Latin script detection.** D2 is Cyrillic-only. Adding a second script is one
  more range in the same character class and needs its own trigger — a second configured
  language — not a general-purpose Unicode dependency.
- **Any `install.sh` / `update.sh` change.** D5 rejected the closing-message `echo` for this
  plan and recorded it as the named fallback. Both scripts stay byte-unchanged (facts 7–9).
- **Emitting or validating the `language` settings key.** This framework writes no `language`
  key anywhere today (fact 5) and this plan adds none. `.claude/settings.local.json` stays
  exactly what it is — a name in `src/manifest.json`'s `projectOwned` list (fact 6) that
  `update.sh` skips and nothing writes. **The README note is DOCUMENTATION; it emits nothing.**
- **Scanning outside the `commit-artifacts` chokepoint.** No pre-commit hook, no other helper.
  ⚠ **`implement_helper wip-commit` is a second commit path and is deliberately NOT covered**
  (fact 21) — so a leak inside a per-task or `[WIP] fix:` code commit is invisible to this
  guard. **That is the plan's coverage bound, stated rather than argued away**; widening it is
  a separate change with its own argument.
- **The operator's conversation language.** Out of scope entirely. Nothing in this plan
  discourages, detects or reports on a non-English response language, and D4's rule says so
  in the emitted text (*"applies to conversation only"*).
- **Back-porting the rule into already-shipped consumer installs.** It arrives through the
  normal `install.sh` / `update.sh` path. No migration, no backfill, no rewrite of any
  already-rendered `CLAUDE.md`. Note that `CLAUDE.md` is three-way-merged rather than
  overwritten (`src/manifest.json:28`), so an existing install picks the rule up through that
  merge.
- **Auditing the existing artifact corpus for non-English content.** This plan guards new
  commits; it makes no claim about what is already on disk and runs no historical scan.

---

## Dependencies + related

- **Plan 34** (`34-VERIFY-HYGIENE-FALSE-POSITIVE-PLAN.md`) — the ADVISORY precedent D1 rests on
  (fact 18). **Not touched**; cited for the stance only, and the demotion it performed
  (blocking → advisory) is the direction this plan starts in rather than arrives at.
- **Plan 44** — the WARN-only fail-soft precedent (fact 19), and the source of Phase 2's
  try/except discipline. **Not touched.**
- **Plan 37** (`37-PER-STEP-ARTIFACT-COMMIT-PLAN.md`) — the plan that made
  `artifact_helper commit-artifacts` the shared artifact-commit chokepoint every pipeline
  command rides. **It is the reason a single hook point covers the whole artifact corpus**, and
  it is the reason fact 21's second path exists separately. **No behavior of that plan changes
  here** — the verb's contract, exit codes and both stdout shapes are preserved by D3.
- **Plan 83** (`83-DOWNSTREAM-REENTRY-SEED-PLAN.md`) — the source of the ratified legitimate
  false-positive class (fact 20): the `conversational (in-window user report; no report file)`
  provenance and its user-quoting `invalidating_evidence`. **This is D1's deciding argument and
  D4's final clause.** Nothing in that plan changes; it is read, not edited.
- **Plan 62** — the stdlib-clean stance D2 honours (no third-party Unicode dependency, no
  `install.sh` change). **Its `z3-solver` exception is a separate, ratified decision and is not
  precedent for adding a dependency here.**
- **Plan 63** — the 13/7 model-invocable carve-out. **Untouched and unaffected**: this plan
  changes no command frontmatter, no `description`, and no command's invocation route.
  **Recorded so a Phase-3 sweep does not go looking for a count to update** — there is none.
- **Plan 72** (`72-UPDATE-SH-REPAIR-GUARD-PLAN.md`) — the recent `install.sh` / `update.sh`
  work D5 cites as the reason a docs-only phase stays zero-script. **Not touched.**
- **Plan 79** — the memory-lane section rubric that matches `## What Failed` / `## What Worked`
  / `## Known Pitfalls` by English heading text. **Cited in `## Origin` as one concrete
  mechanical dependency on an English corpus, not as a surface this plan edits.**
- **Plan 75** — the no-new-check-number / no-new-validator tripwire. **Both halves hold**: this
  plan adds no `verify-*` gate, no PHASE-3.5 number, and no hard-fail validator. The detector
  is a warning, which is neither.

---

## Context for next session

**The one sentence that governs everything here:** Claude Code's `language` key is an
instruction to the model rather than a filter over its writes, so the framework's English-only
file corpus is defended by ONE instruction rule and observed by ONE advisory warning — and
nothing here enforces anything.

**Trap 1 — reading the title as a description of what shipped.** *"Every byte written to a
file"* is the GOAL. The detector covers `artifact_helper commit-artifacts` and **not**
`implement_helper wip-commit` (fact 21), so per-task and `[WIP] fix:` code commits are outside
it. **A session that believes the corpus is covered end-to-end will not build the second half
when it is eventually needed.**

**Trap 2 — appending the warning to `stage_errors`.** That list is the exit-1 channel
(fact 13). It is the nearest-looking list to the new warning, it is one line away in the same
function, and using it converts an advisory into a hard failure with no test necessarily
catching it. **Phase 2's most important verify criterion exists for this.**

**Trap 3 — adding a stdout-JSON key.** It breaks a test whose whole job is pinning that object
(fact 14) and, worse, it invites a downstream caller to gate on an advisory (facts 12, D3).
**The two stdout shapes are the machine contract; stderr is the human channel.**

**Trap 4 — treating a clean Phase 4 as validation.** A detector that does not fire on clean
input has demonstrated that it does not false-positive. **It has demonstrated nothing about
leaks**, because no leak has ever been observed in this repo — which is also why D1's
strengthening trigger is an observation and not a rate.

**Trap 5 — flattening fact 3.** `.claude/settings.local.json` is git-excluded *when Claude Code
creates it*; a hand-created one is not. **The operator most likely to create it by hand is the
one who just read the README paragraph telling them to.**

**Trap 6 — widening D4's final clause.** *"Verbatim quotes of user-reported words may keep
their original language"* is narrow on purpose. **"Quotes may be non-English" is a different
rule** and it is the crack D4's counter-argument predicts.

**Trap 7 — reading this plan as an argument against the `language` setting.** It is not. The
maintainer's use of it is legitimate and this plan is written to make it SAFE, not to walk it
back. Any phase that starts discouraging the setting has left this plan.

**The working tree is uncommitted throughout**, and several plans this file cites are
working-tree state, so any "shipped" claim about them means reviewed-but-uncommitted rather
than released. Re-check each from the code rather than from a Status line.

**Discovered while drafting, NOT owned by this plan and not fixed here:**

1. **`src/manifest.json`'s `projectOwned` list is honoured by `update.sh` and ignored by
   `install.sh`.** Its description reads *"Files generated/customized per-project — NEVER
   overwrite"* with no qualifier about which script implements it, while `install.sh` reads the
   manifest for `version` only (fact 9) and unconditionally overwrites `.claude/settings.json`
   (fact 8) — a file that list names. The overwrite is DOCUMENTED behavior (`src/CLAUDE.md`
   states *"Re-running `install.sh` overwrites `.claude/settings.json` and restores the
   hooks"*), so this is a scope-wording observation about the manifest description, not a
   defect in either script. **Recorded, not owned; D5 works around it by naming the two files
   neither script touches.**
2. **No repo-wide convention exists for what language artifacts are written in.** Before this
   plan, the requirement was implicit in every English prompt and every English-token
   mechanical check, and stated nowhere. **Phase 1's item 15 is the first explicit statement**,
   which means it establishes precedent for the `### Always` list rather than following one.

---

## When resuming work

1. Read this file in full, then **Verified mechanics** again — twenty-five rows, each checkable
   in under a minute. **If rows 10, 11, 12, 13, 14, 15, 16 or 17 no longer hold, stop and
   re-derive**: they are Phase 2's hook point, its warning shape, its timeout discipline, its
   output constraint and Phase 1's landing site, and D3's and D4's decisions rest on them.
2. **Read `src/devforge/lib/_artifact/_cli.py` in full before touching it** — not just
   `_cmd_commit_artifacts`. The four `_git_*` primitives' timeout discipline, the module
   docstring's numbered rules, and the two stdout shapes all constrain what Phase 2 may write.
3. **Read `src/CLAUDE.md`'s whole `## Key Rules` section before appending** — both lists, not
   just `### Always`. The `### Never` items are where a rule about what NOT to write would
   otherwise land, and D4's choice of the `### Always` list is deliberate: the rule states a
   positive obligation about every file, not a prohibition on one act.
4. **Re-verify every anchor before use. Grep the quoted string, never the `:NNN`** —
   `commit-artifacts: warning:`, `stage_errors`, `nothing to commit`, `_GIT_TIMEOUT`,
   `Crash recovery`, `### Never`, `settings.local.json`, `## [Unreleased]`.
5. **Re-fetch the two Claude Code doc pages before writing or amending the README note**
   (facts 1–4). They are external, they evolve, and **the load-bearing fact is an ABSENCE** —
   that the docs describe `language` as affecting how Claude *responds* and say nothing about
   file writes. **If a future version of those pages scopes the key to conversation
   explicitly, D1's detector becomes redundant and this plan should be re-read, not extended.**
6. **Route every edit through the house loops:** **instruction-author → instruction-reviewer +
   claude-code-guide** for BOTH Phase-1 files — `src/CLAUDE.md` because it ships as a
   consumer's root `CLAUDE.md`, and **`README.md` because its D5 paragraph describes the Claude
   Code settings surface** (key, carriers, git-exclusion behavior), which is the same
   integration class; **instruction-author → instruction-reviewer** for every plan-document
   edit; **python-engineer → python-reviewer, test-first** for Phase 2. **Phase 1 dispatches no
   python-engineer and Phase 2 dispatches no instruction-author** — a phase that finds itself
   needing the other has crossed its own boundary and must stop.
7. **Do not let Phase 2's momentum turn the warning into a gate.** D1 is ratified advisory, its
   strengthening trigger is a named observation, and the carve-out a fail-closed version would
   need is forbidden by this repo's zero-escape-hatch policy. **The counter-arguments under
   each decision are retained precisely so a re-open is argued rather than drifted into.**
