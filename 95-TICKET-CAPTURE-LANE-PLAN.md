# 95 — A local ticket capture lane: `tickets/NNN-<slug>.md` as a first-class document type, so a noticed non-bug work item and a pasted tracker ticket both survive the moment they were mentioned

**Status:** **✅ DONE (build) 2026-09-04 — Phase 0 CLOSED (every item D1–D7 + OQ-1–OQ-7 ratified AS RECOMMENDED by a single blanket maintainer directive) and Phases 1, 2, 2b, 3a, 3 and 4 all BUILT the same day.** Commits: `41ff23a` Phase 0 close · `3c0f954` Phase 1 · `b7fa039` Phase 2 · `04882bf` Phase 2b · `b791359` Phase 3a · `180301e` Phase 3 · `fd069a6` Phase 4. ⚠ **Phases 2b and 3a are MID-BUILD ADDITIONS** — prerequisites Phases 2 and 3 discovered they needed, lettered so every downstream cited number stayed intact, and **3a runs BEFORE 3.** **Phase 5 consumer e2e DEFERRED — user-driven HARD GATE, NOT run: everything above is build-verified and NOT consumer-validated**, and the five known-answer anchors are the recipe, with **anchors 2 and 3 scored as a PAIR.** Every decision keeps its recommendation, its alternatives with the reason each is rejected, and its honest bound — **and ratification changed none of them.** ⚠ **The closure came as ONE directive and no per-item deliberation was supplied** — see `## Phase 0 close record`, which says so plainly rather than implying fourteen separate arguments were had. **Ratifying a recommendation does not strengthen it**, and a build that reads a ratified bound as discharged has left this plan.

- **The evidence is ONE maintainer request, dated 2026-09-04, given in conversation. There is NO consumer incident and none is claimed.** This is a predicted-gap / maintainer-directive plan in plan 87's class. **Say that wherever this plan is summarized** — see `## Evidence constraint`.
- **This is explicitly NOT a Jira replacement and it adds NO tracker integration.** It inherits plan 91's stance verbatim: *nothing checks that the ticket exists.* A `tickets/` file records what a human wrote down; it never asserts that a tracker agrees.
- **`bugs/` is not touched.** Its schema, its helper, `/devforge:fix`'s cold lane and `/devforge:report-bug`'s behavior all stay as plan 88 shipped them — with ONE narrow exception that is its own decision to ratify or decline (D6).
- **Phase 5 is a user-driven consumer e2e HARD GATE and it is the only place any of this is observed on a real install.** Everything Phases 1–4 produce will be build-verified and NOT consumer-validated.

**Branch:** `develop-2.0-init`
**Created:** 2026-09-04.

This plan document contains no private-client identifiers and is intended to be **committed normally**, unlike the deliberately-untracked plans 73/74/75.

---

## Evidence constraint

**One maintainer request, 2026-09-04, in conversation.** No consumer run failed, no developer reported a lost ticket, and nothing here has been measured. The request describes a friction the maintainer names from their own working experience; **that is a stated observation, not a recorded incident, and this plan does not upgrade it into one.**

Beside it sit **four mechanically verified facts**, each re-derivable in under a minute and each recorded in `## Verified mechanics`:

1. `src/commands/research/` contains **zero** occurrences of `bugs/` — the same class of finding that authorized plan 88 (a document type whose named consumer does not read it).
2. `src/` contains **zero** occurrences of `tickets/` and **zero** of `report-ticket` — this lane is first-of-its-kind everywhere, with no partial prior art to reconcile against.
3. `/devforge:research` Phase 0.3 treats any non-empty `$ARGUMENTS` as the topic and persists it verbatim into `.devforge/research-state.json`, a file `src/files/devforge.gitignore:4` ignores and Phase 0.3 overwrites unconditionally on every run.
4. The promoted-command roster is pinned in **three** places, one of which fails loudly on an unregistered command and one of which fails **silently** (`## Verified mechanics` rows 9 and 10).

**Fact 4 is the only one that changes the shape of the build rather than its motivation**, and it is why D7 exists.

⚠ **A summary of this plan that says "tickets were being lost" has invented a finding.** What is verified is that the raw prompt lands in a gitignored file that the next run overwrites — a mechanism by which text does not persist. **Whether that has ever cost anyone anything is unmeasured, and Phase 5 does not measure it either.**

---

## Origin — one maintainer request, 2026-09-04

Given in conversation, in Ukrainian. **Paraphrased rather than quoted**, because the original message names working context that has no place in a tracked repository file:

- Today a feature starts at `/devforge:research`, fed either a hand-written prompt or the text of a tracker ticket pasted into the invocation.
- A **bug** a developer notices has a capture path: `/devforge:report-bug` writes `bugs/NNN-<slug>.md` and the developer moves on.
- A **non-bug** work item — a feature idea, an enhancement, an improvement noticed in passing — has **no** capture path at all. The choice is: start the full pipeline now, or keep it in your head.
- Tracker connectivity is **not always available**, and the pasted-ticket route depends on having the tracker open at the moment of invocation.
- The proposal: a separate **document type** — a ticket — holding either dumped tracker-ticket data or the kind of item that today gets filed as a bug because `bugs/` is the only drawer that exists.
- Merging bugs and tickets into one place was floated as an option.

**That last bullet is D1**, and it is the decision with the largest blast radius in this plan. It is answered against `/devforge:fix`'s cold-lane trigger, not against taste.

### The framings this plan rejects, recorded so they are not re-proposed

- **"Just paste it into `/devforge:research` and save the feature."** This is what happens today, and it works — for an item you intend to work on **now**. It is not a capture path: `/devforge:research` runs a mandatory six-dimension rubric (`research/main.md:169`), allocates a feature directory and creates a branch on a confirmed save. **Filing something for next month costs a full intake run, or nothing is written.**
- **"Widen `bugs/` to hold everything and call the field `Type`."** Rejected at D1 on a mechanical ground, not a semantic one: `/devforge:fix`'s cold mode triggers on the literal path shape `bugs/NNN-<slug>.md`.
- **"Add tracker integration so a ticket is fetched rather than pasted."** A non-goal, stated as such. It would make the framework depend on network access and on credentials it has no way to hold, and plan 91 already ratified the opposite stance for the ticket ID itself.

---

## What is actually being added

Five things. **Phase 0 ratifies each independently**, except D4, whose dependency on D3 is named at both.

1. **A `tickets/` document type** — `tickets/NNN-<slug>.md`, sibling to `bugs/`, with its own numbering sequence, its own field set and its own status vocabulary (D1, D2, D3, OQ-3, OQ-5).
2. **`/devforge:report-ticket`** — a new pure-capture command mirroring `/devforge:report-bug`'s shape: two helper verbs, no agent, no diagnosis, no lifecycle advancement (D3). **This is a 21st promoted command and a 17th model-invocable one** (D7).
3. **A consumer, in the same plan** — `/devforge:research` accepts a `tickets/NNN-*.md` path as its argument, seeds the verbatim prompt from the file's body, and pre-offers the file's recorded ticket ID at Step 4.1's ticket question (D4).
4. **A manual-only lifecycle** — `Open → In Progress → Done`, maintained by whoever works the item, with **no** mechanical writer anywhere in v1 (D5).
5. **One advisory sentence in the conversational offer** (D6) — and it is the only byte this plan proposes to change in anything plan 88 shipped.

**⚠ Four honest bounds that must survive into every emitted sentence:**

- **Nothing checks the tracker.** Plan 91's discipline-not-verification statement is inherited whole: the only test applied to a ticket ID is its shape, so `PROJ-0000` satisfies the rule exactly as a real ticket does.
- **Nothing links a ticket file to the feature directory a later run allocates from it.** D5 keeps every write manual in v1, so a project can work a ticket and leave its file reading `Open` forever. **That is the ratified design, not a defect** — and it is the single largest thing this plan does not do.
- **`**Type**` is model judgment with nothing behind it.** No phase validates that an item filed as `enhancement` is not a defect.
- **The new command's `description` enters the always-on skill listing.** Plan 93 recorded that pressure explicitly when it made three commands model-invocable; a seventeenth is a real, permanent context cost paid by every session in every install.

---

## Verified mechanics (2026-09-04)

Every row was confirmed by opening the named file. **The quoted token is the anchor; the digit is a dated hint** — this repo has documented anchor rot, so grep the string, never the `:NNN`.

| # | Fact | Evidence |
|---|------|----------|
| 1 | **`/devforge:report-bug` is the shape to mirror, and it is small.** 101 lines. Frontmatter: `name`, `description`, `argument-hint`, `allowed-tools` (a YAML list of `Read` plus two `Bash(.devforge/lib/report_bug_helper <verb> *)` entries). Body: an overview paragraph, `## Maintainer note`, `## Outputs of this command`, `## Helper interaction model`, four phases, and `## Important rules` with **8** numbered rules | `src/commands/report-bug/main.md:1`–`:9`, `:19`–`:35`, `:92`–`:101` |
| 2 | **Two verbs, and the split is the model.** `preflight` resolves the workspace fail-soft, prints `{bugs_dir, root, is_wrapper}` and **always exits 0 — no gate, never blocks**; `write-bug` validates, builds one issue dict, writes through the shared writer and prints a JSON array of written paths (exit 0 ok / 2 arg error / 1 I/O error). The orchestrator supplies `--date` — **the helper never calls the clock** | `_report_bug/_cli.py:40`–`:71`, `:74`–`:151`, `:236`–`:240` |
| 3 | **`_SUBCOMMAND_REGISTRY` is a documented extension point** — a `(verb, help, handler)` triple list with a three-step comment for adding a verb | `_report_bug/_cli.py:158`–`:184` |
| 4 | **The writer is shared and already has three reusable parts.** `_shared/bug_file.py` carries `_scan_highest_bug_number` (scan-once, highest `NNN-` prefix + 1, zero-padded to 3), `_slugify` (lowercase, non-alphanumeric runs → `-`, collapse, strip, 30-char cap cut at a word boundary, never empty), `_format_bug`, `file_bugs` (atomic `mkstemp` + `os.replace`, `os.makedirs(bugs_dir, exist_ok=True)`) and `close_bug` (plan 88 D4) | `_shared/bug_file.py:133`, `:154`, `:180`, `:266`, `:291`, `:357` |
| 5 | **The launcher is a pair, not one file.** `src/devforge/lib/report_bug_helper` is a POSIX `sh` shim that resolves `python3` / `py -3` / `python` and `exec`s `$HERE/report_bug_helper.py`, exiting 127 with a message when none is found. So a new helper is **four** files: the shim, the `.py` entry, `_<pkg>/__init__.py` and `_<pkg>/_cli.py` | `src/devforge/lib/report_bug_helper:1`–`:35`; `src/devforge/lib/report_bug_helper.py`; `_report_bug/__init__.py` |
| 6 | **The ticket-ID format has exactly one owner.** `TICKET_RE = re.compile(r"^[A-Z]+-[0-9]+$")` in `_shared/feature_alloc.py`; `normalize_ticket` strips and matches, **rejecting lowercase rather than folding it**; `read_require_ticket` reads the `REQUIRE_TICKET` key from `project-config.json` and its docstring states *"REQUIRE_TICKET is discipline, not verification"* | `_shared/feature_alloc.py:335`, `:339`, `:387`, `:437`, `:448`, `:464` |
| 7 | **`/devforge:research` accepts any non-empty `$ARGUMENTS` as the topic, and persists the raw text.** Phase 0.3 runs `reset-memo` / `reset-report` / `set-topic` / `set-verbatim-prompt --value "<full raw $ARGUMENTS>"` / `set-date`, and states that the reset is **unconditional** — *"every invocation starts clean"*. ⚠ **Nothing there detects a path**: a `tickets/001-x.md` argument today becomes the topic string, verbatim | `research/main.md:77`–`:89` |
| 8 | **The rubric is mandatory and its pre-filled-input carve-out is already narrow.** *"Pre-filled input is a STARTING POINT for the `symptom` dimension only — never a license to auto-fill the remaining 5 in one pass"*, followed by the never-fabricate-a-user-mode rule. **Step 4.1's ticket question has exactly two authored options** — `"No ticket"` and `"I'll type the ticket"` — with *"Do NOT add an 'Other' option of your own"*, neither marked `(Recommended)`, and the discipline-not-verification statement printed in the same message | `research/main.md:169`, `:171`, `:1198`, `:1200`, `:1209`–`:1213`, `:1228`–`:1233` |
| 9 | ⚠ **The promoted roster is GATED and a missing registration FAILS LOUDLY.** `scripts/lib/memory_lane.py`'s `DISPOSITIONS` comment: *"Every name in `scripts/emitters/claude.py`'s `_PROMOTED` tuple MUST have exactly one entry here (Rule 1) — a command added to `_PROMOTED` with no entry fails immediately, which is the point."* `report-bug`'s entry is `NOT_APPLICABLE` with the reason *"Pure capture — writes one bugs/NNN-slug.md and stops; dispatches no agent and renders no judgment for memory to inform."* **Two test pins move**: `assertEqual(len(_mod.DISPOSITIONS), 20)` and `test_live_repo_matches_the_20_known_names`. **Four prose numerals move**: the group comments `# ---- READS (13)` and `# ---- N/A (7)`, and the docstring's *"The 20 `_PROMOTED` commands"* / *"13 READS / 7 N/A split"* | `memory_lane.py:69`–`:78`, `:97`–`:102`, `:104`, `:190`, `:230`–`:235`; `tests/lib/test_memory_lane.py:218`, `:548`–`:550` |
| 10 | ⚠ **A THIRD roster exists and a missing registration there fails SILENTLY.** `_profile/_segment.py`'s `HELPER_STEMS` maps each of the 20 commands to its helper stem (`"report-bug": "report_bug_helper"`), `KNOWN_COMMANDS` is derived from its keys, and `tests/lib/_profile/test_segment.py` asserts **20** unique entries twice. **Nothing cross-checks it against `_PROMOTED`**, so a 21st command with no entry passes every test and the wall-clock profiler mis-segments its runs | `_profile/_segment.py:72`–`:94`; `tests/lib/_profile/test_segment.py:12`, `:121`–`:127` |
| 11 | **`_PROMOTED` is a hand-maintained 20-name tuple** with a comment saying so, and `claude.py --list` prints it as a machine-readable contract. The emitter test iterates the tuple rather than pinning its length | `scripts/emitters/claude.py:53`–`:57`, `:123`–`:129`; `tests/scripts/test_claude_emitter.py:259`–`:268`, `:291`–`:316` |
| 12 | **The live invocability counts are 20 promoted / 4 human-typed-only / 16 model-invocable, and ONE site spells them in WORDS.** `README.md`: *"Sixteen of the twenty are model-invocable … Four are human-typed only."* ⚠ **A digit grep misses that sentence entirely.** `src/CLAUDE.md` carries **no numeral** — it says *"Four are **human-typed only**"* and *"Every other forge command is model-invocable"*, both of which stay true at 21 commands | `README.md:54`; `src/CLAUDE.md` (Workflow section); `grep -n "^disable-model-invocation" src/commands/` |
| 13 | **`storage-rules.md` carries `bugs/` in exactly three structural places**: the `## Directory Structure` tree, the `## File Lifecycle` block (`report-bug → creates bugs/NNN-description.md`, plus the `verify` and `fix` lines), and a full `## Bug Report Rules` section (Directory / Naming / Status Lifecycle / Bug File Format / Field notes / How Bug Files Are Created / How Bug Files Are Resolved) | `src/devforge/storage-rules.md:8`–`:9`, `:263`–`:267`, `:362`–`:437` |
| 14 | **`bugs/` is tracked by default and created lazily.** `src/files/devforge.gitignore` lists only `.devforge/` paths — no `bugs/` entry, so bug files are ordinary tracked content once committed. `grep -n bugs install.sh` returns **nothing**, and `file_bugs` calls `os.makedirs(bugs_dir, exist_ok=True)` on first write. ⚠ **`DEVELOPMENT-STATUS.md:69` claims install ships an empty `bugs/` with a `.gitkeep`; the only `gitkeep` token in any `*.sh` is a comment at `install.sh:378` about `docs/`.** Pre-existing, out of this plan's scope, recorded so it is not inherited | `src/files/devforge.gitignore:1`–`:21`; `_shared/bug_file.py:291`; `DEVELOPMENT-STATUS.md:69`; `install.sh:378` |
| 15 | **`/devforge:report-bug` makes no git commit** — *"it makes no git commit (the bug file is left in the working tree for the user to commit). One run writes exactly one bug file."* | `src/commands/report-bug/main.md:29` |
| 16 | **Long text already has a house route that avoids a shell argument.** `implement_helper` reads a review verdict *"from --verdict-file &lt;path&gt; or stdin"*, and `verify_helper` documents *"Pass `-` to read from stdin"* on four arguments | `_implement/_cmds_review_loop.py:9`, `:193`, `:240`; `_verify/_cli.py:324`, `:370`, `:1413`, `:1425` |
| 17 | **`src/commands/research/` contains ZERO `bugs/` occurrences**, and **`src/` contains ZERO `tickets/` and ZERO `report-ticket` occurrences.** The first is the plan-88 no-consumer finding, still true; the second means this lane has no partial prior art anywhere in the emitted tree | `grep -rc "bugs/" src/commands/research/`; `grep -rc "tickets/\|report-ticket" src/` |

### Claude Code authoring surface, verified against current docs

Fetched **2026-09-04** from `https://code.claude.com/docs/en/slash-commands`. **Cited so a future author re-verifies rather than trusting this file.**

- **Command files are skill files.** *"Custom commands have been merged into skills. A file at `.claude/commands/deploy.md` and a skill at `.claude/skills/deploy/SKILL.md` both create `/deploy` and work the same way."*
- **⚠ `name` is INERT in a command file, verbatim:** *"Files in `.claude/commands/` support the same frontmatter, except `name` and `paths`, which Claude Code ignores in a command file. You invoke a command file by its file name."* ⚠ **Every shipped forge command source carries a `name:` line anyway** (`report-bug/main.md:2`). **This plan mirrors that house shape and changes nothing about it** — and **no sentence it writes may claim the line does anything.**
- **`description`, verbatim:** *"What the skill does and when to use it. Claude uses this to decide when to apply the skill. If omitted, uses the first paragraph of markdown content. Put the key use case first: the combined `description` and `when_to_use` text is truncated at 1,536 characters in the skill listing to reduce context usage."* ⇒ **the listing cost is documented, and plan 63 OQ-1's ≈40-word budget is the house rule that sits under it.**
- **`argument-hint`, verbatim:** *"Hint shown during autocomplete to indicate expected arguments."*
- **`allowed-tools`, verbatim:** *"Tools Claude can use without asking permission during the turn that invokes this skill. The grant clears when you send your next message. Accepts a space- or comma-separated string, or a YAML list."*
- **`disable-model-invocation`, verbatim:** *"Set to `true` to prevent Claude from automatically loading this skill. Use for workflows you want to trigger manually with `/name`. … Default: `false`."* ⇒ **there is no positive key**: a command is model-invocable by **omitting** the field, which is what D3 does and what makes D7's count delta arithmetic rather than a choice of syntax.
- **`$ARGUMENTS`, verbatim:** *"All arguments passed when invoking the skill"* and *"The `$ARGUMENTS` placeholder always expands to the full argument string as typed."* ⇒ **a pasted multi-line body reaches the command intact.** ⚠ **What is NOT documented is what happens to that text once the orchestrator puts it inside a Bash argument** — which is OQ-6's whole subject.
- **⚠ Unknown keys in a LOCAL command file are not documented either way.** This plan adds no new frontmatter key, so nothing here depends on the answer.

---

## Decisions (D1–D7)

Each carries the recommendation, the alternatives with the reason each is rejected, and the **honest bound — what the decision does NOT achieve.** **The bounds are load-bearing: a decision ratified with its bound deleted cannot be re-opened honestly later.**

### D1 — A separate sibling directory, NOT merged with `bugs/` *(RATIFIED 2026-09-04 — as recommended)*

**RECOMMENDED RULE.** The new document type lives in its **own top-level directory beside `bugs/`**, with its own numbering sequence (OQ-3), its own field set (D3), its own status vocabulary (D5) and its own creating command (D3). **`bugs/` gains nothing, loses nothing and changes in no byte.**

**Alternatives considered:**

- *(a) One directory for both — merge, or rename `bugs/` to something type-neutral.* **REJECTED on a mechanical ground, and it is the ground that decides this plan.** `/devforge:fix`'s cold mode triggers on an explicit `bugs/NNN-<slug>.md` argument — a **path shape**, chosen by plan 88 precisely because it is mechanical: no judgment call and no severity threshold. An enhancement file living under that path is a **syntactically valid cold-fix input**, and the cold lane ends in a clean `fix(scope):` commit having bypassed `/devforge:specify` → `/devforge:spec-check` → `/devforge:plan` → `/devforge:grill` → `/devforge:breakdown`. Closing that requires a **type discriminator read by `/devforge:fix`** — new branch logic inside a lane whose own Phase 5 consumer e2e has never run (plan 88 closed build-only, its e2e explicitly not waived). **Adding a branch to an unvalidated gate to make room for a filing convenience is the wrong trade in the wrong order.** A second, independent ground: the two types have different terminal states and different writers — a bug has `Fixed` and a mechanical closer (`close_bug`, fact 4), a ticket has neither (D5).
- *(b) Do nothing; keep pasting into `/devforge:research`.* **REJECTED on fact 7**: the pasted text lands in `.devforge/research-state.json`, which is gitignored and which Phase 0.3 overwrites unconditionally on the next run. It survives as `Intent.verbatim_prompt` **only** for a run that reaches a confirmed save. **An item filed for later has no file, and an item whose run was abandoned has nothing.**
- *(c) File the item as a `specs/` feature directory in a draft state.* **REJECTED**: intake has owned feature-directory allocation since plan 68 D3, and plan 91 made the leaf the feature's identifier. Allocating a directory before any intake run has happened inverts both, and a `YYYY/MM` bucket would then record the month the idea was **noticed** rather than the month it was **taken up**.
- *(d) A single flat backlog file with one section per item.* **REJECTED**: sequential numbering, slug derivation and atomic writes are helper-owned everywhere else in this repo (fact 4), and a single append-target file re-creates exactly the append-at-the-end / read-from-the-top window-drift failure class plan 79 spent a whole build removing from `.devforge/memory.md`.

**⚠ Honest bound, TWO parts.** **(i) Two drawers means a filing decision, every time, made by a human or by a model with an advisory rubric behind it** (D6). Nothing mechanical routes an item to the right drawer, and **a misfiled enhancement in `bugs/` is exactly as cold-fixable after this plan as before it** — this decision protects the new type from the trigger; it does not protect the trigger from human error. **(ii) Nothing connects a ticket file to whatever the pipeline later does with it** (D5's bound), so the two directories tell you what was captured and never what was finished.

### D2 — The name: `tickets/`, with a written disambiguation rule *(RATIFIED 2026-09-04 — as recommended; a fork, and the `tickets/` arm WITH the disambiguation rule is the one taken)*

**RECOMMENDED RULE.** The directory is **`tickets/`**, and `storage-rules.md` carries a **mandatory disambiguation rule** stating the two senses explicitly:

- **"ticket ID"** — the tracker identifier, shape `^[A-Z]+-[0-9]+$` (fact 6), asked at `/devforge:research` Step 4.1, used as the feature-directory leaf and the branch name.
- **"ticket file"** — `tickets/NNN-<slug>.md`, the local capture document this plan adds.

**Every sentence this plan writes into an emitted file uses one of the two full phrases, never a bare "ticket".**

**Alternatives considered:**

- *(a) `backlog/`.* **A live alternative with a real argument, and a ratifier who takes it is not overriding a strong recommendation.** It avoids the collision entirely: plan 91 shipped "ticket" meaning the tracker ID across four consumer-facing files plus `TICKET_RE`, `REQUIRE_TICKET`, the `spec/<ticket>` branch and the bucketed leaf, and **no disambiguation rule is needed for a word that is not reused.** Its costs: it discards the maintainer's own word for the thing (`## Origin`), and **a pasted tracker ticket for work starting this afternoon reads oddly in a directory called "backlog"** — the type holds in-progress intake material, not only deferred items.
- *(b) `intake/`.* **REJECTED, and it is worse than either fork.** "Intake" is already a loaded term in this pipeline: `/devforge:research` Phase 0.5 is the *intake-interrogation gate*, its setter is `record-intake-classification`, and its rendered block is `## Intake interpretation`. A directory by that name would collide with a **phase**, which is harder to disambiguate than a collision with a **field**.
- *(c) `tickets/` with no disambiguation rule.* **REJECTED**: the collision is real whether or not it is written down, and an unwritten convention is one a future session cannot follow.

**⚠ Honest bound.** **The disambiguation rule is prose and nothing enforces it.** No test greps for a bare "ticket", and none is proposed — a lint over English prose in this repo would fire on plan 91's own shipped sentences. **The rule binds authors who read `storage-rules.md`, and its failure mode is a future sentence that is ambiguous rather than wrong.**

### D3 — A new command `/devforge:report-ticket`, not a `--type` flag on `/devforge:report-bug` *(RATIFIED 2026-09-04 — as recommended, fields and status values included)*

**RECOMMENDED RULE.** A new command in `/devforge:report-bug`'s exact shape: **pure capture, agent-free, no diagnosis, no lifecycle advancement, model-invocable**, backed by a two-verb helper (`preflight` → `write-ticket`) that owns the directory resolution, the numbering, the slug, the validation and the atomic write (fact 2). **The orchestrator composes values and supplies the date; the helper never calls the clock.**

**The ticket file's fields, recommended and ratified at Phase 0 rather than at build:**

| Field | Values | Notes |
|---|---|---|
| `**Status**` | `Open` \| `In Progress` \| `Done` | Manual-only (D5). **`Done`, not `Fixed`** — a `Fixed` vocabulary would invite `close_bug`'s anchoring to be pointed at this file |
| `**Type**` | `enhancement` \| `task` \| `imported` | `imported` = the body is pasted tracker text. Model judgment, nothing checks it |
| `**Source**` | `manual` \| `paste` | Parallel to the bug file's `**Source**: verify \| manual` |
| `**Ticket**` | a tracker ID, or `(none)` | Validated through `normalize_ticket` when present — **the single owner, imported, never re-implemented** (fact 6, OQ-4) |
| `**Reported**` | `YYYY-MM-DD` | Supplied by the orchestrator |
| body | the idea, or the pasted tracker text **VERBATIM** | Never paraphrased, never summarized, never re-wrapped |

**Plus one rendering element that is NOT one of the six fields, named here because D4 part 2 depends on it:** the file's **H1 heading** — `# Ticket NNN: [Short Title]` — fed by an optional `--title` CLI argument that falls back to the body when omitted. **This mirrors `bug_file.py` exactly**, where `_format_bug` renders `# Bug NNN: <title>` from a `--title` argument defaulting to `--description` (`_cli.py:101`, `:247`–`:255`). **It is the value D4's consumer reads as the topic seed**, so a build that drops it leaves that arm with nothing to seed from.

**Alternatives considered:**

- *(a) A `--type` flag on `/devforge:report-bug`.* **REJECTED on three grounds.** First, that command's contract is defect-specific end to end: a `Critical | Warning | Info` severity with a documented default, a `**Feature**` / `**AC**` pair, `## Expected Behavior` / `## Actual Behavior` / `## Evidence` sections, and **8 rules** two of which (7 and 8) exist only to keep it away from `/devforge:fix`. A `--type` flag makes roughly half of that conditional. Second, **a mode flag inside a shipped contract is the escape-hatch shape the zero-escape-hatch policy forbids** — "these rules apply unless `--type ticket`" is precisely the clause form the policy names. Third, plan 88 D6's conversational rubric names `/devforge:report-bug` as **the bug arm specifically**, so widening the command falsifies a rubric that shipped about a week earlier (plan 88 closed 2026-08-27).
- *(b) No command — document the format and let a human write the file.* **REJECTED**: `NNN` numbering, slug derivation and the atomic write are helper-owned in every comparable path in this repo (fact 4). A hand-written file collides on `NNN` the first time two are written in one day, and the framework's own rule 4 in `/devforge:report-bug` says *"Never hardcode, guess, or compose the number or the slug yourself."*
- *(c) Make it human-typed-only (`disable-model-invocation: true`).* **REJECTED**: plan 93 narrowed that carve-out to a **single criterion** — a one-time mutation of the framework's own `.devforge/` basis with no feature scope — and this command meets none of it. Adopting the flag here would re-widen a carve-out narrowed one day earlier, and D6's whole point is that the model should be able to **offer and then run** the capture when a user mentions an item in conversation.

**⚠ Honest bound, THREE parts.** **(i) A 17th model-invocable command's `description` is permanent always-on context** in every session in every install — the fetched docs put the combined listing text under a 1,536-character truncation, and plan 93 recorded that a command's description is what is lost first when that budget is under pressure, while its NAME never evicts. **The ≈40-word budget from plan 63 OQ-1 binds, and a description that exceeds it has spent someone else's context.** **(ii) `**Type**` is unchecked** — nothing prevents a defect from being filed as `enhancement`, which lands it outside `/devforge:fix`'s cold lane with nothing to say so. **(iii) The `**Ticket**` value is shape-validated and nothing more** — plan 91's statement is inherited word for word, and this plan adds no verification of any kind.

### D4 — The consumer ships in the SAME plan *(RATIFIED 2026-09-04 — as recommended; DEPENDS ON D3, which was ratified in the same directive)*

**RECOMMENDED RULE.** `/devforge:report-ticket` does **not** ship without its reader. `/devforge:research` gains a **file-path arm** at Phase 0.3, instruction-only, in four parts:

1. **Detection.** When `$ARGUMENTS` names an existing file whose path matches the ticket-file shape, treat it as a **ticket-file invocation** rather than as a topic string. **This closes a real gap, not a hypothetical one**: today that argument becomes the topic verbatim (fact 7).
2. **Verbatim-prompt seeding.** The file's **body** becomes the value passed to `set-verbatim-prompt`; the file's **title** seeds the topic passed to `set-topic`. **Both existing setters, unchanged, no new state, no schema change.**
3. **The rubric is untouched.** `research/main.md:169`'s sentence is **EXTENDED, never weakened**: a ticket file is a starting point for the `symptom` dimension only, exactly as a pre-filled ticket pasted inline already is. **Every dimension is still asked separately and answered in its own turn**, and the never-fabricate-a-user-mode rule at `:171` gains a ticket-file clause so a future session cannot read "the ticket already says everything" as a skip licence.
4. **The ticket-ID pre-offer.** When the file carries a `**Ticket**:` value, Step 4.1's question 2 **pre-offers it as a third authored option** — `"<ID> (from the ticket file)"`, `"No ticket"`, `"I'll type the ticket"` — and **never auto-answers.** ⚠ **This keeps the AskUserQuestion contract intact**: three authored options is inside the 2–4 bound, and the tool's own free-text row is still the only "Other" (`research/main.md:1198`). **The discipline-not-verification statement at `:1200` is printed unchanged** — a pre-offered ID is still an unverified string.

**Why the consumer is not a follow-on plan — and this is the load-bearing argument.** `bugs/` shipped with **no consumer at all**, and that absence was itself the finding that authorized plan 88 roughly a week ago (it closed 2026-08-27); `src/commands/research/` still contains **zero** `bugs/` occurrences today (fact 17). **A capture lane with no reader is a lane that produces files nobody's tooling opens.** Shipping the reader in the same plan is the direct application of that lesson, and it costs one instruction-only phase.

**Alternatives considered:**

- *(a) `/devforge:specify` also gains the arm.* **REJECTED for v1.** `/devforge:specify` blocks until a pending research or discover handoff exists in a feature directory — a gate this plan does not touch — so a ticket file handed to it would be read and then refused. **`/devforge:research` is the intake front door and the ticket file is intake material.**
- *(b) `/devforge:discover` also gains the arm.* **REJECTED for v1, with a weaker reason and it is recorded as weaker.** `/devforge:discover` is the greenfield lane, and a pasted tracker ticket for a greenfield idea is a real shape. It is declined because it doubles the surface for one plan, **not** because it is wrong. **Named widening path**, with the trigger being an observed ticket file whose content is greenfield.
- *(c) Ship capture now, reader later.* **REJECTED on the plan-88 lesson above.**
- *(d) Detect the ticket file by reading `**Ticket**:` out of any argument rather than by path shape.* **REJECTED**: it would open and parse an arbitrary path the user named, which is a behavior change to every existing invocation, not an added arm.

**⚠ Honest bound, THREE parts.** **(i) Detection is path-shaped and therefore fallible** — a file that matches the shape and is not a ticket file is read as one, and a ticket file moved elsewhere is read as a topic string. **The failure is visible in the next message** (the run announces what it read), which is the whole mitigation. **(ii) The pre-offer is a convenience, not a link** — picking it records the ID in the feature directory and writes **nothing** back to the ticket file (D5). **(iii) Nothing verifies that the body reached the handoff intact**; OQ-6 is where that risk is decided, and a build that resolves OQ-6 by putting a pasted body inside a shell argument has chosen the failure this bound names.

### D5 — The lifecycle is MANUAL-ONLY in v1 *(RATIFIED 2026-09-04 — as recommended, so the tempting middle stays DECLINED for v1)*

**RECOMMENDED RULE.** `Open → In Progress → Done` is maintained by **whoever works the item**. **No command flips a ticket file's status, no command fills a field in it, and no command deletes one.** `/devforge:report-ticket` only ever writes a fresh `Open` record, and its rule set says so in the shape `/devforge:report-bug` rule 7 already uses.

**This is deliberately WEAKER than the bug lifecycle, and the asymmetry is the point.** A bug has exactly one mechanical writer — `/devforge:fix`'s cold lane, through `close_bug` — because plan 88 D4 chartered it and because a bug's terminal state is provable: the remediation passed its gates. **A ticket's terminal state is not provable by anything the framework observes.** "Done" for an enhancement means the feature shipped, which is a judgment call spread across `/devforge:verify` and a human.

**The tempting middle, recorded and recommended AGAINST for v1** *(a write OQ-7's commit reasoning would also apply to, were it built — OQ-7 itself asks only about `/devforge:report-ticket`'s own commit)*: `/devforge:research`, on a confirmed save that consumed a ticket file, could flip that file to `In Progress` and stamp the allocated feature directory into it. **It is genuinely useful** — it would close D1's bound (ii) and D4's bound (ii) at once. It is declined because it adds a **second writer to a document type on the day it is born**, and because Phase 4's write set in `/devforge:research` is a carefully enumerated list of artifacts **inside** the feature directory (`main.md:1188`, the fixed Phase-4 order), so a write to `tickets/` would be the first write that step makes outside it. **Named strengthening path with an observable trigger: a maintainer who reports losing track of which ticket files already have feature directories.**

**Alternatives considered:**

- *(a) Give tickets a mechanical closer mirroring `close_bug`.* **REJECTED**: there is no command whose successful completion means "this ticket is done" — `/devforge:verify` owns a **feature's** verdict, and a ticket may span several features or none.
- *(b) Drop `Status` entirely and let file presence mean "open".* **REJECTED**: it makes the drawer unreadable — an item worked last month is indistinguishable from one filed this morning, and deletion becomes the only way to close, which destroys the record.
- *(c) Flip the status at `/devforge:research` (the tempting middle).* **Recommended AGAINST for v1**, argued above, **recorded as the named strengthening path rather than refused.**

**⚠ Honest bound.** **A ticket file can be permanently stale and nothing anywhere will say so.** The framework will happily carry a `tickets/` directory of `Open` items that all shipped months ago. **That is the ratified design and it must be stated in the emitted text**, not discovered by a user — `storage-rules.md`'s new section says the lifecycle is manual, in the same voice as its existing *"Manual: the user edits `**Status**: Fixed`"* line.

### D6 — One sentence in the conversational fix-or-file offer *(RATIFIED 2026-09-04 — as recommended; still the ONLY change to anything plan 88 shipped)*

**RECOMMENDED RULE.** `src/CLAUDE.md`'s `### Conversational fix-or-file offer` keeps its three arms and its discriminator **verbatim** — *"whether the fix REPAIRS existing behavior or CHANGES what the system does — never by counting files."* Its **third arm** gains one clause: a change may be **filed for later** with `/devforge:report-ticket` as an alternative to starting the full chain from `/devforge:research` now.

**It is written as a dated, narrow amendment to plan 88's D6**, in the house form plan 85 used on plan 23 and plan 82 used on plan 62: plan 88's ledger entry and its D6 gain a dated note saying the third arm grew a file-it-for-later variant and that **nothing else in the rubric moved.**

**Alternatives considered:**

- *(a) Leave the rubric alone; let the new command be discovered from the catalog entry.* **REJECTED**: the rubric is the only place the model is told **when** to offer a filing path at all. A capture command absent from it is offered when the model happens to remember it, which is the discoverability failure plan 88 D6 was written to fix for bugs.
- *(b) Restructure the offer into four arms (repair-now / file-bug / file-ticket / full chain).* **REJECTED**: the discriminator is **repair vs change**, and a fourth arm would need a second discriminator — now-vs-later — which is a user preference, not a property of the defect. **One arm gaining a variant keeps the rubric's single axis.**
- *(c) Add a forward pointer from `/devforge:report-bug` to `/devforge:report-ticket`.* **REJECTED, and this is the strictest reading of the non-goal.** Plan 88 ratified reading (i) on `/devforge:report-bug` rule 8 — *"Rule 8 stays byte-unchanged and NO forward pointer is added there"* — with its counter-argument retained unresolved. **This plan takes no position on that fork and adds nothing to that file.**

**⚠ Honest bound.** **The offer is advisory model judgment and it is not a gate** — the same bound plan 88 D6 carries, inherited unchanged. **The only mechanical net in this whole plan is the helper's own argument validation**, which fires after the user has already typed the command. **Nothing detects an item that should have been captured and was not.**

### D7 — Scope tripwire: zero gates, and the roster registration is Python *(RATIFIED 2026-09-04 — as recommended)*

**RECOMMENDED RULE.** **Zero gates, zero new `verify-*` gate numbers, zero hard-fail validators** — plan 75's tripwire in both halves. **Nothing this plan adds ever blocks anything.**

**The plan-63/93 count delta is EXPLICIT and it is not zero:** the roster goes **20 → 21 promoted**, **16 → 17 model-invocable**, **4 human-typed-only unchanged.** The new command carries **no** `disable-model-invocation` line, which is what makes it model-invocable (the fetched docs: the field defaults to `false` and there is no positive form). **No existing command's flag moves and no existing description is widened.** ⚠ **Read the counts LIVE before writing any numeral** — plan 63's standing coordination rule, which has earned itself repeatedly.

**⚠ Registering a 21st command is PYTHON, and this is where this plan diverges from a naive phase split.** Three rosters must move together (facts 9, 10, 11):

1. **`scripts/emitters/claude.py` `_PROMOTED`** — one name appended. Its own test iterates the tuple, so nothing there pins a length.
2. **`scripts/lib/memory_lane.py` `DISPOSITIONS`** — one `NOT_APPLICABLE` entry **with a reason**, or `scripts/verify-memory-lane.py` fails immediately by design. Plus the `# ---- N/A (7)` group comment, the docstring's two numerals, and **two test pins** (`len(DISPOSITIONS) == 20`, `test_live_repo_matches_the_20_known_names`).
3. **`src/devforge/lib/_profile/_segment.py` `HELPER_STEMS`** — one `"report-ticket": "report_ticket_helper"` entry, plus the two `== 20` assertions in `tests/lib/_profile/test_segment.py`. ⚠ **Nothing cross-checks this map against `_PROMOTED`, so omitting it passes every test** and silently mis-segments the new command in every profiler run.

**Python (and the packaging that goes with it) is confined to this list, and a phase that needs more has crossed its boundary:**

1. `_shared/ticket_file.py` — the writer, importing `_slugify` and the scan helper from `_shared/bug_file.py` rather than copying them (OQ-1).
2. `_report_ticket/__init__.py` + `_report_ticket/_cli.py` + `report_ticket_helper.py` + the POSIX `report_ticket_helper` shim (fact 5), **the shim shipped executable**.
3. The three roster registrations above and their five test-pin updates.
4. Tests for every new function, **written and run in the same phase**, with the round-trip through the real producer rather than hand-authored fixtures (house rule).

**Everything else is instruction-only.** **No back-porting into shipped installs**: they arrive through `install.sh` / `update.sh`.

**Alternatives considered:**

- *(a) Put the `_PROMOTED` edit in the instruction phase, since it is "one line".* **REJECTED, and this is the divergence worth naming.** That one line makes `scripts/verify-memory-lane.py` fail until a Python dict gains an entry, and moves five assertions across two test modules. **A phase that calls itself instruction-only and then edits tests has mis-scoped itself**; the registration belongs with the rest of the Python.
- *(b) A `verify-ticket-consumed` gate that fails when a ticket file has a feature directory and still reads `Open`.* **REJECTED**: it would be the first mechanical blocker for a lane with zero observed failures, over a state D5 deliberately leaves manual. **Recorded as a shape, not built**, with the trigger being an observed stale-ticket incident.
- *(c) A cross-check test pinning `HELPER_STEMS` keys equal to `_PROMOTED`.* **⚠ Genuinely tempting and still REJECTED for this plan.** It would close a silent gap permanently and it is three lines. It is declined because it is a **maintainer-gate change**, which is exactly the kind of scope growth this decision exists to refuse, and because the gap is **pre-existing and not caused here**. **Recorded as an owned residual for a future plan**, with its cost measured (one test, one import).

**⚠ Honest bound.** **Nothing in this plan verifies that a ticket file is ever read by anyone.** D4 gives it a reader; **no check ever fires if that reader is never used**, and the `bugs/`-had-no-consumer finding could recur here in a year with nothing to detect it.

---

## Open questions (OQ-1–OQ-7)

### OQ-1 — Helper packaging: a sibling module, or a type parameter on the shared writer? *(ANSWERED 2026-09-04 — the sibling module as recommended; the reuse MECHANISM is the PROMOTE arm, picked by the build orchestrator under the blanket delegation — see the attribution below)*

**RECOMMENDATION: a sibling `_shared/ticket_file.py`** that **reuses** `_slugify` and the number-scanning helper from `_shared/bug_file.py` — **the reuse MECHANISM was left open here and is answered below by the PROMOTE arm** — and carries its own `_format_ticket` and `file_ticket`. **`_shared/bug_file.py` gains no format branch, no `type=` parameter and no new caller-facing behavior** — under the promote arm it gains exactly **two** behavior-preserving private-helper renames and nothing else.

**Reasoning.** The two formats genuinely differ — different fields, different status vocabulary, no `## Fix Notes`, no `## Related Issues` batch cross-linking (a ticket run writes exactly one file). A `type=` parameter threading through `_format_bug` would branch roughly half that function's body. **And the decisive ground is risk, not elegance: `bug_file.py` is the write path for `/devforge:verify` Phase 9 triage, `/devforge:report-bug` and `/devforge:fix`'s cold close, and plan 88's consumer e2e has never run.** Widening it to serve a fourth caller puts an unvalidated lane under a fresh edit.

⚠ **The scan helper is currently named with a leading underscore** (`_scan_highest_bug_number`, fact 4). **Importing a private name across modules inside the same package is a real style question the build must answer explicitly** — either promote it to a public name in the same commit, or copy the four-line scan. **Do not import the underscored name silently.**

**ANSWER — the PROMOTE arm, and the attribution is part of the answer.** ⚠ **The blanket directive that closed Phase 0 supplied no arm for this fork, because this section offered none to ratify: it named two arms and required only that one be chosen.** **The pick was therefore made by the BUILD ORCHESTRATOR on 2026-09-04 under that blanket delegation — it is not a maintainer per-item pick, and no summary may report it as one.** The reasoning, recorded so the pick is re-openable:

- **Single owner beats a copy that drifts.** This repo's own style resolves shared behavior through one owner — `_shared/memory.py` owns the memory path literal and its probe, `_shared/feature_alloc.py` owns `TICKET_RE` and `normalize_ticket` (fact 6). **A copied scan lets `bugs/` and `tickets/` numbering rules diverge silently**, which is the failure class the single-owner style exists to prevent.
- **The rename is behavior-preserving and test-pinned.** Nothing about the scan changes; the existing tests over `bugs/` numbering keep asserting the same behavior through the new name.
- **The SAME rule extends to `_slugify`** — also underscored (fact 4), also shared, also a place where ticket and bug slugs could drift apart. **It is promoted in the same commit on the same ground.**

⚠ **The accepted cost, stated as a WIDENING of what this section previously recorded.** The bound above originally said the promote arm costs `_shared/bug_file.py` **one** private-helper rename; extending the rule to `_slugify` makes it **two** — plus their internal-caller updates inside that module and the test references that name them. **That is a widening of the recorded cost, not a restatement of it**, and it is what the promote arm buys the single-owner guarantee with. **Nothing else in `_shared/bug_file.py` moves.**

### OQ-2 — Does `/devforge:verify` Phase 9 triage ever write to `tickets/`? *(ANSWERED 2026-09-04 — as recommended: NO)*

**RECOMMENDATION: NO.** Triage findings are defects by construction — they come from acceptance criteria that failed and mechanical checks that did not pass. **Routing any of them to a non-defect drawer would need a classifier that does not exist**, and would make the triage step's output ambiguous about which drawer to look in. **`/devforge:verify` is untouched by this plan.**

### OQ-3 — Numbering: shared with `bugs/`, or its own sequence? *(ANSWERED 2026-09-04 — as recommended: its OWN sequence)*

**RECOMMENDATION: its OWN sequence**, scanned from its own directory, so both directories start at `001`. Sharing would require a scan across two directories — new logic in a shared writer OQ-1 declines to touch — to buy a global uniqueness nobody needs. **`tickets/001-*.md` and `bugs/001-*.md` coexisting is unambiguous because the directory is part of every reference.**

⚠ **One consequence, stated so it is not discovered later**: a reference written as bare `001` is now ambiguous. **Every emitted sentence names the directory** — `tickets/NNN-<slug>.md`, never `NNN-<slug>.md`.

### OQ-4 — Does a ticket file's `**Ticket**:` ID satisfy `REQUIRE_TICKET` automatically? *(ANSWERED 2026-09-04 — as recommended: NO, it only pre-offers)*

**RECOMMENDATION: NO.** The ID **pre-offers** at Step 4.1 (D4 part 4) and does nothing else. `read_require_ticket` and `normalize_ticket` are untouched, `allocate-feature-dir`'s `--ticket` still comes from **the user's answer** to question 2, and a run that pre-offers an ID the user then declines allocates with no ticket.

**Reasoning.** `REQUIRE_TICKET` is plan 91's opt-in discipline mechanism, and its whole value is that a human named the ticket for **this feature**. **An ID auto-satisfying the requirement from a file written weeks earlier converts a per-run commitment into a stored default** — and plan 91's 2026-08-31 ruling refused a comparable conversion when it declined to make the ticket structurally mandatory, on the ground that it would silently reverse that plan's own OQ-1. **The pre-offer saves typing; it does not answer.**

### OQ-5 — Git disposition of `tickets/` *(ANSWERED 2026-09-04 — as recommended: tracked, by adding nothing anywhere)*

**RECOMMENDATION: tracked, exactly parallel to `bugs/`, and NOTHING is added anywhere to make that true.** Verified (fact 14): `src/files/devforge.gitignore` lists only `.devforge/` paths, so `bugs/` is ordinary tracked content; `install.sh` contains no `bugs` string at all; and the directory is created lazily by `os.makedirs` on the first write. **`tickets/` inherits all three properties by doing nothing** — no gitignore entry, no installer change, no `.gitkeep`.

⚠ **Two findings surfaced while verifying this, neither owned by this plan.** **(a) `DEVELOPMENT-STATUS.md:69` says install ships an empty `bugs/` with a `.gitkeep`**, and the only `gitkeep` token in any `*.sh` is an unrelated comment about `docs/`. **Pre-existing and false as written; recorded, not fixed here.** **(b) `/devforge:report-ticket` will make no git commit** (mirroring fact 15), so a captured ticket sits uncommitted in the working tree until a human commits it — **which is the existing behavior for bug files and is stated in the emitted text rather than left to inference** (OQ-7).

### OQ-6 — How does a pasted body reach the helper? *(ANSWERED 2026-09-04 — as recommended: `--body-file <path>`, `-` reads stdin, NO inline `--body`)*

**RECOMMENDATION: `--body-file <path>`, with `-` reading stdin — never a Bash argument.**

⚠ **This is the sharpest unaddressed hazard in the original brief and it deserves the space.** The docs confirm `$ARGUMENTS` *"always expands to the full argument string as typed"*, so a pasted tracker body reaches the command intact. **What happens next is the problem:** the orchestrator's only route to the helper is a Bash tool call, and a pasted ticket body routinely contains backticks, `$(...)`, `$VAR`, embedded quotes and newlines. **Inside a double-quoted shell argument, backticks and `$(...)` are command substitution.** The realistic outcomes are a mangled body, a broken command, or an executed fragment of somebody's ticket text.

**The house already solved this twice** (fact 16): `implement_helper` reads a verdict *"from `--verdict-file <path>` or stdin"*, and `verify_helper` documents *"Pass `-` to read from stdin"*. **This plan copies that, and the emitted spec instructs the orchestrator to write the pasted body to a scratch file and pass its path** — so the body crosses no shell boundary as an argument.

**The alternative — `--body "<text>"` with a warning to quote carefully — is REJECTED**, and not on style: a rule whose compliance depends on the model correctly escaping arbitrary user-pasted text is unfalsifiable, and **"quote carefully" is the escape-hatch shape the zero-escape-hatch policy forbids.**

⚠ **Ratify this one explicitly.** It changes `write-ticket`'s argument surface, so a Phase 0 that nods past it hands the decision to whoever writes Phase 1, at the point where the inline form is cheapest to code.

### OQ-7 — Does `/devforge:report-ticket` commit the file it writes? *(ANSWERED 2026-09-04 — as recommended: NO)*

**RECOMMENDATION: NO — mirror `/devforge:report-bug` exactly.** It writes one file, prints the path, gives a forward pointer and stops; the file is left in the working tree for the user to commit (fact 15). **`artifact_helper commit-artifacts` is not called**, which also keeps this lane outside plan 87's language-guard coverage — **a bound to state, not to close here**, since that guard rides `commit-artifacts` only and already misses `wip-commit` by plan 87's own recorded scope.

**The alternative — commit the ticket file immediately — is REJECTED for v1**: it would make a capture command a repository mutator, and the one command in this repo that commits its own artifacts on write does so because a pipeline stage depends on them surviving. **Nothing depends on a ticket file surviving the turn.**

---

## Phase 0 close record

**Ratified 2026-09-04 by the maintainer, in-session, with a SINGLE BLANKET DIRECTIVE** — verbatim, in Ukrainian: *«ратифікую. Розробляй по флоу»* (*"I ratify. Build per the flow."*). **Every item — D1–D7 and OQ-1–OQ-7 — is ratified AS RECOMMENDED.** No item was amended, deferred or declined except where a decision's own recommendation was to decline (D1's alternatives (a)–(d); D2's three; D3's three; D4's four; D5's three; D6's three; D7's three; OQ-2's, OQ-4's, OQ-6's and OQ-7's rejected arms) — **those declines ARE the recommendation, not a departure from it.**

⚠ **What this closure is, stated plainly rather than dressed up: ONE directive, not fourteen deliberations.** The maintainer supplied no per-item reasoning, and **this record does not manufacture any.** The arguments standing behind each answer are the ones already written in the decision bodies above — they were ratified, not re-derived, and **nothing in this closure adds evidence to any of them.** *(Precedent: plan 91's Phase 0, closed 2026-08-28, and plans 92's and 94's, both closed 2026-09-03 — each by a single blanket directive, and each recording the blanket form rather than implying per-item argument.)*

**The five explicit picks, as answered — written answers, because Phase 0's own Verify demands them and an inherited nod is not one:**

| Pick | Answer |
|---|---|
| **D2's name** | **`tickets/`, WITH the mandatory disambiguation rule.** The `backlog/` arm is not taken. `storage-rules.md` carries the two senses explicitly — **"ticket ID"** = the tracker identifier of shape `^[A-Z]+-[0-9]+$`, **"ticket file"** = `tickets/NNN-<slug>.md` — and every emitted sentence uses one of the two full phrases, never a bare "ticket" |
| **D3's field set** | **The six fields and the three status values exactly as tabled** — `**Status**` (`Open` / `In Progress` / `Done`), `**Type**`, `**Source**`, `**Ticket**`, `**Reported**`, body — **plus the H1 rendering element (`# Ticket NNN: [Short Title]`, fed by an optional `--title`), which sits OUTSIDE the six-field count** and is the value D4 part 2 reads as its topic seed |
| **D6's amendment** | **RATIFIED — the one-clause amendment to the conversational offer's third arm.** The discriminator, the three arms and plan 88's rubric text are otherwise byte-unchanged, and no forward pointer is added to `/devforge:report-bug` |
| **OQ-6's argument surface** | **`--body-file <path>`, with `-` reading stdin. NO inline `--body`.** The pasted body crosses no shell boundary as an argument |
| **OQ-1's reuse mechanism** | **The PROMOTE arm** — ⚠ **and this one was NOT answered by the directive.** OQ-1 offered two arms and recommended neither, so **the build orchestrator picked it on 2026-09-04 under the blanket delegation.** `_scan_highest_bug_number` **and** `_slugify` are promoted to public names in the same commit; the reasoning and the widened cost are recorded at OQ-1 itself. **It is not a maintainer per-item pick and no summary may report it as one** |

**What ratification did NOT change — recorded so a future session does not read closure as scope growth:**

- **Every alternative and every honest bound survives verbatim.** D1's two bounds, D2's unenforced prose rule, D3's three, D4's three, D5's permanently-stale-ticket bound, D6's advisory-not-a-gate bound and D7's nothing-verifies-a-reader bound are **accepted costs, not answered ones.** **Phase 0's own Verify requires this**, and none was deleted.
- ⚠ **Three costs were ratified WITH their bounds and must not be re-read as discharged.** **(a) Nothing links a ticket file to the feature directory a later run allocates from it** (D5) — a project can work a ticket and leave its file reading `Open` forever, and that is the design. **(b) The filing decision is human or advisory-model judgment** (D1 bound (i), D6's bound) — nothing mechanical routes an item to the right drawer. **(c) A 17th model-invocable command's `description` is permanent always-on context in every install** (D3 bound (i)).
- **The evidence base is unchanged: ONE maintainer request plus four mechanical facts.** ⚠ **Ratifying a request does not upgrade it into a finding**, and no summary of this plan may imply a consumer incident.
- **The scope tripwire holds.** Zero gates, zero new `verify-*` numbers, zero hard-fail validators; Python confined to D7's list. **A phase that needs more has crossed its own boundary.**
- **Phase 5 is NOT cleared.** It is a deferred user-driven HARD GATE with five known-answer anchors, **anchors 2 and 3 scored as a PAIR**. **Everything Phases 1–4 produce will be build-verified and NOT consumer-validated.**

---

## Phases

### Phase 0 — Ratification *(doc-only)* — **CLOSED 2026-09-04**

**Objective:** ratify or amend D1–D7 and answer OQ-1–OQ-7, recording each answer in this file with its reasoning. **Nothing else may start.**

**Five items need an explicit pick rather than a nod**, because each has a named fork whose arms lead to different builds:

- **D2's name.** `tickets/` with a disambiguation rule, or `backlog/` without one. **The two arms produce different directory names in nine or more emitted sentences**, and a build that discovers the fork mid-flight will pick whichever it typed first.
- **D3's field set.** The six fields and the three status values are ratified **here**, not at build. **A field added later is a schema change to files already written.**
- **D6's amendment to plan 88's rubric.** It is the only byte this plan proposes to change in a shipped, not-yet-consumer-validated lane. **A ratifier who declines it gets a capture command the model rarely offers**, which is a legitimate arm and must be picked knowingly.
- **OQ-6's argument surface.** `--body-file` / stdin, or an inline `--body`. **This decides whether a pasted body can be corrupted by shell parsing**, and it is cheapest to get right before Phase 1 exists.
- **OQ-1's private-name import.** Promote the scan helper to a public name, or copy the scan. **Either was acceptable at drafting time, and the PROMOTE arm was taken — see OQ-1's ANSWER**; silently importing an underscored name across modules was never one of the arms.

**⚠ One question Phase 0 CANNOT answer**, and it must not pretend otherwise: **whether anyone will actually file tickets.** There is no incident, no usage data and no measurement (`## Evidence constraint`). **A clean Phase 5 shows the lane works; it never shows the gap cost anything.**

**Verify:**

- `grep -n "^### D[1-7] " 95-TICKET-CAPTURE-LANE-PLAN.md` returns seven lines and **every one carries a ratification marker with a date.**
- `grep -n "^### OQ-[1-7] " 95-TICKET-CAPTURE-LANE-PLAN.md` returns seven lines, each with a recorded answer.
- **Every decision still carries its alternatives AND its honest bound.** A ratified decision whose bound was deleted cannot be re-opened honestly.
- The status line at the top names the ratification date and which phases are cleared.
- **The evidence split survives ratification**: one maintainer request plus four mechanical facts. **A Phase 0 that upgrades the request into a finding has changed the evidence base and must say where the finding came from.**
- **D2's answer is recorded as a NAME, spelled out**, and every later phase uses that name and no other.
- **The five explicit picks each have a written answer**, not an inherited nod.

### Phase 1 — The Python surface and the three roster registrations *(Python)*

**Route: python-engineer → python-reviewer, test-first, tests written AND RUN in the same turn.** House rule, no exceptions for size.

**Step 0 — read before writing.** Read `_shared/bug_file.py` and `_report_bug/_cli.py` in full. **The atomic-write convention, the scan-once numbering rationale, the word-boundary slug truncation and the exit-code contract are all load-bearing and none is obvious from a signature.**

**Deliverables:**

1. **`_shared/ticket_file.py`** — `file_ticket(tickets_dir, item, date, source)` writing one `tickets/NNN-<slug>.md` in the D3 format, atomic (`mkstemp` + `os.replace`), directory created on write, numbering scanned once from its own directory (OQ-3). **Reuses the slug and scan helpers per OQ-1's ratified arm.**
2. **`_report_ticket/`** — `__init__.py` plus `_cli.py` carrying `preflight` (resolve the workspace fail-soft, print `{tickets_dir, root, is_wrapper}`, **always exit 0**) and `write-ticket` (validate, write, print the path array; exit 0 / 2 / 1), built on `_SUBCOMMAND_REGISTRY`'s documented three-step extension pattern. ⚠ **`write-ticket`'s body argument is OQ-6's ratified shape, and it is the one place this helper deliberately diverges from its sibling: `--body-file <path>`, with `-` reading stdin. There is NO inline `--body`.** A build that adds one has re-opened OQ-6 by omission.
3. **`report_ticket_helper.py` + the POSIX `report_ticket_helper` shim**, the shim byte-shaped like its sibling and **shipped with its executable bit set**.
4. **The `**Ticket**` validation** — `normalize_ticket` **imported** from `_shared/feature_alloc.py`. ⚠ **The regex is not re-declared anywhere.** An invalid value exits 2 naming the expected shape; an absent value writes `(none)`.
5. **The three roster registrations** (D7): `_PROMOTED`; `DISPOSITIONS` with a `NOT_APPLICABLE` entry and a reason in the voice of `report-bug`'s; `HELPER_STEMS`. **Plus the five count updates**: `len(DISPOSITIONS) == 20` → 21, `test_live_repo_matches_the_20_known_names` (name and assertion), the two `_profile` assertions, and `memory_lane.py`'s prose numerals and `# ---- N/A (7)` comment.

**Verify:**

- python-reviewer clean; the full `tests/lib` suite green; `tests/scripts` green.
- **Every new function has its own test that RAN**, and the writer's test round-trips through `write-ticket` rather than a hand-authored fixture.
- **`scripts/verify-memory-lane.py` passes**, and its failure mode was **observed first**: run it after appending to `_PROMOTED` and before adding the disposition, and record that it failed. ⚠ **An unobserved gate is indistinguishable from an absent one.**
- **`python3 scripts/emitters/claude.py --list` prints 21 names** with the new one present.
- **`scripts/verify-agent-reachability.py` passes** — this plan adds no agent, so a failure means something unintended moved.
- **A test proves a body containing a backtick and a `$(` sequence round-trips BYTE-IDENTICAL** through `write-ticket --body-file`, and a second proves it does so through `-` on stdin. ⚠ **This is OQ-6's whole point reduced to an assertion**, and it is the build-time twin of Phase 5's anchor 2.
- **A test proves a ticket file with an invalid `**Ticket**` value exits 2** and writes nothing.
- **A test proves the numbering is independent**: a populated `bugs/` does not shift the first ticket off `001`.
- **`git diff --stat` shows zero changes under `src/commands/` and `src/devforge/storage-rules.md`** — those are Phase 2.
- **The counted roster numbers are stated in the commit message**, counted live, never incremented from this document.

⚠ **Dated note, 2026-09-04 — two of the criteria above MOVED, and the criteria themselves are left as written rather than edited.** The `verify-memory-lane` **observed-failure-first** bullet and the **`--list` prints 21** bullet both presuppose deliverable 5, which did NOT land in this phase (build-record divergence 1). **They are Phase 2b's to satisfy, with the registrations**, and they are scored there. **Every other criterion above was scored in this phase.**

**This phase appends a `#### Phase 1 build record` block** carrying what landed, every divergence with its reason, and the reviewer findings by severity.

#### Phase 1 build record — 2026-09-04

**Route as specified: python-engineer → python-reviewer, test-first.** ⚠ **This block records a BUILD, not a consumer observation.** Nothing below was run on a real install.

**What landed:**

1. **`_shared/ticket_file.py`** — `file_ticket(tickets_dir, item, date, source)` plus `_format_ticket` and `_resolve_title`. Atomic `mkstemp` + `os.replace`, `makedirs(..., exist_ok=True)`, **own-sequence numbering (OQ-3)** through the promoted `scan_highest_number`, slug through the promoted `slugify`.
2. **`_report_ticket/__init__.py` + `_cli.py`** — `preflight` (fail-soft, prints `{tickets_dir, root, is_wrapper}`, resolves `<install_root>/tickets` in BOTH modes, **always exit 0**) and `write-ticket` (`--tickets-dir` / `--date` required; **`--body-file <path>` with `-` reading stdin and NO inline `--body`, per OQ-6**; `--title` optional; `--type` required over `enhancement | task | imported`; `--source` optional, default `manual`, over `manual | paste`; `--ticket` through the imported `normalize_ticket`, invalid → exit 2, absent → `(none)`). **Exit 0 / 2 / 1, and an exit-2 writes nothing.**
3. **`report_ticket_helper.py` + the POSIX `report_ticket_helper` shim**, the shim reported as shipped executable (`-rwxr-xr-x`). ⚠ **The mode is recorded as the build reported it and was not independently re-checked when this block was written** — a file mode is not readable through the tools that wrote this record. **Re-check it at Phase 2b**, where the emitter first depends on the pair.
4. **OQ-1's PROMOTE arm executed.** `_shared/bug_file.py`: `_scan_highest_bug_number` → **`scan_highest_number`** (its body is directory-generic, which is why the promoted name drops `bug`) and `_slugify` → **`slugify`**; every caller and test reference updated; **behavior byte-identical**; a provenance note added to the module docstring. **This is exactly the two-rename cost OQ-1's ANSWER recorded, and nothing beyond it.**
5. **Tests — 70 new**, 25 in `test_ticket_file.py` and 45 in `test_report_ticket_helper.py`, including: the **byte-identical round-trip of a body carrying a backtick and `$(`, through BOTH `--body-file` and `-` on stdin**; a CRLF round-trip; invalid-ticket **exit-2-writes-nothing**; both vocabulary rejections; numbering independence from a populated `bugs/`; title fallback; and an explicit `--ticket ""` rejection. **Suite results: `tests/lib` 11628 passed / 16 skipped / 0 failed; `tests/scripts` 31 passed; `verify-agent-reachability` PASS; `verify-memory-lane` PASS.** ⚠ **That last PASS is VACUOUS with respect to `report-ticket`** — the reviewer's word, quoted deliberately — because nothing is registered yet, so the gate had nothing about this command to check.

**Divergences, each with its reason:**

1. ⚠ **THE BIG ONE — deliverable 5 (the three roster registrations and the five test-pin updates) did NOT land in this phase**, by orchestrator scope amendment. **The mechanism:** `tests/scripts/test_claude_emitter.py::test_full_emit_when_only_is_none` runs `emit()` against **LIVE `src/`** and asserts every `_PROMOTED` name appears in the emitted set, while `emit()` **silently `continue`s** on a name whose `src/commands/<name>/` does not load. **So registering before Phase 2 ships `src/commands/report-ticket/main.md` turns the suite red.** ⚠ **The plan's own Phase 1 Verify was internally contradictory on exactly this point** — it demanded both *"`tests/scripts` green"* and *"zero changes under `src/commands/`"*, which deliverable 5 cannot satisfy together. **Resolution: the registrations land as a dedicated Python step — Phase 2b — immediately after Phase 2, and the observed-gate-failure ritual is executed THERE** (append to `_PROMOTED`, run `scripts/verify-memory-lane.py`, record that it failed, then add the disposition). **Stated plainly, because it is the state a fresh session will find: until Phase 2b lands, `report_ticket_helper` is ORPHANED — complete, tested, and reachable by nothing.** Confirmed at the time of writing: `report-ticket` appears in none of the three rosters. **This is python-reviewer finding 1 (High), deferred on this recorded reasoning rather than dismissed.** ✅ **CLOSED 2026-09-04 by Phase 2b, which registered all three rosters and whose reviewer explicitly closed this finding.** ⚠ **The paragraph above is deliberately NOT rewritten** — it records the state this phase shipped and the reason it was acceptable, and a fresh session needs that reasoning intact to understand why an orphan was ever allowed to exist.
2. **Title fallback is the FIRST NON-EMPTY LINE of the body, not the whole body.** An H1 rendered from a multi-paragraph pasted ticket would be absurd; this mirrors the spirit of `report-bug`'s title-defaults-to-description without inheriting its whole-value behavior. **A third fallback exists** — a body that is empty or whitespace-only yields the literal `Untitled ticket`, mirroring `_format_bug`'s own `Untitled bug`.
3. **An empty or whitespace-only body exits 2 and writes nothing.** Not in the plan text; it mirrors the sibling's required non-empty `--description`.
4. **`ticket_file.py` unifies the title and slug source through one `_resolve_title`.** `bug_file.py`'s pre-existing two-literal split was left untouched — **the promote arm's "and nothing else" bound holds.**

**Reviewer findings by severity, with dispositions:**

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | **High** | The three roster registrations are missing, so the helper is unreachable | **DEFER — re-scoped to Phase 2b** on divergence 1's recorded reasoning. **Not dismissed**, and the orphan state is stated in this record so it cannot be mistaken for completion |
| 2 | **Medium** | CRLF universal-newline translation on the `--body-file` read path, where the stdin path did **not** translate — a route-dependent, undocumented difference in what got written | **FIXED** (`newline=""`). ⚠ **And the fix surfaced a SECOND latent instance of the same class** in the test helper `_read_first_ticket()`, also fixed — **recorded explicitly because it is the review catch earning its keep: one reported symptom, two real sites** |
| 3 | **Low** | The promoted `slugify` falls back to the literal `"bug"`, so a symbol-only ticket title lands at `tickets/NNN-bug.md` | **OWNED RESIDUAL — not built.** OQ-1's ANSWER closed at *"and nothing else"*, and an additive `fallback=` parameter would be a third change beyond the ratified cost. **A natural pair with D2's disambiguation concern** — a ticket file named `bug` is precisely the collision D2 exists to prevent — and the right home is a future plan, not this one |
| 4 | **Nit** | Four test method names still carried the old private helper names as labels | **FIXED** (renamed) |
| 5 | **Nit** | `cmd_write_ticket`'s docstring enumerated the exit-2 cases but omitted the empty-body case | **FIXED** |

**Independently re-verified when this record was written** (not taken on report): the two promoted public names exist in `bug_file.py` and neither underscored name survives as a definition; `ticket_file.py` carries `file_ticket` / `_format_ticket` / `_resolve_title`; `_cli.py` carries `--body-file`, `newline=""`, both vocabulary tuples and the empty-body exit-2; `_resolve_title`'s first-non-empty-line rule; both launcher files exist; and **`report-ticket` is absent from `_PROMOTED`, `DISPOSITIONS` and `HELPER_STEMS`**, which is what makes divergence 1's orphan statement a fact rather than a forecast.

### Phase 2 — The command spec and the storage contract *(instruction-only)*

**Route: instruction-author → instruction-reviewer, plus `claude-code-guide` for this phase's own surface.** `src/commands/report-ticket/main.md` is emitted into `.claude/commands/devforge/` — **a Claude-Code-integration surface, so the pass is owed with no frontmatter carve-out.**

Scope:

- **`src/commands/report-ticket/main.md`** — mirroring `/devforge:report-bug`'s structure section for section: frontmatter (`name`, `description`, `argument-hint`, `allowed-tools`), the overview paragraph, **`## Maintainer note`** (the SSOT sentence, adapted), `## Outputs of this command`, `## Helper interaction model`, the phases, and `## Important rules`. ⚠ **The `description` honours plan 63 OQ-1's ≈40-word budget** (D3's bound (i)). ⚠ **No `disable-model-invocation` line** (D3, D7). ⚠ **The phase that dispatches `write-ticket` does NOT mirror `/devforge:report-bug`'s inline `--description`: the body travels as `--body-file <path>` (or `-` on stdin) per OQ-6**, so this spec instructs the orchestrator to write the captured body to a scratch file and pass its path. **The divergence is deliberate and the spec says why** — a pasted body inside a shell argument is subject to command substitution.
- **`src/devforge/storage-rules.md`** — a `## Ticket Capture Rules` section modeled on `## Bug Report Rules` (Directory / Naming / Status Lifecycle / Ticket File Format / Field notes / How Ticket Files Are Created / How Ticket Files Are Resolved), **the D2 disambiguation rule**, one `## File Lifecycle` line (`report-ticket → creates tickets/NNN-description.md`), and one `## Directory Structure` tree entry beside `bugs/`.

**Verify:**

- Instruction-reviewer clean; **`claude-code-guide` invoked for this surface and its answers RECORDED.**
- **Every sentence about the helper uses setter/getter language** — the helper owns the structure, numbering, validation and atomic write; the orchestrator composes values and supplies the date. **No sentence tells the orchestrator to compose a number, a slug or a file path.**
- **The emitted text says the lifecycle is manual and names no mechanical writer** (D5's bound).
- **The emitted text carries the discipline-not-verification statement** for the `**Ticket**` field, in plan 91's voice.
- **`git grep -n "tickets/" src/` shows exactly three groups and nothing else**: **Phase 1's FOUR library files**, which already carried the literal before this phase began — `src/devforge/lib/_shared/ticket_file.py`, `src/devforge/lib/_report_ticket/_cli.py`, `src/devforge/lib/report_ticket_helper.py` (its module docstring) and ⚠ **`src/devforge/lib/_shared/bug_file.py`, the one an enumeration keeps missing** (the promote-arm provenance note plus `scan_highest_number`'s own docstring, both naming `tickets/` as the sibling directory); this phase's `src/commands/report-ticket/main.md`; and this phase's `src/devforge/storage-rules.md` sites — **and no hit under `src/commands/research/`**, because Phase 3's edits have not started.
- **No plan vocabulary in emitted text** — "D3", "OQ-6" and this plan's number are maintainer vocabulary. Emitted text names only commands, files and behaviors.
- **The `description` is counted in words and the count is stated in the commit message.**
- **The frontmatter contains no key outside the four named**, and the `name:` line's inertness (fetched docs) is not contradicted by any sentence.

#### Phase 2 build record — 2026-09-04

**Route as specified: instruction-author → instruction-reviewer, plus `claude-code-guide`.** ⚠ **Instruction-only — no Python, no test, and nothing here has been observed on a real install.**

**What landed:**

1. **`src/commands/report-ticket/main.md`** — 133 lines, mirroring `/devforge:report-bug` section for section: frontmatter, overview, `## Maintainer note`, a two-senses-of-"ticket" section, `## Outputs of this command`, `## Helper interaction model`, four phases (PHASE 3 split into 3.1 staging and 3.2 writing), and `## Important rules`. **Frontmatter carries exactly four keys** — `name`, `description`, `argument-hint`, `allowed-tools` — with **no `disable-model-invocation` line**, which is what makes the command model-invocable. **`allowed-tools` is a YAML list of four entries**: `Read`, the two `Bash(.devforge/lib/report_ticket_helper <verb> *)` globs, and `Write`. **The `description` is 37 words, counted**, inside the ≈40-word budget.
2. **`src/devforge/storage-rules.md`** — three insertions and nothing else: a `tickets/` entry in the `## Directory Structure` tree beside `bugs/`, one `## File Lifecycle` line (`report-ticket → creates tickets/NNN-description.md`), and a `## Ticket Capture Rules` section before `## Cleanup Rules` carrying **the disambiguation rule** (ticket ID vs ticket file, stated first and prominently), Directory / Naming / Status Lifecycle / Ticket File Format / Field notes / How Ticket Files Are Created / How Ticket Files Are Resolved. **The format block mirrors `_format_ticket`'s field order byte-for-byte** — H1, blank, `**Status**` / `**Type**` / `**Source**` / `**Ticket**` / `**Reported**`, blank, bare body — with no `Fixed` line, no severity, and no `## Description` wrapper, because the writer renders none.

**The `claude-code-guide` pass is RECORDED, as this phase's Verify requires.** Its answers **confirmed the surface this plan had already fetched** and changed no decision: the combined `description` + `when_to_use` listing text is truncated at **1,536 characters**; a YAML-list `allowed-tools` carrying `Bash(...)` glob patterns is current; **`disable-model-invocation` has no positive form**, so omitting it is the only way to be model-invocable; `name` is **ignored** in a command file; and `$ARGUMENTS` expands to the full multi-line argument string as typed. **Separately, the reviewer ran its own live permissions-doc fetch on the `Write` grant and confirmed bare `Write` is the correct form** — a scoped `Write(path)` rule is documented as **accepted but never consulted**, so scoping the grant would have produced a rule that reads as a restriction and enforces nothing. **Bare `Write` is therefore the honest form, not the lazy one.**

**Divergences, each with its reason:**

1. **`## Important rules` carries TEN rules, not `/devforge:report-bug`'s eight.** The two extra exist because this command has two concerns its sibling does not: **shell-safety of the body** (rule 6 — the body never crosses a shell argument) and **the two-senses vocabulary** (rule 9 — say "ticket ID" or "ticket file", never a bare "ticket"). **Mirroring the sibling's count would have meant dropping one of them**, and both are load-bearing.
2. **`Write` was added to `allowed-tools` mid-phase**, on the author's recommendation and the orchestrator's acceptance, after the file was first written with the three-entry list. **The reasoning is recorded because the alternative was tempting and wrong:** a quoted heredoc (`<<'EOF'`) would have avoided the grant entirely, but its correctness depends on the model choosing the quoted form over the unquoted one for arbitrary pasted text — **the unfalsifiable-compliance shape the body-file decision exists to refuse.** Without the grant, staging the body prompts for permission on every capture, which pushes a future session toward exactly that heredoc. `PHASE 3.1` now states the grant, so the frontmatter and the instruction agree in writing.
3. **A scratch-diagnostic limitation is disclosed rather than engineered away** (reviewer finding 2). Cleanup fires on success only, so a failed run's staged body survives — **but the scratch path is fixed, so the next invocation overwrites it.** Both sentences say so; making the path unique per run was considered and declined as scope this phase does not own.

**Reviewer findings — 0 high, 0 medium, 2 low, 2 nit — with dispositions:**

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | Low | `"pasted tracker text"` at one site drifted from the established `"pasted tracker-ticket text"` compound | **FIXED** |
| 2 | Low | The scratch file's diagnostic value is bounded by a fixed path and success-only cleanup, and the spec did not say so | **FIXED** — one sentence in PHASE 3.2 and one beside the removal instruction |
| 3 | Nit | The new `## File Lifecycle` line's arrow sits one column off the block's 13-character padding | **SKIPPED — accepted cosmetic.** Re-padding the whole block would put diff noise across a shared file for an alignment nobody reads mechanically |
| 4 | Nit | `"tracker ticket"` appears as a qualified third compound beside "ticket ID" and "ticket file" | **SKIPPED — no ambiguity.** The qualifier names the tracker's own object, and the two-senses framing is about the framework's two uses; a third rule would over-specify prose that already reads correctly |

**Verify-grep results, as run:**

- **`git grep -n "tickets/" src/` → six files**, matching the (corrected) Verify enumeration: Phase 1's four library files, this phase's `report-ticket/main.md`, and this phase's `storage-rules.md`. ⚠ **The enumeration in that Verify bullet was WRONG when this phase started** — it named two Phase 1 files where there are four — and was corrected during this phase rather than scored as a pass against a false expectation.
- **No hit under `src/commands/research/`** — Phase 3 has not started.
- **`## Bug Report Rules` is byte-intact**, and the `declared memory disposition` sentence was not touched.
- **No plan vocabulary in either file this phase wrote.** (`storage-rules.md`'s four pre-existing plan citations sit in the `.devforge/` disposition section, untouched.)

**Residuals recorded, none fixed here:**

1. **Five pre-existing bare-"ticket" sentences from the feature-directory work** live elsewhere in `storage-rules.md` and are now technically at odds with the disambiguation rule this phase added. **Out of scope** — the rule is prescriptive for new writing and makes no claim about the existing file. A future pass may reconcile them.
2. **The `## File Lifecycle` one-column misalignment** (finding 3), accepted above.
3. ⚠ **The standing Phase-4 transient**: `storage-rules.md`'s `declared memory disposition` sentence still reads **20 emitted commands / 13 `READS` / 7 `N/A`**, which Phase 2b's registrations will falsify and Phase 4 corrects. **Recorded here so a reader between those phases does not treat it as a fresh defect.** ✅ **CLOSED 2026-09-04 by Phase 4 — the sentence now reads 21 / 13 `READS` / 8 `N/A`, checked against the live dict. The wording above is kept as the record of the window, not as a description of the tree.**

### Phase 2b — Roster registrations *(Python)*

**Route: python-engineer → python-reviewer.**

**Why this section exists, in one sentence:** deliverable 5 could not land in Phase 1 because `emit()` silently skips a `_PROMOTED` name whose command source does not yet exist while a live-`src/` test asserts every promoted name is emitted — **see the `#### Phase 1 build record`'s divergence 1 for the mechanism** — so the registrations run **strictly AFTER Phase 2's `src/commands/report-ticket/main.md` has landed**, and not before. ⚠ **Until this phase lands, `report_ticket_helper` is orphaned: complete, tested, and reachable by nothing.** ✅ **CLOSED 2026-09-04 by this phase — the sentence above is kept as the record of the state Phase 1 left behind, not as a description of the tree.** All three rosters now carry `report-ticket`; see the `#### Phase 2b build record`.

**Deliverables:**

1. **The three registrations.** `scripts/emitters/claude.py`'s `_PROMOTED` gains `"report-ticket"`; `scripts/lib/memory_lane.py`'s `DISPOSITIONS` gains a `NOT_APPLICABLE` entry **with a reason written in `report-bug`'s voice** (pure capture, writes one file and stops, dispatches no agent, renders no judgment for memory to inform); `src/devforge/lib/_profile/_segment.py`'s `HELPER_STEMS` gains `"report-ticket": "report_ticket_helper"`. ⚠ **All three in one commit** — the first fails loudly without the second, and the third fails **silently** (D7, `## Verified mechanics` row 10).
2. **The five pin and numeral updates.** `tests/lib/test_memory_lane.py`'s `len(DISPOSITIONS) == 20` → 21; `test_live_repo_matches_the_20_known_names` — **both its NAME and its assertion**; the two `== 20` assertions in `tests/lib/_profile/test_segment.py`; and `scripts/lib/memory_lane.py`'s docstring numerals plus its `# ---- N/A (7)` group comment. ⚠ **`# ---- READS (13)` does NOT move** — the new command is `N/A`.
3. **The observed-gate-failure ritual.** Append to `_PROMOTED`, run `scripts/verify-memory-lane.py` **before** adding the `DISPOSITIONS` entry, and **record that it failed**; then add the entry and re-run. ⚠ **An unobserved gate is indistinguishable from an absent one**, which is the whole reason this ritual is a deliverable rather than a nicety.

**Verify:**

- python-reviewer clean; **full `tests/lib` and `tests/scripts` green.**
- **`python3 scripts/emitters/claude.py --list` prints 21 names** with `report-ticket` present. *(Moved here from Phase 1 — see that phase's dated Verify note.)*
- **`scripts/verify-memory-lane.py` passes NON-VACUOUSLY** — its failure was observed first per deliverable 3, so the pass is now a statement about `report-ticket` rather than about a command the gate never saw. *(Moved here from Phase 1.)*
- **The shim's executable bit is re-checked and its mode RECORDED** (`ls -l src/devforge/lib/report_ticket_helper`). ⚠ **Phase 1 recorded that mode as reported rather than verified**; this is where it is confirmed, and it matters here because the emitter first depends on the launcher pair.
- **The counted roster numbers are stated in the commit message** — 21 promoted, 17 model-invocable, 4 human-typed-only — **counted live, never incremented from this document.**
- **`git diff --stat` shows no change under `src/commands/`** — this phase touches the two `scripts/` roster files, one `src/devforge/lib/_profile/` file and two test modules.

**This phase appends a `#### Phase 2b build record` block** carrying what landed, the observed gate failure verbatim, every divergence with its reason, and the reviewer findings by severity.

#### Phase 2b build record — 2026-09-04

**Route as specified: python-engineer → python-reviewer.** ⚠ **Build-verified, NOT consumer-validated** — Phase 5 remains the only place any of this is observed on a real install.

**What landed — the three registrations, in one commit:**

1. **`scripts/emitters/claude.py`** — `_PROMOTED` gains `"report-ticket"` as its **21st** name, **appended last**, matching the tuple's own additive history.
2. **`scripts/lib/memory_lane.py`** — `DISPOSITIONS["report-ticket"]` = `NOT_APPLICABLE` with the reason written in `report-bug`'s voice: *"Pure capture — writes one tickets/NNN-slug.md and stops; dispatches no agent and renders no judgment for memory to inform."* **Placed directly after `report-bug`**, the entry it mirrors. Prose numerals updated to **21** and **"13 READS / 8 N/A"**; the group comment became **`# ---- N/A (8)`**; ⚠ **`# ---- READS (13)` is unmoved**, because the new command is `N/A`.
3. **`src/devforge/lib/_profile/_segment.py`** — `HELPER_STEMS["report-ticket"] = "report_ticket_helper"`. ⚠ **This is the roster whose omission fails SILENTLY**, and it is now registered.

**Five test pins updated:** `len(DISPOSITIONS) == 21`; `test_live_repo_matches_the_20_known_names` **renamed** to `test_live_repo_matches_the_21_known_names` with its `== 21` assertion; the two `== 20` assertions in `tests/lib/_profile/test_segment.py`; and the hardcoded `na` name list inside the disposition test, which now includes `report-ticket`.

**The observed-failure ritual, executed AND independently reproduced.** `scripts/verify-memory-lane.py` was run after the `_PROMOTED` append and **before** the `DISPOSITIONS` entry. It failed, verbatim:

```
FAIL — commands in _PROMOTED with no disposition (Rule 1a):
  - report-ticket
```

exit 1. With the disposition added it exits 0 — a **non-vacuous** pass, unlike Phase 1's, because the gate now has this command to check. ⚠ **The python-reviewer did NOT take that on trust: it re-created the intermediate state itself, observed the same failure, and restored the tree byte-identical.** **That is the difference between a recorded ritual and a performed one**, and it is why this bullet names the reviewer's reproduction rather than only the engineer's run.

**Verified live in this phase:**

- **`python3 scripts/emitters/claude.py --list` prints 21 names** with `report-ticket` present.
- **A real emit produced `.claude/commands/devforge/report-ticket.md`** in a scratch target — twice, independently: the engineer's full emit and the reviewer's `--only report-ticket` emit. **This is the assertion Phase 1 could not make**, and the reason the registrations waited for Phase 2's command source.
- **`scripts/verify-agent-reachability.py` PASS** — no agent moved.
- **The shim's mode re-checked: `-rwxr-xr-x`.** ⚠ **This discharges the check Phase 1's build record explicitly deferred here**, where the emitter first depends on the launcher pair.
- **`tests/lib` 11629 passed / 16 skipped / 0 failed** (+2 against Phase 1, from the two tests the reviewer's fixes added); **`tests/scripts` 31 passed**.
- **Counts, counted live and never incremented: 21 promoted, 17 model-invocable, 4 human-typed-only, 13 `READS`, 8 `N/A`.**

**Divergences, each with its reason:**

1. **`_segment.py`'s module docstring was updated 20 → 21**, which the deliverable list did not name. **The phase's own edit made that sentence stale**, so leaving it would have shipped a file whose docstring contradicted the dict directly beneath it. Fixed in-phase by coordinator call.
2. **The hardcoded `na` name list inside the disposition test was updated**, one step past the literal instruction to change the count. **Same test method, same fix**: incrementing the count while leaving the list short would have left the test failing, so the instruction was completed rather than obeyed to the letter.
3. **`tests/lib/_profile/test_segment.py`'s pre-63 fixture list was deliberately NOT touched.** It is a historical transcript record, and `report-ticket` **cannot appear in a pre-63 transcript** — adding it would have falsified the fixture to satisfy a pattern.

**Reviewer verdict: SHIP-READY, ZERO findings (0 high / 0 medium / 0 low / 0 nit).** ⚠ **And the Phase 1 review's finding 1 — the missing registrations, deferred as High — is explicitly CLOSED by this phase.** **`report_ticket_helper` is no longer orphaned**; the orphan sentences in the Phase 1 build record and in this phase's rationale are kept, dated and marked closed, because they record why the orphan was allowed rather than describing the tree.

### Phase 3a — The verbatim-prompt file route *(Python)*

**Route: python-engineer → python-reviewer, test-first, tests written AND RUN in the same turn.**

**Why this section exists, and why it is lettered rather than numbered:** it is a prerequisite Phase 3 discovered it needed, and lettering it keeps every downstream phase's cited number intact. **It runs BEFORE Phase 3**, despite sorting after Phase 2b.

**The mechanical discovery, verified live 2026-09-04.** `research_helper set-verbatim-prompt` accepts **only** an inline `--value`, and that option is `required=True` — there is no file route and no stdin route (grep the verb name in `src/devforge/lib/_research/_cli.py`; do not trust a line number). **So the consumer arm's "the file's body becomes the value passed to `set-verbatim-prompt`" collides head-on with its own bound (iii) and with Trap 7**: a pasted tracker-ticket body carrying a backtick or `$(` would cross a shell argument boundary, where both are command substitution.

**Why an instruction-only Phase 3 CANNOT close this — three routes, all closed:**

- **Pass the body inline anyway and instruct careful quoting.** ⚠ **Refused by the zero-escape-hatch policy**: a rule whose compliance depends on a model correctly escaping arbitrary user-pasted text is unfalsifiable, and it is the same shape the body-file decision already rejected once for `write-ticket`. Shipping it here would reverse that decision through the back door.
- **Skip `set-verbatim-prompt` for the ticket-file arm.** **Refused on consequence**: that field is what the downstream handoff carries as the user's actual words, and the suspected-cause scan reads it. An arm that silently leaves it unset makes a ticket-file run behave differently from every other run in a way nothing announces.
- **Add a new verb, or a new state key, for file-sourced prompts.** **Refused by Phase 3's own Verify**, which requires that no new helper verb and no new state key appear — and rightly: the value being stored is the same value, arriving by a different door.

**The resolution, which leaves all three constraints intact:** an **additive option on the EXISTING verb**.

**Deliverables:**

1. **`--value-file <path>` on `set-verbatim-prompt`**, with `-` reading stdin. **Mutually exclusive with `--value`, and exactly one of the two is required** — so a call that passes both, or neither, exits 2 rather than guessing.
2. **The read uses `newline=""`**, carrying Phase 1's CRLF lesson forward: a body must not be silently line-ending-translated on one route and not the other. **Empty or whitespace-only content exits 2**, matching `write-ticket`'s own empty-body refusal.
3. **Round-trip tests** proving a body carrying a backtick, a `$(` sequence and CRLF line endings is stored **byte-identical** through both the file path and stdin, plus a regression test that the existing `--value` path is unchanged.

**⚠ Three things this deliberately does NOT change, because existing callers depend on all of them:**

- **The verb name is byte-unchanged** — `set-verbatim-prompt`, as every existing call site spells it.
- **The state key is byte-unchanged** — the same `verbatim_prompt` field, written by the same code path.
- **Inline `--value` behavior is byte-unchanged** — it stays available and stays correct for callers that already use it. **This is an addition, not a migration**, and no existing caller is touched.

**Plan 75's tripwire holds, both halves:** an argparse option is neither a `verify-*` gate number nor a hard-fail validator. **Nothing new blocks anything.**

**⚠ One residual, recorded and deliberately NOT closed here.** The **pre-existing** hazard at Phase 0.3's ordinary path is untouched: an ordinary `/devforge:research "<pasted text>"` invocation still routes `$ARGUMENTS` to `--value` inline, exactly as it does today. **This phase does not widen into that flow** — the ordinary arm keeps `--value`, and only the ticket-file arm uses the file route. **That hazard predates this plan, is not caused by it, and closing it is a different change with a different blast radius**; a summary that reports this phase as having fixed the inline hazard generally has over-claimed.

**Verify:**

- python-reviewer clean; **`tests/lib/_research` green**, and the full `tests/lib` suite green.
- **A test proves a body carrying a backtick and a `$(` sequence round-trips BYTE-IDENTICAL** through `--value-file`, and a second proves it does so through `-` on stdin.
- **A CRLF body round-trips byte-identical on both routes** — the Phase-1 lesson, re-asserted where it can recur.
- **The existing `--value` path is regression-green**, with a test that asserts its stored result is unchanged.
- **Passing both flags exits 2, and passing neither exits 2** — argument-shape errors, nothing written.
- **`git diff --stat` shows `_research/_cli.py` and its tests only** — no command spec, no other helper.
- **The verb name and the state key appear in the diff only as context**, never as changed lines.

**This phase appends a `#### Phase 3a build record` block** carrying what landed, every divergence with its reason, and the reviewer findings by severity.

#### Phase 3a build record — 2026-09-04

**Route as specified: python-engineer → python-reviewer, test-first.** ⚠ **Build-verified, NOT consumer-validated.**

**What landed:**

1. **`_research/_cli.py`** — `set-verbatim-prompt`'s `--value` and the new `--value-file` sit in one **mutually-exclusive group declared `required=True`**, so argparse itself enforces exactly-one rather than the handler re-deriving it. The verb's help names both routes.
2. **`_research/_cmds_basic.py`** — `cmd_set_verbatim_prompt` reads `--value-file`, with `-` reading stdin and a real path opened `encoding="utf-8", newline=""` — **Phase 1's CRLF lesson carried forward to the second place it could recur.** An I/O error on the read is exit 1. ⚠ **Both routes funnel through the same `_validate_scalar`**, so the stored shape and the empty/whitespace-only exit-2 contract are **route-independent by construction** rather than by two parallel checks that could drift.
3. **Nothing else moved.** The **verb name**, the **state key** and **inline `--value` behavior** are byte-unchanged, exactly as this phase's "does NOT change" block required; `set-topic` was deliberately left alone.
4. **`tests/lib/_research/test_set_verbatim_prompt_value_file.py` — 11 tests, every one a real-producer subprocess round-trip** rather than a hand-authored fixture: a body carrying a backtick, a `$(` sequence and embedded CRLF stored **byte-identical via file AND stdin**, with `stored_file == stored_stdin` asserted directly so the two routes cannot diverge silently; the inline `--value` regression; both-flags and neither-flag exit 2; empty and whitespace-only content exit 2; a nonexistent path exit 1; and the explicit `--value-file ""` guard pinned to its LITERAL message.

**Verified:**

- **`tests/lib/_research` — 30 passed** (19 pre-existing + 11 new).
- **A wider sweep across every module referencing the verb — 1242 passed / 0 failed** — including the 13,660-line research monolith (572 passed).
- ⚠ **`/devforge:discover` has a SEPARATE verb of the same name**, and it is an independent implementation in `_discover/_cmds_core.py`. **It was not touched and is green** (its own 9 tests plus the discover monolith's 166). **The reviewer confirmed the independence rather than inferring it from the shared name.**

**Divergences, each with its reason:**

1. **The engineer traced every ambiguous call site individually instead of grepping the verb name.** ⚠ **The reason generalizes past this phase: `discover_helper` shares the verb NAME with a distinct implementation, so a file-level grep over `set-verbatim-prompt` MISCOUNTS** — it returns two commands' call sites as though they were one command's. **Anyone re-deriving this blast radius must trace, not grep.**
2. **An explicit `--value-file ""` became its own exit-2 message** rather than falling through to the `OSError` branch. ⚠ **Recorded precisely, because it would be easy to over-claim: this is a CATEGORIZATION improvement, not a crash guard.** `open("")` raises `FileNotFoundError`, which the existing handler already catches as exit 1 — so the empty string was always handled; it was merely reported as an I/O failure when it is an argument error. **The reviewer established that independently rather than accepting the engineer's framing.**

**Reviewer findings — 1 Medium, dispositioned:**

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | **Medium** | The `--value-file ""` guard had **zero dedicated coverage**, while an adjacent test exercised a DIFFERENT code path whose stderr text overlaps — so the guard looked covered and was not | **FIXED** — a test pinned to the guard's LITERAL message. ⚠ **Worth keeping: overlapping stderr text is exactly what makes an uncovered branch read as covered**, and only reading the assertion against the branch it names catches it |

Everything else was confirmed clean and the verdict was then discharged.

**Residual, restated so it is not lost between phases:** ⚠ **the PRE-EXISTING inline hazard on the ordinary intake path is untouched.** An ordinary `/devforge:research "<pasted text>"` invocation still routes `$ARGUMENTS` through inline `--value`. **Only the ticket-file arm uses the file route**, and closing the general case is a different change with a different blast radius. **A summary reporting this phase as having fixed the inline hazard generally has over-claimed.**

### Phase 3 — The `/devforge:research` consumer arm *(instruction-only)*

**Route: instruction-author → instruction-reviewer, plus `claude-code-guide`** — `research/main.md` is emitted into `.claude/commands/devforge/`.

Scope, all inside `src/commands/research/main.md`:

- **Phase 0.3** — the ticket-file arm: detection by path shape, `set-topic` from the title, and `set-verbatim-prompt` from the body **by the concrete route Phase 3a builds — the orchestrator writes the extracted body to a scratch file with the Write tool and passes `--value-file <path>` (or `-` on stdin), never an inline `--value`**, because a pasted tracker-ticket body inside a shell argument is exposed to command substitution. **The unconditional reset stays unconditional** and no new state is introduced.
- **The rubric sentences** — `:169` EXTENDED with a ticket-file clause; `:171`'s never-fabricate-a-user-mode rule extended so "the ticket file already answers everything" is named as a fabrication.
- **Step 4.1 question 2** — the conditional third authored option. ⚠ **Exactly three authored options when the ticket file carries an ID and exactly two when it does not; no authored "Other" in either case; the tool's own free-text row is untouched; the `(Recommended)` marker stays off every option** (fact 8).
- **`## Outputs of this phase`** — one sentence stating that a consumed ticket file is **read and never written** (D5).

**Verify:**

- Instruction-reviewer clean; **`claude-code-guide` invoked and its answers RECORDED.**
- **The rubric's mandatory per-dimension rule is intact** — `git diff` shows `:169` and `:171` **extended**, with no clause removed. ⚠ **A diff that shortens either sentence has weakened the gate this arm rides on.**
- **The AskUserQuestion contract holds**: authored options counted (3 with a ticket ID present, 2 without), no authored "Other", `(Recommended)` on neither.
- **The discipline-not-verification statement is unchanged**, byte for byte.
- **No new helper verb and no new state key appear** — the arm uses `set-topic` and `set-verbatim-prompt` only.
- ⚠ **This phase DEPENDS on Phase 3a having landed**: the arm passes `--value-file` to `set-verbatim-prompt`, and that option does not exist until Phase 3a ships it. **An instruction written against the inline `--value` would put a pasted body inside a shell argument** — the failure Phase 3a exists to prevent — so a Phase 3 that runs first has written a spec its helper cannot honour safely.
- **`git diff --stat` shows `research/main.md` and nothing else.**

#### Phase 3 build record — 2026-09-04

**Route as specified: instruction-author → instruction-reviewer.** ⚠ **Instruction-only, and it touched ONE file.** Build-verified, NOT consumer-validated.

**What landed — six edits delivering the four ratified parts, all inside `src/commands/research/main.md`:**

1. **Phase 0.3's ticket-file arm**, a conditional block placed **BEFORE** the topic-string paragraph, because detection has to run before the argument is treated as a topic. Five numbered steps: announce the path read; open the file with the Read tool; the `# Ticket NNN: <title>` heading's title part seeds `set-topic`; the body is written VERBATIM to a scratch file with the Write tool and passed as `set-verbatim-prompt --value-file` (`-` reads stdin), **never inline**, with the command-substitution reason in one clause; and a `**Ticket**:` value other than `(none)` is carried to Step 4.1 **unnormalized**. The block shows only the two setter calls that differ, states that `reset-memo` / `reset-report` / `set-date` and the six-dimension rubric are untouched, states that the run READS the ticket file and never writes it, and closes with an explicit no-op clause for a non-matching argument.
2. **The `set-verbatim-prompt` explanation extended** so the arm does not falsify it: in the ticket-file arm the persisted value is the ticket file's BODY rather than `$ARGUMENTS`, **the field and its meaning unchanged — only the door it arrives through differs.**
3. **The `STARTING POINT` rubric sentence extended** — a consumed ticket file is pre-filled input **in exactly that sense and carries no extra authority**: however complete it looks, it seeds `symptom` and nothing else.
4. **The never-fabricate-a-user-mode rule extended** — two ticket-file phrasings added inside the existing banned list, plus *"a consumed ticket file is input, never permission."*
5. **Step 4.1's question 2** — the conditional third authored option `"<ID> (from the ticket file)"` listed first, **three authored options in that case and two otherwise**, no authored "Other", `(Recommended)` on none, *"Pre-offering is not answering"*, and the answer-reading list gaining the new arm plus a **hardened `No ticket`** that stands even when an ID was pre-offered.
6. **The read-only sentence** in the outputs section, stating a consumed ticket file appears in no output list in either mode.

**Reviewer verification highlights — what it checked rather than assumed:**

- **Every mechanical claim was matched against the COMMITTED Phase 1 and Phase 3a code**, not against this plan: the `# Ticket NNN: <title>` heading and the field order the arm parses were diffed against `_format_ticket`'s actual render, and the `--value-file` flag, its `-` stdin form and the `newline=""` read behavior against the shipped parser and handler.
- **The discipline-not-verification paragraph was diffed WORD FOR WORD and is byte-identical.** ⚠ **This is the check most worth naming**, because the paragraph sits directly beneath an edited block and an accidental re-flow would look like nothing.
- **OQ-4 holds MECHANICALLY, not by prose:** the pre-offered ID flows into the **unmodified** `<ticket>` variable and reaches the **unmodified** `allocate-feature-dir` call, so a declined pre-offer allocates per the user's actual answer because there is no other path for it to take.
- **The ordinary arm and the Fresh-every-run guarantee are byte-unchanged** — `set-verbatim-prompt --value "<full raw $ARGUMENTS>"` still sits at its original site, and the unconditional reset is still unconditional.
- **A `value-file` grep returns exactly three files**, all expected: the two committed Phase 3a sources and this command spec.

**Reviewer findings — 0 high / 2 medium / 1 low / 1 nit — ALL FIXED:**

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | Medium | One bare **"ticket"** survived in added text at the hardened `No ticket` arm — the exact drift the vocabulary rule exists to prevent, in the sentence that asserts it | **FIXED** → "is not a ticket ID" |
| 2 | Medium | The three-option list gave no guidance on **position**, while Question 1 pairs first-slot with `(Recommended)` — so a reader could infer the pre-offered ID is recommended because it is listed first | **FIXED** — the contrast is now stated: position carries no weight here, read the label, not the slot |
| 3 | Low | "Step 4.1's ticket question" was ambiguous under this plan's own two-senses rule | **FIXED** → "ticket-ID question" |
| 4 | Nit | A double negative ("grants no shortcut … would not have granted, which is none") made a load-bearing sentence read twice | **FIXED** → "grants exactly the shortcut pasting the same text inline would — none" |

**Two items raised by the author and resolved by the reviewer:**

1. **The discipline paragraph's opening — *"the message that carries the two questions"* — is STILL TRUE.** "Two questions" counts the questions in the one AskUserQuestion call (save + ticket), not the options in question 2. **Checked deliberately, because the third option makes it read wrong at a glance.**
2. ⚠ **RESIDUAL, recorded not fixed: that same untouched paragraph uses a bare "ticket" three times.** The byte-identical requirement and the vocabulary rule collide there, and **byte-identical wins** — the paragraph is the one this phase must not re-flow. Every sentence this phase ADDED uses "ticket ID" or "ticket file".

**`claude-code-guide` coverage:** this session's invocation covered the command surface, and **Phase 3 changed no frontmatter** — no `allowed-tools` entry, no key, no description. The pass is cited rather than re-run.

### Phase 4 — Docs, ledgers, and the plan-88 amendment *(instruction-only)*

**Route: instruction-author → instruction-reviewer**, plus `claude-code-guide` for `src/CLAUDE.md` (it ships as the consumer's root `CLAUDE.md`; plan 08's always-on-trim discipline binds, and **"checked, nothing to amend" is a finding to record**, not a phase that failed).

Open with `grep -rn "report-bug\|Sixteen of the twenty\|model-invocable\|declared memory disposition\|emitted commands\|bugs/" src/ scripts/ *.md README.md` and reconcile every hit. ⚠ **The last two alternations were added because the first four MISSED a live numeral site** — see the `storage-rules.md` bullet below; **a roster numeral does not have to contain a digit-shaped roster word to be a roster numeral.** **This sweep list is NOT certified exhaustive** — treat a hit not named below as an omission in this plan, not as a new defect.

Scope:

- **`src/CLAUDE.md`** — the `Standalone` list gains one bullet; `### Command Details` gains one short entry in the thirteen's terse shape; **`### Conversational fix-or-file offer`'s third arm gains D6's clause.** ⚠ **The "Four are human-typed only" sentence and "Every other forge command is model-invocable" both stay TRUE at 21 commands and need no edit** (fact 12) — **record that as a checked no-op.**
- **`src/devforge/storage-rules.md`** — ⚠ **a roster numeral living OUTSIDE the three rosters D7 names, and the one this plan's original sweep pattern missed entirely.** Inside the VERSIONED class's `memory.md` READ-lane bullet, one sentence reads *"Each of the 20 emitted commands carries exactly one declared memory disposition (13 `READS` / 7 `N/A`) with a recorded reason, enforced by the maintainer-side gate `scripts/verify-memory-lane.py`."* **Both numerals move: 20 → 21 and the `N/A` count 7 → 8; the `READS` 13 does not move**, because the new command is `N/A` (Phase 1's deliverable 5). ⚠ **Phase 2 already edited this file for a different section** — that edit does NOT touch this sentence, so **do not read a Phase-2 diff on this path as evidence this numeral was handled.** ⚠ **And name the window rather than discovering it: Phase 1's disposition entry makes this sentence FALSE the moment it lands, and it stays false until this phase.** That is an accepted cross-phase transient, not a defect — **but a session that stops between Phase 1 and Phase 4 has left a false sentence in an emitted file**, so this bullet is the first thing Phase 4 does, not the last.
- **`README.md`** — ⚠ **the words `Sixteen of the twenty` become the new spelled-out figures, and the command list gains one line.** **A digit grep will not find this sentence.**
- **`CHANGELOG.md`** — one `## [Unreleased]` entry stating the honest bounds: manual-only lifecycle, no tracker integration, nothing links a ticket file to a feature directory.
- **`88-COLD-FIX-BUGS-LANE-PLAN.md`** — a dated note at D6 recording the third arm's new variant and that nothing else in the rubric moved. **No build record is edited and no phase is re-opened.**
- **Repo-root `CLAUDE.md`** — this plan's one-line index entry, and a dated pointer on plan 88's and plan 63's entries.
- **`PLAN-STATUS-ARCHIVE.md`** — the mirrored full entry.
- **`DEVELOPMENT-STATUS.md`** — the command list. ⚠ **Its `bugs/`/`.gitkeep` claim (fact 14) is NOT this plan's to fix** — record it, leave it.

**Verify:**

- The sweep returns zero dangling references; the `tests/` suite is green.
- **The counts were read LIVE and the delta is stated: 20 → 21 promoted, 16 → 17 model-invocable, 4 human-typed-only unchanged.** ⚠ **What the rule demands is the live read, not a particular result.**
- **`grep -rn "Sixteen of the twenty" .` returns nothing**, and the replacement figures are spelled the same way.
- **`grep -n "declared memory disposition" src/devforge/storage-rules.md` returns ONE line, and that line reads 21 / 13 `READS` / 8 `N/A`.** ⚠ **Check this against `scripts/lib/memory_lane.py`'s live dict rather than against this plan** — the file and the dict must agree, and the dict is the one a gate reads.
- **Plan 88's amendment exists, is dated, and edits no build record.**
- **`src/CLAUDE.md`'s human-typed sentence is byte-unchanged**, and the no-op is recorded.
- **The `CHANGELOG.md` entry states the bounds.** An entry claiming the framework "tracks tickets" has over-claimed by the whole plan.
- **Commit style read from the live `git log`** — subject lowercase and terse with a scope prefix; **read the trailer convention from the log, never from a remembered sentence.**

#### Phase 4 build record — 2026-09-04

**Route as specified: instruction-author → instruction-reviewer.** ⚠ **Instruction-only.** ⚠ **A concurrent session had committed plan 94's own ledger sweep earlier the same day, so every shared file was re-read LIVE and nothing was carried from an earlier read.**

**Live counts — read from the tree, independently re-derived by the reviewer, never incremented from this document: 21 promoted / 17 model-invocable / 4 human-typed-only, and 13 `READS` / 8 `N/A`.** The human-typed SET is unchanged and no `disable-model-invocation` flag moved.

**The nine-file sweep, as executed:**

1. **`src/devforge/storage-rules.md` — FIRST, because it is the recorded transient.** `20 emitted commands` → **21**, `7 N/A` → **8**, `READS 13` unmoved (the new command is `N/A`). **Written from `scripts/lib/memory_lane.py`'s live dict — eight `NOT_APPLICABLE` entries out of twenty-one — never from this plan.**
2. **`src/CLAUDE.md`** — one `Standalone` bullet, one terse `### Command Details` entry, and D6's one clause on the conversational offer's third arm.
3. **`README.md`** — the spelled-out figures, the `Standalone` line, the command list, the artifact-directory list and the layout diagram.
4. **`CHANGELOG.md`** — one `## [Unreleased]` → `### Added` entry, first in the list.
5. **`88-COLD-FIX-BUGS-LANE-PLAN.md`** — a dated blockquote at D6. **No build record edited, no phase re-opened.**
6. **Repo-root `CLAUDE.md`** — this plan's index entry plus dated pointers on plans 63 and 88.
7. **`PLAN-STATUS-ARCHIVE.md`** — the mirrored full entry plus the same two pointers.
8. **`DEVELOPMENT-STATUS.md`** — the command-list entry and the model-invocable count.
9. **`scripts/lib/memory_lane.py`** — a prose-only docstring closure of the split narrative (`…16/4 since plan 93…, and 17/4 since plan 95…`). **No logic, no dict, no test touched.**

**Two transients CLOSED, both verified against the tree by the reviewer rather than taken from the record:** the `storage-rules.md` numeral (Phase 2's build record now carries a dated CLOSED marker beside the original wording), and the `report_ticket_helper` orphan (closed at Phase 2b, marked in two places). **In both cases the original sentence is KEPT** — it records the state a phase shipped and why it was acceptable, which a reader needs more than a tidy file.

**Checked no-ops, recorded because "nothing to amend" is a finding:**

- **`src/CLAUDE.md`'s two count-adjacent sentences** — *"Four are **human-typed only**"* and *"Every other forge command is model-invocable"* — are **both still true at 21** and were **NOT edited**. Verified by reading them live.
- **`claude-code-guide` was CITED, not re-run**, with the reason stated: **this phase changed no frontmatter** — no key, no `allowed-tools` entry, no `description`.

**The sweep grep, and its result classified rather than declared clean:** every surviving hit of the stale strings is a **self-dating historical record**, not a live claim — plan 92's CHANGELOG parenthetical (*"the LIVE counts are 16/4 **as of 2026-09-03**"*), plan 94's fact table, plans 63 and 74's own dated amendment notes, and this plan's own scope, Verify and trap lines, which name the string they instructed changing. **That last group is the self-referential-grep artifact plan 94 avoided by deliberately not writing the token its own Verify forbade.**

⚠ **The lesson this phase actually produced, and it is the one worth carrying: the plan's own Verify pattern MISSED a site.** The Verify said *"`grep -rn "Sixteen of the twenty" .` returns nothing"* — an exact-phrase pattern — and `DEVELOPMENT-STATUS.md` carried the variant **"Sixteen commands are model-invocable"**, which that pattern cannot match. **This is the words-spelled-count trap recurring one level deeper**: the plan already knew a digit grep misses a spelled count and wrote a phrase grep to catch it, and the phrase grep then missed a *different spelling of the same count*. **The durable form of the check is a spelled-number-token sweep** (`sixteen` / `seventeen` / `twenty` / `teen `), not an exact phrase — and the reviewer, not the author, found it.

**Post-fix verification of that lesson, run across the sweep's files:** `README.md` returns **exactly one** spelled-count hit (the corrected `"Seventeen of the twenty-one"`) and `DEVELOPMENT-STATUS.md` **exactly one** (the corrected `"Seventeen commands"`). Every other hit anywhere is either an **`### Always` Key-Rule ordinal** (`a sixteenth Key Rule`, `the list stayed at sixteen` — items, not commands) or a **dated historical verification** (*"verified 2026-08-17 that seven of twenty command files carry the flag"*). **No stale spelled command count survives.**

**Reviewer findings — 0 high / 3 medium / 2 low / 1 nit — ALL SIX FIXED:**

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | **Medium** | `DEVELOPMENT-STATUS.md` still read *"Sixteen commands are model-invocable"* — **the site the plan's own exact-phrase Verify could not match** | **FIXED** → "Seventeen"; the *"narrowed from seven"* clause is untouched, being a dated historical statement |
| 2 | **Medium** | `README.md`'s artifact-directory list omitted `tickets/`, so the install section named the drawers a project gets and left the new one out | **FIXED** |
| 3 | **Medium** | `README.md`'s layout diagram showed `bugs/` and not `tickets/` — the same omission where a reader looks for the tree | **FIXED** |
| 4 | Low | `src/CLAUDE.md`'s new catalog entry ran longer than its siblings and restated the lifecycle the Standalone bullet already carries | **FIXED** — trimmed to sibling length; `--type` reworded to "is required — compose it", which is also what the helper actually enforces |
| 5 | Low | `memory_lane.py`'s docstring narrative stopped at plan 93 while its dict had moved on | **FIXED** — one dated clause appended; **prose only** |
| 6 | Nit | The archive entry said "ticket question" where the emitted text now says "ticket-ID question" | **FIXED** |

**Divergences, each with its reason:**

1. **The archive's plan-63 and plan-88 entries were amended too**, beyond the literal instruction to pointer the repo-root ledger. ⚠ **`PLAN-STATUS-ARCHIVE.md`'s own head-matter requires its entries and the `CLAUDE.md` one-liners to stay in sync**, so pointering one and not the other would have created precisely the drift that file exists to prevent.
2. **Plan 63's own FILE was deliberately NOT touched.** Its `(AMENDED 2026-09-03 …)` note is dated and self-scoping, and the file is outside this phase's scope list. **Recorded rather than decided.**
3. **`DEVELOPMENT-STATUS.md`'s `bugs/` / `.gitkeep` claim is left as-is**, per instruction — `install.sh` contains no `bugs` string and the directory is created lazily on first write. **It is now recorded as a residual in three surfaces** (this plan, the repo-root index entry, and the archive entry) so it is not rediscovered as new.

### Phase 5 — Consumer e2e *(user-driven HARD GATE)*

**Everything above is build-verified, NOT consumer-validated.** No phase above may claim any of this has been observed on a real install.

**Batched behind the deferred e2e runs already queued** (plan 85's batching decision), never run mid-build.

**Known-answer anchors**, so this is a regression anchor rather than an exploratory run:

1. **Capture an enhancement.** `/devforge:report-ticket "add CSV export to the reports page"` on an install with no `tickets/` directory. **MUST** produce: `tickets/001-<slug>.md`, `**Status**: Open`, `**Type**: enhancement`, `**Source**: manual`, `**Ticket**: (none)`, `**Reported**` = today, and the body carrying the text as given.
2. **Capture pasted tracker text with an ID.** Capture a multi-paragraph pasted body **containing a backtick and a `$(` sequence**, with ticket `PROJ-123`. **MUST** produce: the body byte-identical to what was pasted, and `**Ticket**: PROJ-123`. ⚠ **The awkward characters are the point** — this anchor is where OQ-6's decision is observed, and a body that came back mangled is an OQ-6 finding, not a helper bug.
3. **Consume it.** `/devforge:research tickets/001-<slug>.md`. **MUST** produce: an announcement naming the file it read; **all six rubric dimensions asked separately, each in its own turn**; and at Step 4.1, question 2 offering `PROJ-123 (from the ticket file)` alongside the two standing options, **with the ID not pre-selected**. ⚠ **MUST also produce the NO-WRITE-BACK result, and it is not optional colour**: record the SHA-256 of `tickets/001-<slug>.md` before the run and after it, and confirm `git status` reports the file unmodified — **including on the confirmed-save arm, which is the arm that would write if anything did.** **This is where D4's bound (ii) and D5 are observed**; a modified file means a second writer exists and D5 was breached by the build. **Scored as a PAIR with anchor 2** — a capture that mangles the ID passes 3's mechanics and fails the pair; a consumer that auto-answers the ticket question passes 2 and fails the pair. **Neither is meaningful alone.**
4. **`bugs/` and the cold-fix contract are untouched.** After anchors 1–3: `git status` shows **no** modification under `bugs/`, and `/devforge:fix bugs/NNN-<slug>.md` on a pre-existing bug behaves exactly as before. **Then record what `/devforge:fix tickets/001-<slug>.md` does.** ⚠ **This half is an OBSERVATION, not a MUST**: whether that argument enters cold mode is a property of the existing path-shaped trigger, which this plan does not modify and no phase of it tested. **A cold-mode entry there is a finding about that trigger** — and it would falsify D1's central argument, so it is recorded verbatim whichever way it goes.
5. **The offer.** Mention a non-defect improvement in conversation. **MUST** produce: the third arm offering `/devforge:report-ticket` as the file-it-for-later variant beside the full chain. ⚠ **This is an OBSERVATION with no MUST about which the user picks** — the rubric is advisory (D6's bound).

**Verify:**

- All five anchors are scored **explicitly** — stated, not summarized. **Anchors 2 and 3 are scored as a PAIR.**
- **Anchor 3 records the number of rubric turns as a NUMBER.** A run that collapsed the rubric is the failure this plan's D4 exists to prevent, and it is invisible in a summary that says "the rubric ran".
- **If it fails**, record the negative with artifacts and identify which mechanism produced it before proposing anything: a mangled body is OQ-6; an auto-answered ticket question is D4 part 4; a collapsed rubric is D4 part 3; **a ticket file whose hash changed across the run is D5** (a second writer shipped); a ticket file accepted by `/devforge:fix` is D1; a missing offer is D6. **They have different fixes.**
- **A clean run is evidence the lane works and NOT evidence the gap cost anything.** There was no incident; there still is none.

---

## Non-goals

- **Any tracker or Jira integration, API call, credential, or network access.** The framework reads what a human pasted and nothing else.
- **Verifying that a ticket ID exists.** Plan 91's stance, inherited verbatim.
- **Any change to `bugs/`'s schema, `_shared/bug_file.py`, `report_bug_helper`, `/devforge:fix`, or `/devforge:report-bug`** — beyond D6's one clause in `src/CLAUDE.md`'s conversational offer, which touches none of those files.
- **A forward pointer inside `/devforge:report-bug`.** Plan 88 ratified reading (i); this plan takes no position on that fork (D6 alternative (c)).
- **Any gate, `verify-*` number, or hard-fail validator.** D7 — plan 75's tripwire, both halves.
- **Any mechanical lifecycle transition.** D5 — no command flips, fills or deletes a ticket file in v1.
- **Migrating existing `bugs/` files into `tickets/`.** Nothing moves, nothing is re-classified, nothing is deleted.
- **`/devforge:verify` Phase 9 triage writing to `tickets/`.** OQ-2.
- **Changing plan 63/93's human-typed carve-out.** The four setup commands keep the flag; the new command is model-invocable and the delta is in the model-invocable count only (D7).
- **A cross-check test binding `HELPER_STEMS` to `_PROMOTED`.** D7 alternative (c) — recorded as an owned residual with its cost measured, deliberately not built here.
- **Fixing `DEVELOPMENT-STATUS.md`'s `bugs/`/`.gitkeep` claim.** Fact 14 — pre-existing, recorded, out of scope.
- **Back-porting into shipped installs.** They arrive via `install.sh` / `update.sh`.

---

## Dependencies + related

- **`88-COLD-FIX-BUGS-LANE-PLAN.md`** — the closest sibling and the source of this plan's central constraint: **`/devforge:fix`'s cold trigger is a path shape**, which is why D1 refuses a merged directory. Its D6 rubric is the only thing this plan amends, dated and narrow. ⚠ **Its own Phase 5 consumer e2e has NOT run** — deferred as a separate effort, not waived — so nothing it shipped may be treated as consumer-validated while this plan builds beside it.
- **`91-FEATURE-DIR-IDENTITY-AND-PROVENANCE-PLAN.md`** — the owner of the word "ticket" in the live tree (`TICKET_RE`, `REQUIRE_TICKET`, `spec/<ticket>`, the bucketed leaf) and of the *"nothing checks that the ticket exists"* statement this plan inherits. **D2's disambiguation rule exists because of it; OQ-4 declines to weaken it.**
- **`87-ARTIFACT-LANGUAGE-GUARD-PLAN.md`** — the English-only rule binding every byte of this plan and everything it emits, and the **predicted-gap-with-no-incident framing** `## Evidence constraint` copies. ⚠ Its detector rides `commit-artifacts` only, and OQ-7 keeps this lane outside that path — **a coverage bound, stated, not closed.**
- **`63-SKILL-COLLISION-SUPPRESSION-PLAN.md`** and **`93-MODEL-INVOCATION-CARVE-OUT-NARROWING-PLAN.md`** — the emitted layout, the `_PROMOTED` roster, the ≈40-word description budget, and the counts this plan **does** move. **Plan 63's standing coordination rule binds: read the counts LIVE.**
- **`75-INVESTIGATION-SEARCH-HARNESS-PLAN.md`** — the no-new-check-number / no-new-validator tripwire. **Both halves hold** (D7).
- **`74-MEMORY-LANE-INTEGRITY-PLAN.md`** — the owner of the `DISPOSITIONS` gate a 21st command must satisfy (fact 9). **Its Rule 1 is not loosened; one entry is added.**
- **`70-PIPELINE-WALLCLOCK-PROFILING-PLAN.md`** — the owner of `HELPER_STEMS` (fact 10). **A missing entry there is silent**, which is why D7 names it.
- **`68-INTAKE-OWNS-FEATURE-DIR-PLAN.md`** — the reason D1 alternative (c) is rejected: intake owns allocation, and a captured ticket allocates nothing.
- **`79-MEMORY-WINDOW-AND-RECEIPT-PLAN.md`** — cited for D1 alternative (d)'s rejection: a single append-target file is the failure class that plan removed.
- **`26-REINTRODUCE-FIX-PLAN.md`** — the *"extend the one binary, never a second composer"* rule. ⚠ **OQ-1 deliberately does NOT extend `bug_file.py`**, and the reason is risk to an unvalidated lane, not a repeal of that rule — **say it that way, or a future reader will read a precedent that was never set.**

---

## Context for next session

**The one sentence that governs everything here:** a `tickets/` file is a **capture**, not a **commitment** — it is written once by one command, read by one command, advanced by a human, and checked by nothing.

**Trap 1 — believing `bugs/` and `tickets/` are interchangeable.** They are not, and the asymmetry is deliberate: a bug has a provable terminal state and one mechanical closer; a ticket has neither (D5). **A build that gives tickets a `Fixed` status or a `close_ticket` verb has crossed D5 and D1 at once.**

**Trap 2 — putting a ticket file under `bugs/` "just for now".** `/devforge:fix`'s cold mode triggers on that path shape (D1). **A file there is a valid cold-fix input regardless of what its `**Type**` field says**, because nothing reads that field.

**Trap 3 — the word "ticket".** Two senses, both live, both this repo's (D2). **Every emitted sentence says "ticket ID" or "ticket file".** A sentence that says only "ticket" will be read the wrong way by half its readers.

**Trap 4 — the silent third roster.** `_PROMOTED` and `DISPOSITIONS` fail loudly if you forget one; **`HELPER_STEMS` does not** (fact 10). A 21st command with no entry there passes every test and quietly mis-segments the profiler. **Register all three in one commit.**

**Trap 5 — the spelled-out count.** `README.md` says *"Sixteen of the twenty"* in **words** (fact 12). **A `grep 16` sweep will report the docs clean while that sentence is false.**

**Trap 6 — weakening the rubric to make the consumer arm feel smoother.** `research/main.md:169` and `:171` are the forcing function that makes intake per-dimension. **A ticket file is a starting point for `symptom` and nothing else** — and `:171` exists precisely because a model with a full-looking ticket in hand will reach for a justification to skip.

**Trap 7 — a pasted body inside a shell argument.** Backticks and `$(...)` are command substitution in a double-quoted Bash argument (OQ-6). **The house already has the file/stdin route; use it.** A body that "worked in testing" was tested with text that happened to contain none of those characters.

**Trap 8 — reading a clean Phase 5 as evidence the lane was needed.** There is no incident behind this plan and none is claimed. **Phase 5 observes that capture and consumption work; it measures nothing about how often either is used.**

**The working tree carries uncommitted work throughout**, and several plans this file cites are working-tree state, so any "shipped" claim about them means reviewed-but-uncommitted rather than released. Re-check each from the code rather than from a Status line.

**Discovered while drafting, NOT owned by this plan and not fixed here:**

1. **`DEVELOPMENT-STATUS.md:69` claims `install.sh` ships an empty `bugs/` with a `.gitkeep`.** `grep -n bugs install.sh` returns nothing and the only `gitkeep` token in any `*.sh` is an unrelated `docs/` comment (fact 14). **The directory is created lazily on first write.**
2. **`_profile/_segment.py`'s `HELPER_STEMS` is not cross-checked against `_PROMOTED`** (fact 10). **Pre-existing; D7 alternative (c) records the three-line fix and declines to build it here.**
3. **`_shared/bug_file.py`'s number-scanning helper is private** (`_scan_highest_bug_number`), so any second document type either imports an underscored name across modules or duplicates the scan (OQ-1). **The choice is a real one and Phase 0 makes it.**
4. **Every forge command source carries a `name:` frontmatter line that the current docs say Claude Code IGNORES in a command file** (`### Claude Code authoring surface`). **House convention, harmless, untouched here** — recorded so a future author does not "discover" it as a defect and remove twenty lines.

---

## When resuming work

1. **Read this file in full, then `## Verified mechanics` again** — seventeen rows, each checkable in under a minute. **If rows 4, 6, 7, 8, 9, 10 or 12 no longer hold, stop and re-derive**: they are the shared writer, the ticket-ID owner, the research intake path, the rubric's forcing sentences, the two gated rosters and the live counts.
2. **Read `src/commands/report-bug/main.md` end to end before writing the new command spec.** It is 101 lines and it is the template; **its `## Maintainer note`, its helper-interaction paragraph and its eight rules are the shape being mirrored**, not just its phase list.
3. **Read `_shared/bug_file.py` and `_report_bug/_cli.py` in full before writing any Python.** The scan-once numbering rationale, the word-boundary slug truncation and the exit-code contract are load-bearing and none is visible from a signature.
4. **Re-verify every anchor before use. Grep the quoted string, never the `:NNN`** — `_SUBCOMMAND_REGISTRY`, `_scan_highest_bug_number`, `TICKET_RE`, `read_require_ticket`, `set-verbatim-prompt`, `Pre-filled input is a STARTING POINT`, `Which ticket is this feature tracked under?`, `_PROMOTED`, `DISPOSITIONS`, `HELPER_STEMS`, `Sixteen of the twenty`, `## Bug Report Rules`.
5. **Invoke the `claude-code-guide` agent before writing or amending any command frontmatter** — Phases 2, 3 and 4 each touch an emitted command surface or the consumer's root `CLAUDE.md`. **The fetched answers in `### Claude Code authoring surface` are dated 2026-09-04; re-check them if more than a few days have passed.**
6. **Route every edit through the house loops:** python-engineer → python-reviewer, test-first, for Phase 1; instruction-author → instruction-reviewer for Phases 2, 3 and 4, with `claude-code-guide` added for every command-spec and `src/CLAUDE.md` edit. **Phases 2–4 dispatch no python-engineer** — a phase that finds itself needing one has crossed its own boundary and must stop.
7. **Every file byte stays English** (plan 87), including this plan, the emitted command spec, every field label and every option string — regardless of any operator response-language setting.
8. **Do not let Phase 1's momentum answer Phase 0's forks.** The directory name, the field set, the rubric amendment, the argument surface and the private-name import are five separate picks, and **a build that discovers them mid-flight will resolve them by whichever is cheapest to code.**
