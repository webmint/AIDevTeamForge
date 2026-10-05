# 110 — Implement Auto-Approve Plan

**Created**: 2026-09-23
**Status**: **DECLINED 2026-10-03 by the maintainer — do not build; no phase of this plan starts.** The premise — an unattended drain of a feature's tasks — contradicts a principle the maintainer stated the same day: the framework is human-centric, a human reads every task's diff at the PHASE 7 gate before it is committed, and the loop waits for that read by design — because one task's diff is a load a reader can hold where a whole feature's diffs at once are not, and because a defect found in task N is repaired before task N+1 builds on it, which no after-the-fact review can do. The cost the gate carries is latency, and it is accepted with the measurement in view: `RESEARCH-2026-09-27-V2-COST-DIAGNOSIS.md` records 75 stops and 76 h idle in one implement run and ranks this plan the largest stop reducer (its L6 and §2.5 item 1), and `124-PIPELINE-COST-REDUCTION-PLAN.md` item 0 counts this plan as a dependency — the research file is a dated record and stands; plan 124 is a stub whose item 0 now rests on a declined plan and is re-pointed by whoever authors that plan, not here. `111-WIP-MARKER-CONTRACT-PLAN.md`'s D5 ordering against this plan is moot, and its planned edits to this file are no longer owed. The decision is recorded in `DEVELOPMENT-STATUS.md` `## Key Design Decisions` item 23. **Everything below is kept as the record of the argument, every counter-argument included, with two edits — the `### Phase 0 close record` paragraph and `## When resuming work` step 2, both now saying what this line says**: nothing in it is ratified, no file may quote a flag, field, option token, note token or filename this plan proposed as if it were live or ratified, and Phase 6 never ran. The status line this replaces read: *"Phase 0 OPEN — nothing below is ratified, no close record exists, and no build phase may start."* ⚠ **Numbered 110 because 101, 102, 104, 105, 106, 107, 108 and 109 are taken in this checkout as of 2026-09-23 and 103 was vacated by a renumbering — the gap at 103 is not a missing plan and must not be reused.**

`/devforge:implement` stops at a per-task human gate before every commit, and that gate is the reason the command has no unattended form: its own Usage sentence says so in writing. The proposal is a `--auto-approve` flag that does **not** remove the gate — it collapses the per-task gate down to the checkpoints the user ALREADY declared at `/devforge:breakdown`. The `review_checkpoint` field is authored by a documented placement rule, validated as a strict bool, carried across the breakdown handoff, and emitted on the task-resolve payload — **and consumed by nothing.** Auto mode activates a dead field rather than inventing a new policy. Nothing is being built. This plan exists to be argued and ratified first.

---

## Origin & evidence

⚠ **Evidence class, to be repeated in every summary of this plan: NO consumer incident, none claimed, NOTHING MEASURED, and no benchmark run stands behind any line here.** The plan originates from ONE maintainer request plus a code read of this tree on 2026-09-23. It is a capability plan in plan 101's class: the framework should be able to drain a task set unattended without lowering a quality bar. **A stated capability is not evidence.** A clean Phase 6 would show the flag behaves on one real feature; it would never show that the per-task gate cost anything, how often a user would use the flag, or what an unattended run saves.

This repo is public. **This plan names no client, no install, no repo, no branch of a client, no ticket id and no session identifier**, and no phase of it may introduce one. `release/v-1.23.0` is this repository's own branch and is named freely.

### What the flag is, derived from the tree

Each link is F-cited below. Nothing here is a relayed claim about the current tree; each step was re-read on 2026-09-23.

1. **The per-task gate is a v2 invention.** v1 had no per-task human approval gate at all — it committed inside its own phases and auto-advanced through a continuation file (F9). What v1 DID have were two stops v2 does not: a **review-checkpoint gate** keyed on the next task's `Review checkpoint: Yes` header, and a **context-health pause** at 6+ tasks completed in one session (F11, F12).
2. **v2 kept the FIELD and dropped both STOPS.** `Review checkpoint` is still authored per task by a documented placement rule, still parsed, still a strict bool on the handoff, still emitted on the resolve payload — and `src/commands/implement/main.md` names the identifier exactly once, in the list of keys that payload carries, and acts on it in no phase (F8).
3. **v2 also lost the session task counter** that v1's context-health tier read. `update-session-state` writes a FEATURE progress ratio, not a per-session count, and nothing in `src/` carries a per-session task counter of any kind (F13).
4. **So the unattended gap and the dormant field are the same gap.** The per-task gate is what makes the missing checkpoint stop and the missing context-health stop harmless today: the user stops at every task anyway. **Turning the per-task gate off is precisely what makes both absences active.**

**Consequence.** A flag that simply skipped the gate would ship a loop with no stops at all — no checkpoint stop, no context-health stop, and nothing to catch a conflict the panel refused to decide. **The flag is therefore not a subtraction; it is a re-binding of the stop to the policy the user already authored.**

### Corrections to the drafting brief

**Correction 1 — `.devforge/wip.md` is written and read by the ORCHESTRATOR, not by the helper, and `_wip.py`'s writer and reader have no production caller.** The drafting brief framed the marker as helper-owned and put the flag's persistence field in a Python build phase. The tree says otherwise: `src/commands/implement/main.md` PHASE 2 step 2 instructs the orchestrator to write the file, PHASE 0 instructs it to read the file, and `src/commands/implement/references/crash-recovery.md` states the arrangement in its own words — *"PHASE 2 writes the file directly and PHASE 0 parses it back; `_implement/_wip.py` states the same field shape in code, and both ends must honour it."* A grep over `src/` returns **no production caller** for `write_wip_marker`, `read_wip_marker` or `ImplementState`; the only live call in that module is `clear_wip_marker` (F14). **This changes D7's cost and Phase 1's content, and it is recorded rather than smoothed over.**

**Correction 2 — `src/CLAUDE.md`'s `### Hard Gates (block until approved)` list does NOT name the per-task gate.** The brief listed it among the sentences that would go stale. The heading sits at `:158` and the `/devforge:implement` member at `:163` reads *"Task breakdown approval → before `/devforge:implement` can start"* — a gate BEFORE the command, which the flag does not touch. **It stays true under the flag and is a classify-site, never a stale-site** (F15).

**Correction 3 — SIX plans ahead of this one carry an unratified Phase 0, not five, and a seventh is ratified-but-unbuilt.** The brief named 104, 105, 106, 107 and 109. `102-SPECIFY-IN-PLACE-REVISION-PLAN.md` is also *"Phase 0 OPEN"*, and `108-SCOPE-RULE-DOWNSTREAM-REGIME-PLAN.md` is *"Phase 0 CLOSED … Build phases MAY start. NOTHING IS BUILT."* (F19).

### Verified structure (2026-09-23)

Every fact below was read against this tree on 2026-09-23, except F9–F12, which are reads of the `release/v-1.23.0` branch and are marked. ⚠ **Line digits drift — grep the quoted text, never the digits.**

**F1 — The command file, and one frontmatter quirk.** `src/commands/implement/main.md` is **363 lines**. Its frontmatter order is `name` → `argument-hint` → `description`, so **`argument-hint: ""` sits at `:3`** — ⚠ **every other command source in `src/commands/` carries `argument-hint` at `:4`** (checked by an unfiltered grep on 2026-09-23: seventeen command sources declare one, and `implement` is the only `:3`). The `description:` field ends *"…then a per-task human hard gate before any commit."*

**F2 — The load-bearing contradiction, verbatim.** `src/commands/implement/main.md:31`: *"Usage: `/devforge:implement` — no arguments. The command resolves the first incomplete feature in resolution order (PHASE 1) and walks its tasks in dependency order; there is no `N`, range, or `all` form. Per-task human approval is logically incompatible with batch forms."* ⚠ **The last sentence is PLAIN TEXT in the file, not bold** — a Verify that greps for a bolded form fails against a correct tree. **This sentence is a direct contradiction of the proposed flag and a build phase must rewrite it.**

**F3 — The paired non-goal bullet.** `:53`, under `## What this command does NOT do`: *"**No batch task targeting.** There is no `/devforge:implement N` form (see Usage)."* ⚠ **It cross-references F2 by name, so the two are one edit or neither.**

**F4 — There are exactly FIVE `AskUserQuestion` sites in `main.md`, and TWO further mentions in the references, neither of which is a sixth prompt.** An unfiltered grep over `src/commands/implement/` on 2026-09-23 returns seven hits:
- `main.md:64` — PHASE 0 crash recovery; options `["resume", "rollback", "skip", "manual"]`.
- `main.md:240` — PHASE 7 Stage A, iterating recorded decision items, *"sequentially, never batched"*.
- `main.md:269` — PHASE 7 Stage B; options `["approve", "repair", "skip", "stop"]`.
- `main.md:329` — the gate-blocked path; options `["repair", "skip", "stop"]` (no `approve`).
- `main.md:343` — the tooling-unavailable path; options `["fix-tooling", "scope-and-approve", "skip", "stop"]`.
- `references/crash-recovery.md:32` — **the same PHASE 0 prompt, documented**, not a second one.
- `references/forcing-functions-gate.md:52` — **a ROUTING line**, not a prompt: it sends triage to *"the PHASE 7 gate-blocked `AskUserQuestion`"*.
⚠ **`references/agent-brief.md` and `references/review-loop.md` contain no prompt at all.** **Load-bearing: an auto branch is owed at FIVE sites, and a sixth claimed anywhere is a misread of the two reference mentions.**

**F5 — Stage A has THREE decision-item kinds with three different option sets, and two of them carry an explicit prohibition.**
- **A judgment item** (`:243`): `["<agent's resolution> (recommended)", "<named alternative>", "let me specify", "stop"]`, with *"Option 1 is ALWAYS the agent's resolution, marked `(recommended)`, so agreeing is one click."*
- **A `could-not-converge` item** (`:250`): `["send back with direction", "skip", "stop"]` — *"there is NO accept-the-finding-as-is option, because an open finding must never reach `approve` (the D4 guarantee above)"*.
- **A `conflict` item** (`:257`): `["<reviewer A's position>", "<reviewer B's position>", "let me specify", "stop"]`, closing at `:261` with *"Never pick either reviewer's position for the user — this item exists because PHASE 6 must not decide it on the user's behalf."*
⚠ **VOCABULARY COLLISION, named here so it cannot be misread later:** that file's *"the D4 guarantee above"* is an EARLIER PLAN'S D4, and the same file cites *"(D1)"* at `:294`, *"per D2"* at `:294` and *"per D3"* at `:143` in the same borrowed vocabulary. **None of them is this plan's D1–D10.** No phase may read them as this plan's items, and **no emitted sentence this plan writes may add a new plan-vocabulary token to that file.**

**F6 — The judgment item ALREADY has a spec-sanctioned no-answer default.** `:248`: after a second reply that picks no option, *"keep option 1 without relaunching the agent, and add `shape not confirmed by the user — delegated`, naming the item's finding, to the `--notes` value Stage B's `approve` passes to `mark-complete`, so the task's Completion Notes record that the user never confirmed this shape."* The same sentence guards the reason: *"Option 1 stays because it is the resolution already in the working tree, never because it is marked `(recommended)`."* **So an auto path for judgment items is an existing fallback given a declared trigger, not a new invention** (D3, OQ-5).

**F7 — Two `## IMPORTANT RULES` items, and one emitted always-on rule, are in scope.** `:358` rule 1: *"**Nothing commits before `approve`.**"*. `:360` rule 3: *"**One task at a time, dependency order.** `resolve-next-task` picks exactly one task; the loop drains the feature task-by-task. There is no batch mode."* ⚠ **A third site is emitted into every consumer project and is NOT in `src/commands/`:** `src/CLAUDE.md` `### Always` item 6, *"**One task at a time** — execute tasks sequentially following the dependency graph"*. **That one stays TRUE under the flag** — the flag removes approvals, never sequencing — **so it is a classify-site for Phase 5, not an edit by default.**

**F8 — THE DEAD FIELD. `review_checkpoint` is wired end to end and consumed by nothing.** Verified 2026-09-23 by an unfiltered `review_checkpoint|Review checkpoint` grep over `src/`:
- **Authored** — `src/commands/breakdown/main.md:506`, `### Review Checkpoint Placement`: *"Set `**Review checkpoint**: Yes` or `No` per task. Auto-place `Yes` at:"* then *"1. **Convergence points** — the task depends on 2+ other tasks. 2. **Layer boundary crossings** — the first presentation-layer task after domain/data-layer tasks. 3. **High-risk tasks** — any task rated High in the risk assessment."*, closing at `:514` with *"All other tasks get `No`. The user can add or remove checkpoints during the Phase 4 approval gate."* ⚠ **The section spans `:506`–`:514`, not `:505`–`:513` as the drafting brief had it.**
- **Declared as a task header field** — `breakdown/main.md:397`, *"Review checkpoint (Yes/No — see below)"*.
- **Reported back to the user, twice** — `breakdown/main.md:627` *"**Review checkpoints**: [count] (before tasks [list])"*, rendered by `src/devforge/lib/breakdown_helper.py:3730`; and `breakdown/main.md:524`, which tells the orchestrator to fill *"the review checkpoints table"* in `tasks/README.md`.
- **Emitted into the task skeleton** — `breakdown_helper.py:1067` appends `**Review checkpoint**: Yes/No`; the same field shape is restated in `src/devforge/storage-rules.md:202` and in `breakdown_helper.py:142`'s module docstring.
- **Parsed** — `breakdown_helper.py:2892` `_REVIEW_CHECKPOINT_RE`; `:3392`–`:3398` and `:3418` set it, with `:3216` documenting *"review_checkpoint: 'Yes' → True, 'No'/missing → False."*
- **Validated** — `src/devforge/lib/_breakdown/handoff_schema.py:126` types it `bool`, and `:151`–`:154` reject a non-bool. **The rule is stated TWICE, in DIFFERENT words**: `:111` reads *"review_checkpoint is a strict bool. int (including 1/0) is rejected."*, and the module docstring at `:26` reads *"TaskRow.review_checkpoint is a strict bool (int is rejected)."* ⚠ **Same rule, not the same string — a Verify asserting one verbatim text at both lines fails against a correct tree.**
- **Carried** — `breakdown/main.md:665` names it among the handoff's per-task machine contract; `src/devforge/lib/_implement/_handoff_reader.py:203` reads it as `review_checkpoint=bool(t.get("review_checkpoint", False))`.
- **Emitted on the resolve payload** — `src/devforge/lib/_implement/_cmds_resolve.py:387`, `"review_checkpoint": selected.review_checkpoint,` on the `{"state": "task", …}` object.
- **And then dropped.** `src/commands/implement/main.md:102` names it in the list of keys that payload carries, and **that is the ONLY occurrence of the identifier in the whole implement command — `main.md` and all four reference files.** No phase reads it, branches on it, or mentions it again.
⚠ **A SEMANTIC MISMATCH the plan must settle, not inherit:** the field's own user-facing report says *"(before tasks [list])"*, i.e. a stop BEFORE task N — which is v1's gate position (F11) — while v2's only human stop is AFTER the work and before the commit (F4, `main.md:269`). **"Activate the field" therefore does not name a position on its own** (D2).

**F9 — v1's equivalent command, and what it did NOT have.** ⚠ **Branch read, `release/v-1.23.0`, pre-`src/` layout. These files exist ONLY on that branch — read them with `git show release/v-1.23.0:<path>` and NEVER as a working-tree path.** ⚠ **Independently corroborated here on 2026-09-23: a glob of `.claude/commands/*.md` in this working tree returns `review-helper.md` and `release.md` and nothing else.** The command is `.claude/commands/execute-task.md` (453 lines) plus two included files, `.claude/commands/_multi-task-continuation.md` (59 lines) and `.claude/commands/_context-maintenance.md` (89 lines). **v1 had NO per-task human approval gate at all:** it committed in its Phases 4/5/6 and auto-advanced through Phase 8 into `_multi-task-continuation.md`. **The per-task hard gate is a v2 invention, and this plan does not restore a v1 behaviour — it bounds a v2 one.**

**F10 — v1's stops that were HALTS, not prompts.** ⚠ Branch read, as F9.
- `execute-task.md:139` — a pre-flight failure → *"STOP execution — do not proceed to Phase 3"*.
- `execute-task.md:288` — *"If all 3 repair attempts are exhausted and checks still fail"* → *"STOP execution entirely"*.
- `_multi-task-continuation.md`, Queue Processing step 3a — the next task's dependency is not Complete → *"stop and report: 'Task [N] is blocked by incomplete dependency Task [M]. Completed [X] of [Y] queued tasks.'"*
**Load-bearing for D4 and D5: v1's unattended loop halted on exactly the conditions this plan proposes to halt on, and it halted rather than guessing.**

**F11 — v1's stops that were PROMPTS.** ⚠ Branch read, as F9.
- `execute-task.md:44` — PHASE 0 Recovery Check.
- `_multi-task-continuation.md` step 3a2 — **the Review checkpoint gate**: read the NEXT task's header; if `Review checkpoint: Yes`, print `⏸️ REVIEW CHECKPOINT before Task [N]` with the preceding tasks' contract summaries and options `1. Continue / 2. Review (show git diff) / 3. Pause`.
- `_multi-task-continuation.md` step 3b — **Context health**: at 6+ tasks completed this session, *"**pause execution**"* with a `/compact` command, and *"Stop execution here. Do NOT continue to the next task without user-initiated compaction."*

**F12 — v1 counted tasks per SESSION, in three tiers.** ⚠ Branch read, as F9. `_context-maintenance.md` phases 7.5.1/7.5.2 tracked `Tasks completed this session` in session state with **1-2 light (no action) / 3-5 moderate (advisory `💡`) / 6+ heavy (`🔴` strong recommendation)**, and the file records the deliberate asymmetry: *"Phase 7.5.2 (single-task) recommends compaction; Phase 8 (multi-task, heavy) pauses execution. The difference is intentional: single-task completion is advisory, multi-task continuation requires the pause to prevent context degradation across many sequential tasks."*

**F13 — v2 LOST that counter, and one live doc line still claims it.** `src/devforge/lib/_implement/_cmds_session.py:145` writes `**Progress**: {0}/{1} tasks complete` — a FEATURE ratio, not a per-session count. `cmd_update_session_state` (`:247`) is the ONLY command that module defines, its flags are `--feature`, `--completed-count`, `--total-count`, `--recent-tasks`, `--recent-decisions`, and the file it writes is a ≤40-line sliding window of the last 3 task mods and last 3 decisions. **No `implement_helper` verb READS it** — `main.md`'s `allowed-tools` names `update-session-state` alone, and `src/CLAUDE.md`'s `## Session Continuity` makes the read the orchestrator's. ⚠ **There is no per-session task counter anywhere in `src/`, and no context-health mechanism of any kind:** an unfiltered case-insensitive grep over `src/` for `compact|context health|context-health` on 2026-09-23 returns `SessionStart` hook matchers and their two documentation rows, `src/CLAUDE.md`'s *"compact snapshot"* and *"If context is compacted"* sentences, and unrelated uses of the word *compact* meaning "small" — **no tier, no threshold, no task count and no `/compact` recommendation anywhere.** ⚠ **`DEVELOPMENT-STATUS.md:123` nevertheless still reads *"Three-tier context health check: light (no action), moderate (optional /compact), heavy (strongly recommend /compact)"*, under a heading that names v1's phase number (`### Context Maintenance (Phase 5.2)`). That sentence is FALSE against this tree TODAY, before this plan changes anything** (D8, Phase 5).

**F14 — `.devforge/wip.md` has a FIXED field set, and the ORCHESTRATOR is its live writer and reader.** The fields are `Command` / `Feature` / `Task` / `Title` / `Agent` / `Phase` / `Checkpoint`, stated in three places: `src/commands/implement/main.md:144` (PHASE 2 step 2, which instructs the orchestrator to write them), `references/crash-recovery.md:9`–`:24` (the fenced field block plus one bullet per field), and `src/devforge/lib/_implement/_wip.py`'s module docstring and `write_wip_marker`. **The reference file states the two-end rule itself, at `:7`:** *"PHASE 2 writes the file directly and PHASE 0 parses it back; `_implement/_wip.py` states the same field shape in code, and both ends must honour it."*
- ⚠ **`write_wip_marker`, `read_wip_marker` and `ImplementState` have NO production caller.** A grep over `src/` returns their definitions, their own docstrings, and one live import: `_implement/_cmds_commit.py:157` imports `clear_wip_marker`, called at `:694`. Their only exercisers are `tests/lib/_implement/test_wip.py` and `tests/lib/_implement/test_state.py`.
- `write_wip_marker` renders from an `ImplementState` (`_implement/_state.py`, a frozen 8-field dataclass validated in `__post_init__`); `read_wip_marker` parses `**Key**: Value` lines and returns `{}` for a present-but-unparseable file, so callers must use `.get`; writes are atomic (`tempfile.mkstemp` + `os.replace`).
- ⚠ **The two ends ALREADY disagree on one field's vocabulary.** `crash-recovery.md:23` documents `Phase` as *"(`dispatch` / `verify` / `review` / `forcing_functions` / `gate`)"* and `main.md:144` starts it at `dispatch`; `_state.py`'s `_VALID_PHASES` is `preflight, agent, verify, review, forcing_functions, gate, commit, complete` — **eight values, no `dispatch`** — while the same file's docstring calls them *"exactly the seven loop phases"*. **PRE-EXISTING, not caused by this plan, and it is the evidence for D7's counter-argument.**
- ⚠ **The phase-naming drift has a THIRD site, and one of its three occurrences is USER-FACING.** `grep -n "Phase 9" src/devforge/lib/_implement/` returns exactly three lines, all in `_cmds_preflight.py`: `:12` (the module docstring), `:310` (`_check_wip_marker`'s docstring) and **`:323`, which is not a docstring at all but a segment of the stderr string a consumer reads on a stale marker** — *"Re-run /devforge:implement (or restart the loop) to enter the Phase 9 crash-recovery branch (resume / rollback / skip / manual)."* **The live spec calls that branch PHASE 0** (`src/commands/implement/main.md:57`, `:59`). **PRE-EXISTING, not caused by this plan, and NOT fixed here** (`## Non-goals`, Trap 11).
- **There is no auto-mode field, and no helper verb writes or reads this file.**

**F15 — The consumer-facing sentences, each classified rather than lumped.** ⚠ **Re-verify every digit; `108-SCOPE-RULE-DOWNSTREAM-REGIME-PLAN.md` recorded `DEVELOPMENT-STATUS.md` item 20 at `:114` on 2026-09-21 and it reads `:116` today.**
- **Goes stale under the flag — an EDIT:** `src/CLAUDE.md:62` (*"per-task hard gate before commit"*); `src/CLAUDE.md:102` (the `#### /devforge:implement` entry at `:101`, *"No arguments — auto-resolves … with a per-task hard gate before each commit."*); `README.md:79` (*"… → per-task hard gate before commit."*); `DEVELOPMENT-STATUS.md:113` (*"panel-clean gates the per-task approve"*).
- **Describes the marker or the loop — CLASSIFY, edit or verified no-op:** `DEVELOPMENT-STATUS.md:121`, `:128`, `:129`, `:130`; `src/CLAUDE.md` `### Always` items 6 and 13, `## Session Continuity`, `### Crash Recovery`.
- **Stays TRUE — a verified NO-OP:** `src/CLAUDE.md:163`, *"Task breakdown approval → before `/devforge:implement` can start"* (Correction 2).
- ⚠ **Already FALSE before this plan — but with DIFFERENT owners, so they are NOT grouped:** `DEVELOPMENT-STATUS.md:133`, *"In wrapper mode, WIP marker includes `## Source Repo Checkpoint` section"* — that literal appears nowhere in `src/` (grep, 2026-09-23; its only other hit is `CHANGELOG.md:426`, a released entry and a frozen record) — is **NOT this plan's to fix**, and is named only so that a drive-by edit is a recognised scope departure rather than an accident. **`DEVELOPMENT-STATUS.md:123` (F13's three-tier claim) is equally false today but IS this plan's to SETTLE**, because D8's outcome reaches it either way — made true by Phase 2, or repaired by Phase 5 (D8, Phase 5's Deliverables, Trap 11). **Both sit inside blocks Phase 5 reads, which is why both are named here; only the first is left as it stands.**

**F16 — Emission needs no change, and the reference naming convention is already fixed.** `scripts/emitters/claude.py:83` calls `write_references(refs, refs_dir)` with `refs_dir = refs_root / source.name` and `refs_root = target / ".devforge" / "command-refs"` (`:71`, `:79`), so a NEW file under `src/commands/implement/references/` lands at `.devforge/command-refs/implement/` with **no emitter edit**; `implement` is already a member of `_PROMOTED` (`:57`), so no `_PROMOTED` edit either. The four existing reference files are `agent-brief.md`, `crash-recovery.md`, `forcing-functions-gate.md`, `review-loop.md` — **lowercase kebab-case, topic-named, no prefix.** ⚠ **That the emitted `.claude/commands/devforge/<name>.md` layout itself keeps working is F22, which also records why the skills question is out of scope here.**

**F17 — A flag on an emitted command is not a new convention.** `src/commands/audit/main.md:4` carries `argument-hint: "[--full | --uncommitted | --top N | path] [--passes N]"`; `report-bug` and `report-ticket` carry flag-bearing hints too (grep of `^argument-hint:` over `src/commands/`, 2026-09-23 — seventeen sources declare one).

**F18 — Numbering.** 110 is the next free number: a glob of `1??-*.md` at the repo root on 2026-09-23 returns 100, 101, 102, 104, 105, 106, 107, 108 and 109 among its hits, **and no 110**. ⚠ **103 is a VACATED GAP** — no file in the tree, and `grep -n "^103\|103-" PLAN-STATUS-ARCHIVE.md` returns nothing. **It is not a missing plan and must not be reused.**

**F19 — Neighbouring plan states, read from each file's own `**Status**:` line on 2026-09-23.** `102` *"Phase 0 OPEN"*; `104` *"Phase 0 NOT STARTED"*; `105` *"Phase 0 PENDING"*; `106` *"Phase 0 OPEN"*; `107` *"Phase 0 OPEN"*; `108` *"Phase 0 CLOSED 2026-09-21 by a blanket maintainer directive … Build phases MAY start. NOTHING IS BUILT."*; `109` *"Phase 0 OPEN"*. **SIX plans ahead of this one have an unratified Phase 0 and a seventh is ratified-but-unbuilt** (Correction 3). Plans execute in numeric order, so **this plan will not be built soon, and that is expected.**

**F20 — How a flag actually reaches this command.** Established through the `claude-code-guide` agent — **the channel CLAUDE.md mandates for Claude-Code-integration facts** — which fetched `https://code.claude.com/docs/en/slash-commands.md` on 2026-09-23.

⚠ **READ THE VOLATILITY WARNING BEFORE THE FACTS.** That URL was fetched **three times on 2026-09-23** — by the plan's author, by the instruction reviewer, and by the agent — and **the three reads returned three different frontmatter field lists** (five fields, about eleven, about twenty). **This F-item therefore records NO field-list enumeration**, because the list is the part most likely to rot and the part the three reads disagreed on. **The volatility is itself the fact: it strengthens Phase 3's mandatory re-check rather than weakening it.**

**The four facts this plan is load-bearing on, each verbatim:**
- **A dedicated `arguments:` key EXISTS and is POSITIONAL-ONLY** — *"Named positional arguments for `$name` substitution in the skill content. Accepts a space-separated string or a YAML list. Names map to argument positions in order."* ⚠ **A flag-shaped argument such as `--auto-approve` is NOT expressible through it**, and the documentation discusses no flag-style syntax anywhere. **So `arguments:` was CONSIDERED and REJECTED as the flag's mechanism** (OQ-3).
- **The unplaceheld-argument append is confirmed** — *"When no placeholder receives an argument, Claude Code appends them as `ARGUMENTS: <value>`."*
- **`disable-model-invocation:` is current** — *"Set to `true` to prevent Claude from automatically loading this skill. Use for workflows you want to trigger manually with `/name`. Also prevents the skill from being preloaded into subagents and from running when a scheduled task fires with the skill as its prompt. Default: `false`."*
- **`allowed-tools:` pattern syntax is current** — *"Tool patterns follow this format: `ToolName(pattern)` or `ToolName(pattern *)`"*.

**Three existing repo conventions are CONFIRMED CORRECT by this read and must not be flagged as defects anywhere:** the `name:` key every command source carries (*"Display name shown in skill listings. Defaults to the directory name."*), the `disable-model-invocation: true` on the four human-typed-only commands, and `main.md`'s `Bash(.devforge/lib/implement_helper resolve-next-task *)` allowed-tools form.

⚠ **Two consequences for this plan.** First, **`/devforge:implement --auto-approve` already delivers that text to the orchestrator today**, with `argument-hint: ""` and no placeholder anywhere in the body — **the flag's arrival is not what has to be built; its MEANING is.** Second, **the in-repo precedent for an explicit placeholder is `/devforge:audit`**, whose Phase 1.1 heading — *"Resolve mode from `$ARGUMENTS`"* — passes `-- "$ARGUMENTS"` to `audit_helper resolve-mode` (`src/commands/audit/main.md:114`, `:118`). ⚠ **A future session re-establishes every one of these facts through `claude-code-guide` rather than trusting this paragraph — and rather than fetching the URL directly, which is not the mandated channel** (OQ-3, Phase 3).

**F21 — What `skip` actually does, and why an auto-`skip` is the dangerous arm.** `src/commands/implement/main.md:311`–`:322`, the Stage B `skip` path: step 1 `git -C <source_root> reset --hard <checkpoint_sha>`; step 2 `mark-skipped`, which *"sets `**Status**: Skipped` in the task file and rewrites the Status cell of the matching `tasks/README.md` index row"*; step 3 clear `wip.md`; **step 4** *"If this task's `produces` feed a downstream task's `expects`, warn the user before the skip lands that downstream tasks may be affected."*; **step 5** *"(`resolve-next-task` treats `Skipped` as satisfied for dependency resolution, so downstream tasks are not permanently blocked.)"* ⚠ **A grep of that exact string returns exactly TWO hits in the file — step 5 itself at `:322`, and PHASE 0's `skip` arm at `:75`.** ⚠ **It is NOT at `:100`**: that line is PHASE 1 prose about `depends_on` being *"all `Complete` or `Skipped`"* — the same rule in the resolver's own words, **related in substance and not a second occurrence of the sentence.** ⚠ **Under the flag, step 4's warning has no recipient**, and step 5's satisfied-dependency rule then advances downstream tasks against an `expects` nothing produced. **Load-bearing for D4.**

**F22 — Custom commands have been MERGED INTO SKILLS, and the emitted layout keeps working.** Established through `claude-code-guide` on 2026-09-23 (same fetch as F20), verbatim: *"Custom commands have been merged into skills. A file at `.claude/commands/deploy.md` and a skill at `.claude/skills/deploy/SKILL.md` both create `/deploy` and work the same way. Your existing `.claude/commands/` files keep working. Skills add optional features: a directory for supporting files, frontmatter to control whether you or Claude invokes them, and the ability for Claude to load them automatically when relevant."* ⚠ **No deprecation timeline, no migration expectation, no behaviour change, and the same `/namespace:name` invocation.** **This plan depends on the emitted `.claude/commands/devforge/<name>.md` layout continuing to work (F16), and this fact is why that dependency is sound.**

⚠ **The broader question — whether this framework should migrate its emitted layout toward `.claude/skills/` — is explicitly OUT OF SCOPE for this plan and has NO OWNER.** It is framework-wide, it touches every one of the 21 promoted commands and the emitter that writes them, and it is incomparably larger than an auto-approve flag. **It is recorded here as a fact and NOT as a decision or an open question: no phase of this plan may act on it, and a future session must not read this paragraph as unfinished business belonging to plan 110.**

---

## Coordination with the neighbouring open plans

⚠ **Sibling plans are referenced by TITLE throughout this plan, because plan numbers in this checkout have already moved** — `102-SPECIFY-IN-PLACE-REVISION-PLAN.md` records that it was drafted as 102, briefly renumbered to 103, and returned to 102 the same day. **If a filename given here does not resolve, find the plan by its title — `grep -l "Scope Rule Downstream Regime Plan" *.md` — never by assuming a number.**

**No neighbouring plan writes `src/commands/implement/`, `src/devforge/lib/_implement/` or `implement_helper`.** Verified 2026-09-23 by two match-only greps — `_implement|implement_helper|implement/main|implement/references` and `commands/implement` — across `10[2-9]-*.md`. They return exactly **two** hits, and **both sit inside read-only grep RECORDS rather than scope claims**: `108`'s **Anchor F**, whose own `grep -rln` over five command directories including `src/commands/implement` *"returns **no hits**"*; and `102`'s **F4**, which names `_implement/_cmds_session.py:247` as the single hit of its own grep. ⚠ **`102`'s F4 is a fact this plan's Phase 2 MAY falsify, depending on the shape OQ-2 chose** — a new `def cmd_update_*` in that module changes that grep's answer, while a new flag on the existing verb does not, and neither does a read verb named outside that grep's verb family (Phase 2's Verify holds all three branches and requires the phase to record which one it took). **Whoever builds second re-derives it; neither builder may read the other's committed work as a defect.**

### Shared surfaces, and the rule that binds

- **`src/CLAUDE.md` — three plans write it, in DIFFERENT regions.** The Universal Sections Integrity Plan edits **one clause in the `#### /devforge:constitute` catalog entry**; the Scope Rule Downstream Regime Plan edits **`### Always` item 17 and states *"Nothing is inserted anywhere else, and no other file changes"***; this plan's Phase 5 region is **the `/devforge:implement` lines at `:62` and `:102`, plus the classify-sites at `### Always` items 6 and 13**. The Intake Provenance Continuity Plan and the Re-entry Chain Continuity Plan both carry *"no `src/CLAUDE.md` edit"* as an explicit non-goal. ⚠ **The regions do not overlap, but the FILE is contended** — and the Scope Rule Downstream Regime Plan records it as *"dirty with another session's work"* on 2026-09-21, prescribing a staged single-hunk apply for exactly that reason. ⚠ **That is its 2026-09-21 reading, not a 2026-09-23 one: re-derive the file's state from `git status` — then stage by hunk and check `git diff --cached --stat`, never the unstaged view.**
- **`DEVELOPMENT-STATUS.md` — one plan EDITS a numbered item; five carry a classify line.** The Scope Rule Downstream Regime Plan's Phase 3 edits **item 20**; plans 104, 105, 106, 107 and 109 each carry an *"edit or a recorded verified no-op"* docs bullet. This plan's region is **item 17 (`:113`) and the `### Context Maintenance` / `### Crash Recovery` blocks (`:121`–`:133`)**. ⚠ **Item numbers and line digits BOTH drift here** — that neighbour's own Trap 2 records the same rule under two different item numbers in two files.
- **`README.md` and `CHANGELOG.md`** — ledger surfaces four or more open plans touch. **Re-read live; never edit into a released version block.**
- **`src/commands/breakdown/main.md` — this plan is the only one of the eight that writes it** (OQ-7, Phase 4). ⚠ **If a neighbour's scope later expands to that file, this line stops being true — re-derive it from their live text, not from here.**
- **The rule that binds, in one sentence: whoever lands first, the next re-reads LIVE.** Every shared surface is read at build time and every edit is re-derived from what is actually there — never from a pre-computed diff, never from a sibling plan's site list. **The rule binds the READ, not the edit.**
- ⚠ **This plan is SEVENTH in the queue and will sit unbuilt for a long time.** Every `file:line` below was true on 2026-09-23 and **will** have drifted; `## When resuming work` step 3 is the first action of any build session, not an optional one.

---

## Phase 0 — ratification

Nothing below is ratified. Each item states the decision, its options where they exist, a recommendation, and the strongest counter-argument, **recorded honestly rather than answered away**. **Every flag name, field name, option token, note token and filename this section proposes is PROPOSED and UNRATIFIED**; no phase may quote one until Phase 0's close record fixes it. Proposed emitted wording is **substance, not final text**: the builder may reword, but every element named must survive. **No emitted sentence may name plan vocabulary** ("D3", "plan 110", "Phase 0"); real headings such as `PHASE 7` or `Stage A` are fine. ⚠ **`src/commands/implement/main.md` already carries an EARLIER plan's `D1`–`D4` tokens (F5) — no phase may add one, reuse one, or read one as this plan's.**

### D1 — The flag is named `--auto-approve`

**RECOMMEND `--auto-approve`.** It names exactly what it removes: the per-task approval. It does not claim to remove the halts.

**Counter-argument, recorded:** `--auto` is terser and sits better beside `/devforge:audit`'s flag register (F17), where the flags are short and lowercase.

**Rebuttal.** **`--auto` overclaims.** Under D4, D5 and D6 the loop still halts on a conflict, on a could-not-converge item, on a gate-block, on unavailable tooling, and at crash recovery — and under D10 it stops at every declared checkpoint. A future session reading `--auto` will expect *never asks anything* and be surprised by the first `conflict` item, which is exactly the surprise D4 exists to preserve. **A flag name that has to be corrected by its own documentation is the wrong name.**

### D2 — The flag does NOT disable the gate; it collapses it onto `review_checkpoint`

**The proposal.** Under `--auto-approve`, a task whose `review_checkpoint` is `false` takes the auto path at Stage A (D3) and auto-`approve`s at Stage B. **A task whose `review_checkpoint` is `true` runs the gate exactly as today** (D10). Every other stop stays (D4, D5, D6). **No cap moves, no reviewer is skipped, no forcing-functions rule is disabled.**

**Why this and not a new policy.** The checkpoint policy already exists, is already authored by a documented placement rule, is already adjustable by the user at `/devforge:breakdown`'s Phase 4 approval gate, and is already reported back as a count and a table (F8). **The flag consumes a policy the user wrote; it does not invent one.**

**RECOMMEND D2.** ⚠ **With a sub-fork this decision must settle rather than inherit, because F8 shows the field's reported semantics and v2's gate position disagree:**
- **Arm (i), RECOMMENDED — the checkpoint stop is that task's OWN Stage A/B gate**, run in full after the work and before the commit. **The diff exists there, the gate machinery lives there, and nothing new is built.** Its cost is that `/devforge:breakdown`'s *"(before tasks [list])"* wording (F8) becomes misleading and Phase 4 must repair it.
- **Arm (ii), rejected — a v1-shaped stop BEFORE dispatching task N.** It matches the field's current wording and v1's position (F11), but v2 has no pre-dispatch prompt at all: it would be a **sixth** `AskUserQuestion` site, contradicting F4's five, and it would stop the user before there is anything to look at.

**Counter-argument to D2 itself, recorded and NOT answered away:** **a user who set checkpoints while they were inert may have set them carelessly.** Every breakdown ever produced by this framework carries `review_checkpoint` values chosen under the knowledge that nothing read them — the placement rule is automatic, and the Phase 4 adjustment is optional. **Activating the field retroactively changes what those values mean**, and no user consented to that meaning. **That risk is real and this plan does not dissolve it — it routes it to OQ-7.**

### D3 — Under the flag, a judgment item takes option 1 and records that it did

**The proposal.** A Stage A **judgment** item (F5) resolves to option 1 — the agent's resolution, already in the working tree — without asking, and the run records that it was not confirmed by a human, reusing F6's existing `--notes` mechanism.

**RECOMMEND D3.** F6 establishes that this exact outcome is already spec-sanctioned for an unanswered judgment question, with the reason already stated correctly: option 1 stays *"because it is the resolution already in the working tree, never because it is marked `(recommended)`"*. **Under the flag the reason is unchanged; only the trigger is declared instead of accidental.**

**Counter-argument, recorded and NOT answered away:** **that note was written for an unresponsive human, not for a declared unattended run.** Both produce the same six words in the same Completion Notes field, so a later reader cannot tell *"the user was asked twice and said nothing"* from *"the user asked for an unattended run"*. **The two are different events with different follow-ups**, and conflating them makes the task record ambiguous in exactly the place a reviewer would look. **OQ-5 poses the distinct-token question; this decision does not pre-empt it.**

### D4 — `conflict` and `could-not-converge` items HALT the loop

**The proposal.** Under the flag, a `conflict` item or a `could-not-converge` item **stops the loop** and tells the user which task stopped it and why. **Never auto-pick a reviewer's position. Never auto-`skip`.**

**RECOMMEND D4**, on two independent grounds.
- **(i) The spec already forbids both.** F5: *"Never pick either reviewer's position for the user — this item exists because PHASE 6 must not decide it on the user's behalf"*, and *"there is NO accept-the-finding-as-is option, because an open finding must never reach `approve`"*. **A flag that picked one would be the orchestrator doing what the command tells it it must not do.**
- **(ii) v1 halted on the analogous conditions.** F10: a blocked dependency, an exhausted repair budget and a failed pre-flight each stopped the unattended loop and reported. **The unattended precedent in this repository is halt-and-report, not guess.**

**Counter-argument, recorded:** **a halt on the first conflict wastes an unattended run.** The user starts a long drain, the loop stops at task 2, and they return to a stalled loop having gained one task.

**Rebuttal, and the reason the alternative is worse.** The only alternative that keeps the loop moving is auto-`skip`, and F21 says what that does: `git reset --hard` to the checkpoint, `**Status**: Skipped`, then `resolve-next-task` treats `Skipped` as **satisfied** for dependency resolution. **So downstream tasks proceed against an `expects` nothing produced, and they fail in a cascade the user never authorised** — and step 4's *"warn the user before the skip lands"* has **no recipient in an unattended run**. **A stalled loop costs one night. A cascade of tasks built on a contract that was never produced costs the feature.**

### D5 — The gate-blocked path and the tooling-unavailable path HALT

**The proposal.** Under the flag, `main.md:329`'s gate-blocked prompt and `main.md:343`'s tooling-unavailable prompt both **halt** and report. **An auto `scope-and-approve` is FORBIDDEN.**

**RECOMMEND D5.** An auto `scope-and-approve` would mark tasks `Complete` with the type-check, lint and test Done-When boxes left unticked and annotated `_(unverified — see Completion Notes)_` — a claim of completion **no one read**, produced by a flag whose whole justification is that it lowers no quality bar. ⚠ **The gate-blocked path has no `approve` option at all** (F4), so on that path there is nothing to decide: the only auto-reachable options are `repair` (needs a direction the user has not given) and `skip` (D4's cascade). **Halt is the only arm left.**

**Agreement, stated as agreement rather than dressed as a counter:** `fix-tooling` needs a human present anyway — it tells the user to install a tool or fix a configured command and end the turn — **so halting there costs nothing the flag could have delivered.**

**The honest cost, recorded:** on a machine missing one configured tool, an unattended run halts at task 1 and delivers nothing. ⚠ **That is the correct outcome and not a counter-argument** — the alternative is a feature marked Complete on checks that never ran. ⚠ **Do not widen this to "no tests configured":** a project with no test command produces a clean `pass` with an empty `test_commands_run` (`main.md:182`), not `tooling_unavailable` (`main.md:186`), and the flag never meets this path there.

### D6 — PHASE 0 crash recovery still PROMPTS

**The proposal.** The PHASE 0 recovery question (F4, `main.md:64`) is asked under the flag exactly as it is today.

**RECOMMEND D6.** It runs **once**, before the loop, and it is the only place where a human can tell an intact working tree from a corrupted one. **The flag itself may have been lost with the interrupted context**, which is D7's whole subject — so at the moment PHASE 0 runs, the orchestrator may not yet know an unattended run was ever requested.

**Counter-argument, recorded and NOT answered away:** **an unattended restart then hangs at the very first question, which is the worst possible place to hang** — before a single task has run, and precisely in the scenario the flag exists to survive.

**The alternative, named and not taken:** auto-`resume` under the flag, leaving `rollback` and `manual` reachable only interactively. It is coherent, and it is rejected here because `resume` re-enters a recorded phase on a working tree whose state nothing has verified — ⚠ **and because it depends on D7 having already restored the flag, which makes D6 and D7 a pair: a close record that ratifies auto-`resume` without ratifying D7's persistence has ratified an arm that cannot run.**

### D7 — The flag persists in `.devforge/wip.md` as an `Auto` field

**The proposal.** `.devforge/wip.md` gains an eighth field recording whether this run is unattended, so the mode survives compaction, a context reset and crash recovery.

**Why persistence at all.** Without it the flag lives only in the turn's context. After a compaction the loop **silently** reverts to interactive — it asks a question nobody is there to answer, and the run stops with no error and no report. **The failure mode is silent, and it lands precisely on the long runs the flag exists for.**

**RECOMMEND D7, with the field added at BOTH ends the tree already binds** (F14): `main.md` PHASE 2 step 2 and `references/crash-recovery.md`'s field block (the live writer and reader), **and** `_wip.py`'s format docstring, `write_wip_marker` and `_state.py`'s `ImplementState` (the code statement of the same shape). **This is not a choice about tidiness — `crash-recovery.md:7` states the rule in its own words: *"both ends must honour it."***

**Counter-argument, recorded and NOT answered away, in two parts.**
- **(i) `wip.md` is a crash-recovery marker, not a run-configuration store.** Widening its field set widens what every reader must tolerate, and the file's own documentation calls it *"a lightweight crash-recovery marker"*.
- **(ii) The two-ends rule is a rule the tree does not keep.** F14: the `Phase` vocabulary already disagrees across the two ends — the instruction says `dispatch`, the code says `agent`, and `_state.py`'s own docstring says *"seven"* for eight values. **Syncing a code path no production caller reaches is work with no runtime effect, and it entrenches a duplicate statement of a format that has already drifted once.**

**Alternatives, named and weighed:**
- **(a) Instruction-only** — add the field at the two live ends and leave `_wip.py` alone. **Cheaper and honest about what runs.** Rejected as the recommendation because it deepens the very divergence (ii) complains about, and the next session that wires the helper up would ship a writer that silently drops the mode.
- **(b) A separate run-state file** — a second artifact with its own lifecycle, its own git disposition and its own staleness question ("is this file from THIS run?"). **Rejected: `wip.md` already answers that question, because it is created per task and cleared on commit, skip or rollback.**
- **(c) Make the helper the writer** — the helper-owns-shape arrangement the rest of the framework uses. **A marker-ownership change with its own evidence bar; out of scope here, and named so a future session recognises it as a separate plan rather than a missing piece of this one.**

### D8 — Restore a per-session task counter and a context-health halt

**The proposal.** The loop counts tasks completed in the current session and **halts** when the count crosses a threshold, telling the user to compact and re-run. **A halt, not an advisory** — under the flag there is nobody to read an advisory.

**RECOMMEND D8.** This is the v1 mechanism v2 dropped (F11, F12, F13), and it is dormant-but-harmless today **only because the per-task gate makes the user stop at every task anyway.** The flag removes exactly that. ⚠ **And one live document still claims v2 has it:** `DEVELOPMENT-STATUS.md:123` describes a three-tier context health check that does not exist (F13). **Ratifying D8 makes that sentence true; declining it makes repairing that sentence Phase 5's job. Either way the line is this plan's to settle, because this plan is what read it.**

**Counter-argument, recorded and NOT answered away:** **a task counter is a poor proxy for context pressure.** Five large tasks with wide diffs and four review-panel rounds each can cost more context than fifteen one-line ones. A counter that halts a cheap run at task 6 and lets an expensive run past task 3 is measuring the wrong thing — **and this plan measures nothing, so it cannot say what the right threshold is** (OQ-1).

### D9 — An end-of-run report

**The proposal.** When an unattended run ends — drained, halted or stopped — it prints one report: tasks auto-approved, Stage A resolutions auto-taken, checkpoints honoured, tasks remaining, and **the halt reason when the loop stopped**, modelled on v1's `## Multi-Task Final Report` (`_multi-task-continuation.md`, F9).

**RECOMMEND D9.** The user was not present. **The report is the only artifact that tells them what was decided for them**, and the halt reason is the one thing no other surface carries.

**Counter-argument, recorded:** it duplicates what `git log` and the task index already show — one `[WIP]` commit per approved task, one `Status` cell per row.

**Rebuttal, partial and honest.** The per-task facts ARE duplicated, and the plan concedes it. **What is not duplicated is the aggregate and the halt reason**: `git log` does not say which Stage A resolutions were taken without a human, and a loop that stopped leaves **no** artifact naming why. ⚠ **That is an argument for a short report, not a long one** — and OQ-4 decides whether it lands on disk at all.

### D10 — `Review checkpoint: Yes` is a STOP even under the flag

**The proposal.** Stated as its own decision, so no future phase can quietly weaken it: a task whose `review_checkpoint` is `true` runs the full Stage A/B gate under the flag, and the Stage B presentation carries **the preceding auto-approved tasks' contract summaries** (`expects` / `produces`) the way v1's checkpoint gate did (F11).

**RECOMMEND D10.** It is the point of D2, and D2 without it is a flag that skips every gate.

**Counter-argument — none on the principle, and this plan says so rather than manufacturing one.** ⚠ **There is one honest COST, and it is not an argument against the decision:** v2 assembles no multi-task summary anywhere. `expects` and `produces` arrive on the per-task resolve payload (`_cmds_resolve.py:383`–`:384`) and are not accumulated, and `.devforge/session-state.md` keeps only the last three task modifications (F13). **So the contract summaries for the preceding run of auto-approved tasks must be held across loop iterations or re-read from the task files, and the phase that builds this owes that explicitly.**

### OQ-1 — The context-health threshold

v1 used 6+ tasks completed in one session, with 1-2 light and 3-5 moderate below it (F12).
**RECOMMEND the v1 threshold — halt at 6** — as the only number this repository has ever used, adopted for continuity rather than for correctness.
**Counter, recorded:** it is a number with no measurement behind it, imported from a command whose per-task context cost was different (v1 had no four-reviewer panel). **Anything keyed on something better — diff size, review-panel rounds, tasks-since-last-compaction — is a guess this plan cannot price**, because nothing here is measured.
**Alternative:** make the threshold configurable. ⚠ **That opens a `/devforge:configure` field**, with the schema, render, default and post-update-WARN surface plan 101 documents — **a cost this plan should not pay for a number nobody has measured.**

### OQ-2 — Where the session counter lives

**RECOMMEND `.devforge/session-state.md`** — v1's own home, already written per approved task by an existing verb with an existing CLI (F13), already read by the orchestrator at session start per `src/CLAUDE.md`'s `## Session Continuity`, and already gitignored as a runtime artifact.
**Counter, recorded:** **the counter needs a READ path and there is no verb for one.** `_cmds_session.py` defines exactly one command and it writes (F13), so the count comes back only through the orchestrator's own Read of the file — an LLM parsing a number out of markdown, which is the shape the helper-owns-shape principle exists to avoid.
**Alternative:** put it beside D7's `Auto` field in `wip.md`. ⚠ **It does not survive there: `wip.md` is CLEARED on commit, skip and rollback** (F14, `main.md:39`), so a per-task counter stored in it resets every task. **Whoever answers this must answer the clearing question explicitly, or the alternative ships a counter that is always 1.**

### OQ-3 — How the flag is parsed, and whether the body gains a placeholder

**The mechanism is settled by F20 and only the placement is open.** A dedicated `arguments:` key exists and is **POSITIONAL-ONLY** — *"Names map to argument positions in order"* — so **a flag-shaped `--auto-approve` is not expressible through it, and it is CONSIDERED AND REJECTED here rather than left unmentioned.** `argument-hint` is an autocomplete hint that parses nothing. **That leaves reading the flag out of the command text as the only available mechanism**, and an unplaceheld argument already arrives appended as `ARGUMENTS: <value>`.
**RECOMMEND an explicit `$ARGUMENTS` placeholder in the body**, on `/devforge:audit`'s precedent (F20), because relying on the appended fallback puts the flag's arrival at the END of a 363-line command body, far from the phase that must act on it.
**Counter, recorded:** `/devforge:audit` pairs its placeholder with a helper verb (`resolve-mode`) that owns the parse, and **this plan proposes no helper verb** (`## Non-goals`), so the placeholder would be read by the orchestrator directly — a shape that file does not currently have.
⚠ **Whatever this resolves to, every fact behind it is re-established through `claude-code-guide` at build time and not taken from F20** — three reads of that page on one day returned three different field lists. ⚠ **`argument-hint` in this file is at `:3`, not `:4`** (F1).

### OQ-4 — Does the end-of-run report land on disk?

**RECOMMEND transcript only.** Nothing in `/devforge:implement` writes a run-scoped artifact today — its outputs are the per-task commit, the task file, the index row, `wip.md` and `session-state.md` (`main.md:37`–`:40`) — and a new on-disk artifact needs a path, a git disposition in `src/devforge/storage-rules.md`, and a lifecycle answer for a run that is re-entered after a halt.
**Counter, recorded:** **a transcript-only report dies with the context**, and the user of an unattended run is by definition not watching the transcript when it is produced. ⚠ **This is the same argument D7 uses for persistence**, and answering OQ-4 "transcript only" while ratifying D7 accepts an asymmetry: the MODE survives a compaction and the REPORT does not.
**Alternative:** fold the aggregate into `.devforge/session-state.md`, which already survives and is already read at session start — at the cost of its ≤40-line fixed-size contract (F13).

### OQ-5 — Does the auto path need its own Completion-Notes token?

**RECOMMEND a DISTINCT token**, so a later reader can tell *"asked twice, no answer"* (F6) from *"unattended by request"* (D3). **The two are different events and lead to different follow-ups.**
**Counter, recorded:** a second token doubles what a reader of Completion Notes must recognise, for a distinction only an auditor will ever make. ⚠ **And it is the cheaper half of the trade at ratification and the expensive half afterwards** — the token is quoted in the spec and written into every task file an unattended run touches.
⚠ **This plan proposes no literal spelling.** Fix it in the close record, and fix it **in the same line as OQ-1's threshold is NOT required** — but it MUST be fixed before Phase 3 quotes it.

### OQ-6 — CHANGELOG landing, and already-shipped installs

**Posed, not decided here.**
- **CHANGELOG landing:** the entry goes under whichever unreleased section is in flight, **re-verified LIVE at build time**, never as an edit into a released version block. ⚠ **Whether such a section exists is a live question — neighbouring plans record contradictory states for it on different days. Read `CHANGELOG.md` at build time; trust no plan on this.**
- **Back-porting: RECOMMEND an explicit NON-GOAL**, per the standing house rule — consumers arrive via `install.sh` / `update.sh`. An install that has not updated keeps the interactive-only loop, which is today's behaviour and harms nothing.
- **Counter, recorded:** the flag is inert on a shipped install until it updates, and **a user who types `--auto-approve` there gets the documented appended-`ARGUMENTS` fallback with no phase that acts on it** (F20) — i.e. a flag that is silently ignored rather than rejected. ⚠ **The plan does not fix that and says so.**

### OQ-7 — Does `/devforge:breakdown` change now that `review_checkpoint` becomes load-bearing?

**The risk, stated plainly.** The placement rule (F8) was written for a field nothing consumed. Users have been accepting the auto-placement at the Phase 4 approval gate **without any consequence attaching to it**, and every existing feature directory in every install carries checkpoint values chosen under those stakes. **D2 changes the stakes retroactively.**
**RECOMMEND the minimum that removes the surprise: `/devforge:breakdown`'s summary line says what a checkpoint now DOES** (F8's `:627` site, which also needs arm (i)'s *"before tasks"* repair), **and the placement rule keeps its three automatic conditions unchanged.**
**Counter, recorded:** **re-tuning the placement rule is the change that would actually matter**, and this recommendation deliberately does not make it — a rule authored for an inert field is not obviously the right rule for a live one, and this plan has measured nothing that would tell it which conditions belong.
**Alternative:** leave `/devforge:breakdown` untouched entirely, accepting that the first unattended run on an old breakdown honours checkpoints the user does not remember setting.

### OQ-8 — Is the flag permitted in wrapper mode at all?

**What wrapper mode does here.** `main.md:294`: in wrapper mode `wip-commit` *"commits ONLY the source `touched_files` to the **source** repo on its branch (deriving the `[TICKET-ID]` from the source branch per D2)"* and leaves the wrapper artifacts uncommitted; `main.md:37` gives the subject shape `[TICKET-ID] - <title>`, *"since it lands in the client-owned source repo"*; and `main.md:154` forbids the agent from writing or even MENTIONING a framework artifact in that tree, a rule enforced by PHASE 5's isolation check and `code-reviewer`'s framework-mention check.
**RECOMMEND permitting it, with no wrapper-specific carve-out.** The flag removes approvals and changes nothing about what is committed, where, or under what subject; the isolation check and the mention check are PHASE 5 and PHASE 6 mechanics that run unchanged, and an isolation failure is a gate-block, which D5 halts on.
**Counter-argument, recorded and genuinely open:** **unattended committing into a client-owned repository is a different kind of act from unattended committing into your own.** The framework's whole wrapper posture is that the client's repo must carry no trace and no surprise; a run nobody watched, landing commits under a ticket ID, is a surprise of a kind the rest of that posture is built to prevent. ⚠ **This is the one open question where the recommendation is weakest, and the close record should say so rather than rubber-stamp it.**
**Alternative:** refuse the flag when `WORKSPACE_MODE` is wrapper, and say why in the refusal.

### Phase 0 close record

**NOT CLOSED — the plan was DECLINED AS A WHOLE on 2026-10-03; see the `**Status**:` line at the top of this file.** No item of D1–D10 or OQ-1–OQ-8 was ratified, amended or individually declined, and the requirements below, kept as written, describe the record a close would have needed. Had it closed, this record would have had to name **each** of D1 through D10 and OQ-1 through OQ-8 with its outcome (ratified / amended / declined), state whether per-item deliberation was supplied, state whether the close was an explicit pick or a delegation (plan 98's D1 distinction), and say which files the outcomes put in scope. **Every counter-argument stays where it is written — a ratified decision with its counter-argument deleted cannot be re-opened honestly.** ⚠ **Ratification changes no evidence class: NO consumer incident, none claimed, NOTHING MEASURED.**

#### Verify

- The record names **each** of D1–D10 and OQ-1–OQ-8 with an explicit outcome. **No item is silently omitted**, and each is checked **BY NAME, never against a range** — a range reads as complete while a hand-written enumeration beside it drops a member, and an item with no Verify line cannot fail.
- **D2's sub-fork is closed explicitly** — arm (i) (the task's own Stage A/B gate) or arm (ii) (a pre-dispatch stop). **A close that ratifies D2 without naming an arm has not closed D2**, because Phase 3's branch position and Phase 4's `/devforge:breakdown` wording both depend on it.
- **D6 and D7 are closed as a PAIR, or D6's auto-`resume` alternative is explicitly declined.** Auto-`resume` cannot run without D7's persistence.
- **D7's outcome names which ENDS are edited** — the two live ends alone (alternative (a)), or the live ends plus `_wip.py` and `_state.py` (the recommendation). **Phase 1 exists only under the latter.**
- **D8's outcome states what happens to `DEVELOPMENT-STATUS.md:123`** — made true by the build, or repaired by Phase 5 as a false line. **It is never left implicit.**
- **OQ-2's outcome answers the `wip.md` clearing question** if it picks the `wip.md` home; an answer that does not is not an answer.
- **OQ-5 fixes the token's literal spelling**, or explicitly declines a second token. Phase 3 may not invent one.
- **OQ-8's outcome records that it is the weakest recommendation in this section**, whichever way it goes.
- It states whether per-item deliberation was supplied, and whether the close was an explicit pick or a delegation.
- **Every counter-argument above is still present, unshortened** — including D2's retroactive-meaning concession, D5's honest cost, D7's two-part counter, D8's proxy objection and D9's partial rebuttal.
- The record says what the outcomes put in scope: **D1 fixes the flag's spelling every later phase quotes**; **D2 decides whether Phases 1–5 exist at all**; **D2's arm decides Phase 3's branch position and Phase 4's `/devforge:breakdown` edit**; **D7 decides whether Phase 1 exists**; **D8 decides whether Phase 2 exists**; **OQ-2 decides which file Phase 2 writes**; **OQ-3 decides whether Phase 3 adds a `$ARGUMENTS` placeholder**; **OQ-4 decides whether Phase 3 or Phase 2 owns the report's destination**; **OQ-5 fixes the token Phase 3 emits**; **OQ-6 decides where Phase 5's CHANGELOG entry lands**; **OQ-7 decides Phase 4's scope**; **OQ-8 decides whether Phase 3 writes a wrapper-mode refusal.**

---

## Phases

Phase 0 is the `## Phase 0 — ratification` section above; **nothing below starts before its close record exists.**

**Build order, and its forced dependencies.** **Phases 1 and 2 are independent of each other and both precede Phase 3**, because Phase 3 quotes the field name and the counter's surface they create. **Phase 4 depends on Phase 0's OQ-7 answer and on D2's arm**, not on Phases 1–3. **Phase 5 runs last**, because it records what the earlier phases did. **Phase 6 is the maintainer's.**

⚠ **This plan is not shippable as Phase 3 alone under a ratified D7 or D8** — an instruction that names an `Auto` field no writer writes, or a counter nothing counts, ships a spec whose branches can never fire.

### Phase 1 — Python: the marker's code-side shape

**Exists ONLY if Phase 0 ratified D7's recommendation** (both ends). ⚠ **Under alternative (a) this phase does NOT exist, and the plan records that as an explicit outcome rather than an empty phase.**

**Route: python-engineer → python-reviewer. Every function gets a test written AND run in the same turn.** Commit by explicit path.

⚠ **This phase creates NO helper verb and NO CLI flag.** The flag never reaches Python: it arrives in the command body as text (F20), and `.devforge/wip.md` has no helper writer (F14). **A phase that adds a subparser has misread F14 and F20.**

#### Deliverables

- `src/devforge/lib/_implement/_state.py` — the new `ImplementState` field carrying the mode, with its `__post_init__` validation in the shape the other seven fields already use.
- `src/devforge/lib/_implement/_wip.py` — the field in the module docstring's `File format` block and in `write_wip_marker`'s rendered content, at the position D7's close fixed.
- `tests/lib/_implement/test_state.py` and `tests/lib/_implement/test_wip.py` — ⚠ **both files exist today; add to them rather than creating new modules.** Cases: the field written and read back; the marker round-tripped through `write_wip_marker` → `read_wip_marker`; a marker WITHOUT the field (every marker written before this change) read without raising; and `ImplementState` rejecting an invalid value for the new field.

#### Verify

- **A marker written before this change still parses**, and `read_wip_marker` returns a dict lacking the new key rather than raising — asserted with a hand-built fixture whose text omits the field.
- **The field's name is byte-identical in three places**: `_wip.py`'s docstring block, `write_wip_marker`'s format string, and the instruction text Phase 3 writes. ⚠ **Asserted by grepping the literal across `src/`, not by reading them side by side.**
- **`clear_wip_marker`'s one live call site is untouched** — `git diff` shows no change to `_implement/_cmds_commit.py`.
- ⚠ **`_state.py`'s pre-existing *"seven loop phases"* docstring and its eight-member `_VALID_PHASES` are LEFT AS THEY ARE**, and this phase records that as a deliberate no-op with the grep that shows it. **They are false before this plan and are not this plan's to fix** (F14, Trap 11).
- The targeted suite, then the full `tests/lib` suite, is green.
- python-reviewer returns SHIP-READY, or every finding is fixed.

### Phase 2 — Python: the per-session counter and its context-health surfacing

**Exists ONLY if Phase 0 ratified D8.** Its file is whatever **OQ-2** answered.

**Route: python-engineer → python-reviewer. Every function gets a test written AND run in the same turn.** Commit by explicit path.

#### Deliverables

- `src/devforge/lib/_implement/_cmds_session.py` — the counter joins the written state at the position OQ-2 fixed, with its own flag on `update-session-state`, and the ≤40-line fixed-size contract preserved.
- The matching subparser registration.
- Tests covering: the counter written and read back through the real producer; **the ≤40-line cap still holds with the counter present**; a state file written BEFORE this change loading without the key; the counter incrementing across successive calls; and the threshold's boundary — one below, at, and one above.

#### Verify

- **The ≤40-line guarantee is re-asserted, not assumed** — `_build_session_state`'s own docstring computes its maximum, and the computation is updated in the same change.
- **A `session-state.md` written before this change still loads**, and the counter reads as absent rather than as zero-by-accident.
- ⚠ **`102-SPECIFY-IN-PLACE-REVISION-PLAN.md`'s F4 records that `_implement/_cmds_session.py:247` `cmd_update_session_state` is the SINGLE hit of a `def cmd_(remove|delete|drop|update|edit|amend|replace|revise)_` grep over `src/devforge/lib/`. Whether THIS phase falsifies that depends on the shape OQ-2 chose, and the phase RECORDS which branch it took:**
  - **A new flag on the existing `update-session-state` verb adds no `def cmd_*`, so that grep's answer is UNCHANGED** — and the phase records it as a verified no-op by re-running the grep.
  - **A new function whose name matches that pattern — `cmd_update_*` above all — CHANGES the answer**, and the phase records the new count.
  - ⚠ **A read verb named outside the pattern (`cmd_read_*`, `cmd_get_*`) also leaves the answer unchanged** — the grep keys on the verb family, not on the file.
  **Either way this phase records the outcome and does NOT edit that plan's file.**
- The full `tests/lib` suite is green.
- python-reviewer returns SHIP-READY, or every finding is fixed.

### Phase 3 — Instruction: the flag, its five branches, and the contradictions it repairs

**Route: instruction-author → instruction-reviewer, plus `claude-code-guide` for every Claude-Code-integration fact.** Instruction-only: **no `.py` file changes in this phase.** **Needs Phases 1 and 2 where they exist** — it quotes the field and the counter they created. Commit by explicit path.

#### Deliverables

- **`src/commands/implement/main.md` frontmatter** — `argument-hint` gains the flag. ⚠ **It is at `:3` in this file, not `:4`** (F1). The `description:` field's tail, *"then a per-task human hard gate before any commit"*, is re-worded to survive the flag.
- **`main.md:31`, the Usage sentence** — F2's *"Per-task human approval is logically incompatible with batch forms."* is replaced. ⚠ **The replacement must not make the opposite over-claim:** the flag is not a batch form either; `resolve-next-task` still picks exactly one task.
- **`main.md:53`, the no-batch bullet** — F3 keeps its substance and stops citing a Usage sentence that no longer says what it cited. ⚠ **`/devforge:implement N` is STILL not introduced** (`## Non-goals`).
- **The arg parse** — at whatever site OQ-3 fixed, and nowhere else.
- **The `review_checkpoint` consumption** — one branch reading the key `main.md:102` already names, at the position D2's arm fixed.
- **The auto branch at all FIVE prompt sites** (F4): Stage A's three item kinds (D3, D4), Stage B (D2, D10), the gate-blocked path (D5), the tooling-unavailable path (D5), and PHASE 0 (D6).
- **`main.md:358` rule 1 and `main.md:360` rule 3** — rule 1's *"Nothing commits before `approve`"* stays TRUE and gains the sentence saying who gives the `approve` under the flag; rule 3's *"There is no batch mode"* is repaired.
- **PHASE 2 step 2 (`main.md:144`) and `references/crash-recovery.md`'s field block** — D7's field, at both live ends.
- **A NEW `src/commands/implement/references/autonomous-mode.md`** — the flag's full mechanics: what collapses, what halts, what persists, the counter, and the end-of-run report. ⚠ **No emitter change and no `_PROMOTED` change** (F16), and the filename follows the four existing references' lowercase kebab-case topic naming.

#### Verify

- **`grep -c "AskUserQuestion" src/commands/implement/main.md` returns 5**, and **each of the five carries an auto branch** — checked one site at a time, by name, never by a count alone. ⚠ **`references/crash-recovery.md` and `references/forcing-functions-gate.md` still carry one mention each and neither becomes a prompt** (F4).
- **`grep -n "logically incompatible with batch forms\|There is no batch mode" src/commands/implement/main.md` returns nothing**, and no surviving sentence in the file asserts that unattended operation is impossible.
- **`grep -n "review_checkpoint" src/commands/implement/` returns MORE than one hit**, and at least one of them is a branch rather than a key list — **the whole point of this plan is that the count was 1** (F8).
- **`grep -rn "Never pick either reviewer's position\|an open finding must never reach" src/commands/implement/main.md` still returns its two sentences, byte-unchanged** (F5) — the flag adds a halt beside them and weakens neither.
- **No emitted sentence names plan vocabulary**, and ⚠ **no NEW `D<n>` token is introduced into `main.md`**, which already carries an earlier plan's `D1`–`D4` (F5).
- **The flag name, the field name and the notes token are byte-identical everywhere they appear** — asserted by grepping each literal across `src/`, and each matches what Phase 0 ratified.
- **`git diff --stat src/commands/` lists `implement/main.md`, `implement/references/crash-recovery.md` and the new `implement/references/autonomous-mode.md` and nothing else** — ⚠ **`breakdown/main.md` is Phase 4's, not this phase's.**
- **The `claude-code-guide` check is RUN in this phase and its result recorded**, covering at minimum: how an argument reaches the command body, whether the positional-only `arguments:` key has gained any flag-style form, and whether the emitted `.claude/commands/` layout still works (F20, F22). ⚠ **A claim sourced from F20 or F22 alone does NOT discharge it** — both are 2026-09-23 reads and this phase runs later. ⚠ **The reason is recorded, not assumed: three reads of that page on ONE day returned three different frontmatter field lists (F20), so this surface demonstrably moves faster than this plan will be built.** ⚠ **The check goes through the agent, never through a direct fetch** — CLAUDE.md mandates that channel because an agent invocation leaves a trace a claimed doc-read does not.
- The live-spec tests are green: `tests/lib/test_agent_reachability.py`, `tests/lib/test_memory_lane.py`, `tests/scripts/test_claude_emitter.py`.
- instruction-reviewer returns SHIP-READY, or every finding is fixed.

### Phase 4 — Instruction: `/devforge:breakdown`, and crash recovery where D6 lands there

**Route: instruction-author → instruction-reviewer.** Instruction-only. **Scope is whatever OQ-7 ratified, plus D2's arm.** Commit by explicit path.

#### Deliverables

- **`src/commands/breakdown/main.md`** — whatever OQ-7 ratified. Under the recommendation that is the `:627` summary line, which under D2 arm (i) also loses its *"(before tasks [list])"* position claim (F8).
- ⚠ **`### Review Checkpoint Placement`'s three conditions stay byte-identical** under the recommended OQ-7 answer. **A phase that re-tunes them has exceeded OQ-7 and must return to Phase 0.**
- **`src/commands/implement/references/crash-recovery.md`** — only if D6 landed on the auto-`resume` alternative. ⚠ **Under the RECOMMENDED D6 this file's four options are byte-unchanged in this phase**, and the phase records that as a verified no-op with the grep that shows it. (Its field block is Phase 3's, under D7.)

#### Verify

- **Every `Review checkpoint` site is classified as an edit or a verified no-op, with the grep that shows it** — `breakdown/main.md` `:397`, `:506`–`:514`, `:524`, `:627`; `breakdown_helper.py` `:142`, `:1067`, `:3216`, `:3730`; `src/devforge/storage-rules.md:202`. ⚠ **The helper sites are Python and are NOT edited by this instruction-only phase** — a classification that turns into an edit has broken the phase's own contract.
- **`grep -n "before tasks" src/commands/breakdown/main.md` agrees with D2's ratified arm** — under arm (i) it returns nothing; under arm (ii) it returns the line unchanged.
- **`git diff` on `src/devforge/lib/` is EMPTY for this phase.**
- instruction-reviewer returns SHIP-READY, or every finding is fixed.

### Phase 5 — Docs sweep

**Route: instruction-author → instruction-reviewer. Docs only.** ⚠ **Apply the coordination rule before touching any shared file** (`## Coordination with the neighbouring open plans`): other sessions build in this checkout, `src/CLAUDE.md` is contended by two other plans, and several ledgers are modified by other work. **Re-read `git status`, read each file LIVE, re-derive every edit from what is there, and commit by explicit path — never `git add -A`.**

#### Deliverables

- **`CHANGELOG.md`** — one entry, placed per OQ-6's answer, with **the evidence class FIRST and the honest bounds LAST.** ⚠ **Never an edit into a released version block.**
- **`src/CLAUDE.md`** — `:62` and the `#### /devforge:implement` entry at `:101`–`:102` (F15's edit class). ⚠ **`### Always` items 6 and 13, `## Session Continuity` and `### Crash Recovery` are each an edit or a recorded verified no-op**, and `:163` is a **verified no-op** with the grep that shows it (Correction 2).
- **`README.md:79`** — F15's edit class.
- **`DEVELOPMENT-STATUS.md`** — `:113` (edit class); `:121`, `:128`–`:130` (classify).
  - ⚠ **`:123`'s three-tier context-health sentence is settled per D8's outcome** — made true by Phase 2, or repaired as a false line. **It is never left as it stands.**
  - ⚠ **`:133`'s `## Source Repo Checkpoint` sentence is ALREADY FALSE and is NOT fixed here.** It is pre-existing, this plan did not cause it, and no phase of this plan falsifies it. **It is named because it sits two lines from a block this phase reads, which makes a drive-by edit a recognised scope departure rather than an accident** (F15, Trap 11).
- **`PLAN-STATUS-ARCHIVE.md`** — this plan's own `## Index` line and its `## Entries` record. ⚠ **BOTH shapes or neither** — that file's `## Index` preamble states the rule in its own words. **No other plan's record in that file is touched.**
- **`src/devforge/storage-rules.md`** — an edit or a recorded verified no-op for the `wip.md` field set and the `Review checkpoint` line at `:202`.

#### Verify

- Every site above is recorded as an **edit or an explicit verified no-op**, with the grep that shows it.
- **`grep -rn "per-task hard gate" src/ README.md DEVELOPMENT-STATUS.md` surfaces no sentence that still promises an unconditional per-task gate.** ⚠ **Hits in `CHANGELOG.md` and in plan documents are FROZEN HISTORICAL RECORDS and are left alone** — each states what was true on its own date. ⚠ **This sweep does NOT reach the repo root's plan files.**
- **`DEVELOPMENT-STATUS.md:133` is BYTE-UNCHANGED**, and `git diff` proves it.
- **No line belonging to any neighbouring plan is altered or reflowed** — `git diff` on the shared files shows only this plan's own hunks, checked with `git diff --cached --stat` after staging and never on the unstaged view.
- **The CHANGELOG entry's evidence-class statement PRECEDES its honest-bounds statement**, read from the entry's own text and never inferred from section placement.
- **No ledger sentence claims any phase is consumer-validated. "Built and build-verified" is the ceiling in every line.**
- **No tracked file names a client, an install, a repo, a branch, a ticket id or any benchmark identifier.**

### Phase 6 — Consumer e2e on a real feature — user-driven HARD GATE, DEFERRED by default, NOT run

⚠ **Deferred by default, per the house pattern, and explicitly NOT WAIVED.** Everything Phases 1–5 ship is **build-verified at best and NEVER consumer-validated** until this phase runs, and **"done" never means Phase 6 passed.**

- **Fixture:** a testForge20 feature with at least one `Review checkpoint: Yes` task and at least three `No` tasks. ⚠ **The frozen benchmark install is never touched.**

The anchors are known-answer cases, **scored explicitly and in their pairs**:

1. **A feature drained under the flag with no conflicts** — every `No` task auto-approves and commits; the run reaches `all-complete`. **PAIRED WITH 2.**
2. **The SAME feature's `Yes` task STOPPED and asked**, with the preceding tasks' contract summaries present (D10). ⚠ **Anchors 1 and 2 are scored as a PAIR: a flag that never stops passes 1 and fails 2; a flag that stops everywhere passes 2 and fails 1.** **Record the number of tasks auto-approved as a NUMBER**, not as "it worked".
3. **A planted `conflict` item HALTS**, and the halt names the task and the reason (D4). ⚠ **Scored on its own. `skip` must not have been taken, and `git log` must show no commit for that task.**
4. **A planted forcing-functions exit 2 HALTS** (D5), and no task is marked `Complete` with an unticked verification box.
5. **A compaction mid-run leaves the mode intact** (D7) — the loop continues unattended after the context resets. ⚠ **If D7 landed on alternative (a), this anchor is RECORD ONLY.**
6. **The context-health halt fires at its threshold** (D8, OQ-1). ⚠ **Scored if D8 was ratified; RECORD ONLY if declined.** **Record the tasks-per-session count as a NUMBER.**
7. **A wrapper-mode run** — scored per OQ-8's outcome: permitted, the source repo carries the expected `[TICKET-ID]` subjects and no framework trace; refused, the refusal fires and names the reason.

#### Verify

- **Every anchor is scored explicitly — stated, not summarized — with anchors 1 and 2 scored together and anchor 3 scored on its own.**
- **If an anchor fails, record the negative with the artifacts and NAME THE MECHANISM before proposing anything:** a `Yes` task that did not stop is **D2's arm or the `review_checkpoint` branch**; a `No` task that stopped is **the branch's polarity**; a conflict that did not halt is **D4's branch**; a commit on a halted task is **D5**; a mode lost after compaction is **D7's persistence**; a counter that never fires is **Phase 2's threshold**. ⚠ **They have different fixes.**
- ⚠ **A clean run shows the flag behaves on one planted feature. It never shows that the per-task gate cost anything, that anyone wanted the flag, or that an unattended run is safe in general.**

---

## Non-goals

⚠ **On this plan's SHAPE, stated because a departure must be argued rather than silent: this file follows `109-REENTRY-CHAIN-CONTINUITY-PLAN.md`'s Phase-0-OPEN template and therefore carries NO `## Residuals` section.** `101-NON-WEB-STACK-READINESS-PLAN.md` has one, and that is the right shape for a plan that reached DONE — residuals accumulate across a build, and **no build has happened here.** The pre-existing defects found while drafting are carried instead as **F-items (F14, F15), the last bullet of this section, and Trap 11**, each with the same disposition a residual would have given them: named, dated, attributed to a cause other than this plan, and explicitly not fixed. ⚠ **F13's `DEVELOPMENT-STATUS.md:123` is a drafting-time find too, and it is deliberately NOT in that group:** it is the one stale statement a decision of this plan REACHES, so D8's outcome settles it either way — made true by the build, or repaired by Phase 5 (D8, Phase 5's Deliverables, this section's last bullet, Trap 11). **A future session adding a `## Residuals` section must MOVE the F14/F15 content rather than duplicate it, and must leave `DEVELOPMENT-STATUS.md:123` out of it — a residual is by definition unowned, and that line has an owner.**

Each is argued, not merely listed.

- **No batch task targeting.** `/devforge:implement N`, a range form and an `all` form stay absent; F3's bullet stands and Phase 3 keeps its substance. ⚠ **A careless reader will conflate "unattended" with "batch" — they are different: `resolve-next-task` still picks exactly ONE task and the loop still drains in dependency order.** **The flag changes who answers the gate, never how many tasks are resolved at once.**
- **No cap moves.** The self-repair cap (3) and the review-panel cap (3) are helper-owned and stay helper-owned (`main.md:359`). **The flag must never lower a quality bar; it removes approvals and nothing else.**
- **No edit to `src/devforge/lib/_implement/_cmds_gate.py` or `_cmds_review_panel.py`.** Neither is reached by any decision here; the four reviewers fan out unchanged and the forcing-functions gate dispatches unchanged.
- **No reviewer skipped, no forcing-functions rule disabled, no verification scoped away.** An auto `scope-and-approve` is forbidden by D5 for exactly this reason.
- **No new helper verb and no new `verify-*` gate.** The flag never reaches Python (F20), so there is nothing for a verb to parse. Phases 1 and 2 extend existing functions and one existing verb.
- **No re-tuning of `/devforge:breakdown`'s placement rule** under the recommended OQ-7 — the three automatic conditions stay as authored. A different rule is a different decision with its own evidence bar.
- **No change to what is committed, where, or under what subject.** `wip-commit` is untouched in both modes.
- **No `disable-model-invocation` change.** `/devforge:implement` is model-invocable today and stays so.
- **No back-port into shipped installs** (OQ-6). They arrive via `install.sh` / `update.sh`.
- **Nothing is done to any installed consumer.** A frozen benchmark install exists; **this plan neither updates nor edits it and sends it no message.**
- **No repair of the THREE pre-existing stale statements this plan FOUND** — `DEVELOPMENT-STATUS.md:133`, `_state.py`'s *"seven loop phases"* docstring, and `_cmds_preflight.py`'s *"Phase 9"* at `:12`, `:310` and `:323` (F14, F15). **They are named so they are not edited by accident, not so they are fixed here.** ⚠ **`_cmds_preflight.py:323` is the one that reaches a USER** — it sits inside the stale-marker stderr string rather than in a docstring — **which makes it the most tempting drive-by of the three, and the reason it is named rather than merely known.** ⚠ **`DEVELOPMENT-STATUS.md:123` is the exception and is NOT in this non-goal: D8's outcome reaches it either way.**
- **Anything specific to the benchmark**, and any client, install, repo, branch, ticket id or benchmark path in this repo.

---

## Context for next session

⚠ **Evidence class, repeated: NO consumer incident, none claimed, NOTHING MEASURED. ONE maintainer request plus a code read of this tree on 2026-09-23.** ⚠ **F9–F12 are reads of the `release/v-1.23.0` branch and are re-derived with `git show release/v-1.23.0:<path>`, never from a working-tree path.** ⚠ All line digits drift — **grep the quoted text, never the digits.**

**The one sentence that governs everything here:** **the flag does not disable gates — it collapses the per-task gate onto the checkpoints the user already declared, and every stop that protects correctness stays.**

### Honest bounds

- **Nothing is measured.** No rate of use, no time saved, no cost of the per-task gate, no context cost per task. **No number was computed before this plan and none will be after it** short of Phase 6's recorded anchors, which are observations on one planted feature.
- **The checkpoint policy was authored under different stakes.** Every existing breakdown carries `review_checkpoint` values chosen while nothing consumed them (OQ-7). **The flag makes them binding retroactively, and no user consented to that.**
- **The context-health threshold is v1's number with no measurement behind it** (OQ-1). A counter that halts a cheap run early and an expensive run late is measuring the wrong thing, and this plan cannot say what the right thing is.
- **A halt is still a stalled run.** D4 and D5 are correct and they are not free: an unattended overnight drain can stop at task 2 and deliver one task. **The plan chooses that over a cascade** (F21) and does not pretend the cost is zero.
- **D3 delegates a shape decision.** Under the flag the agent's resolution is kept without a human reading it. The note records that it happened; **nothing checks it was right.**
- **The mode's persistence rests on a file nothing but the orchestrator writes** (F14). If a future session moves the marker to helper ownership, D7's field moves with it.
- **Three pre-existing stale statements were found and are not fixed** (`DEVELOPMENT-STATUS.md:133`, `_state.py`'s *"seven"*, and `_cmds_preflight.py`'s *"Phase 9"* — the last of which reaches a user through a stderr string). **Recorded, not repaired.**
- **Six plans ahead of this one have an unratified Phase 0 and a seventh is ratified-but-unbuilt** (F19). **This plan will not be built soon, and that is expected.**

### Traps

**Trap 1 — reading `--auto-approve` as "never asks".** It halts on a conflict, a could-not-converge item, a gate-block, unavailable tooling and crash recovery, and it stops at every declared checkpoint (D4, D5, D6, D10). **D1's counter-argument is exactly this trap, which is why `--auto` was rejected.**

**Trap 2 — conflating "unattended" with "batch".** `/devforge:implement N` is still not introduced, `resolve-next-task` still picks one task, and dependency order is untouched (`## Non-goals`, F3).

**Trap 3 — auto-`skip` on a conflict.** It resets the tree, marks the task `Skipped`, and `resolve-next-task` then treats `Skipped` as **satisfied**, so downstream tasks build on an `expects` nothing produced — and the spec's own *"warn the user before the skip lands"* has no recipient (F21, D4).

**Trap 4 — auto-`scope-and-approve`.** It marks tasks `Complete` with type-check, lint and test boxes unticked and annotated `_(unverified — see Completion Notes)_` — completion nobody read (D5).

**Trap 5 — reading `main.md`'s `D1`–`D4` as this plan's.** That file carries an earlier plan's decision vocabulary at `:143`, `:236`, `:250` and `:294` (F5). **No phase may reuse those tokens, and no phase may add a new one.**

**Trap 6 — assuming the flag needs a parser before it can arrive.** `argument-hint` parses nothing, and an unplaceheld argument is already appended as `ARGUMENTS: <your input>` (F20). **What has to be built is the flag's MEANING, not its arrival.**

**Trap 7 — editing `argument-hint` at line 4.** In this one file it is at `:3`; `:4` is `description:` (F1). **Every other command source has it at `:4`, which is what makes the mistake easy.**

**Trap 8 — treating `.devforge/wip.md` as helper-owned.** The orchestrator writes it and reads it; `_wip.py`'s writer and reader have no production caller, and only `clear_wip_marker` is live (F14, Correction 1). **A phase that adds a helper verb for the marker has misread this.**

**Trap 9 — storing the session counter in `wip.md`.** That file is cleared on commit, skip and rollback (F14), so a per-task counter kept there is always 1 (OQ-2).

**Trap 10 — reading `src/CLAUDE.md:163` as a stale sentence.** *"Task breakdown approval → before `/devforge:implement` can start"* stays true under the flag; it is a verified no-op (Correction 2, F15).

**Trap 11 — "helpfully" fixing the three pre-existing stale statements.** `DEVELOPMENT-STATUS.md:133` sits inside the `### Crash Recovery` block Phase 5 reads; `_state.py`'s *"seven loop phases"* sits at the top of a file Phase 1 edits; and `_cmds_preflight.py`'s *"Phase 9"* sits partly in a function this plan lists as a READ-ONLY anchor — **`:310` and `:323` are inside `_check_wip_marker`, but `:12` is MODULE-LEVEL, in the module docstring above every `def`.** **All three are stale, none is caused by this plan, and an edit to any is a scope departure** (F14, F15, `## Non-goals`). ⚠ **Reading only the anchor's line range finds two of the three** — grep the file for the literal instead. ⚠ **`_cmds_preflight.py:323` is inside a user-facing stderr string, not a docstring** — which makes it look more urgent than the other two and makes the temptation to fix it stronger. ⚠ **`DEVELOPMENT-STATUS.md:123` is NOT one of these three — D8's outcome reaches it.**

**Trap 12 — counting six `AskUserQuestion` prompts.** There are five in `main.md`; `references/crash-recovery.md:32` documents the PHASE 0 one and `references/forcing-functions-gate.md:52` routes to the gate-blocked one (F4). **A sixth auto branch has been written against a misread.**

**Trap 13 — ratifying D2 without naming its arm.** The field's report says *"before tasks"* and v2's only gate is after the work (F8). **"Activate the field" names no position on its own**, and Phase 3's branch and Phase 4's wording both depend on which arm was taken.

**Trap 14 — quoting a `file:line` from this plan as current.** Every anchor here was true on 2026-09-23. **Six plans ahead of this one are unbuilt and will move these digits before this plan starts.**

**Trap 15 — touching another session's plan file, or sweeping a shared ledger.** `src/CLAUDE.md` is contended by two other open plans — one of which recorded it dirty with another session's work on 2026-09-21 — and `DEVELOPMENT-STATUS.md` is edited by one. ⚠ **A neighbour's dated reading of the working tree is not this session's: re-read `git status`, read each file live, stage by hunk, check `git diff --cached --stat`, and never touch another session's plan file.**

### File anchors

**EDIT targets — a phase of this plan writes each of these:**

- **`src/commands/implement/main.md`** — frontmatter `:3`–`:4`; the Usage sentence `:31`; the no-batch bullet `:53`; the PHASE 0 prompt `:64`; the `review_checkpoint` key list `:102`; PHASE 2 step 2 `:144`; Stage A's three item kinds `:240`–`:261`; Stage B `:269`–`:272`; the gate-blocked prompt `:329`–`:332`; the tooling-unavailable prompt `:343`–`:346`; IMPORTANT RULES 1 and 3 `:358`, `:360` (Phase 3).
- **`src/commands/implement/references/crash-recovery.md`** — the field block `:9`–`:24` (Phase 3, D7); the four options `:32`–`:39` (Phase 4, ONLY under D6's alternative).
- **`src/commands/implement/references/autonomous-mode.md`** — NEW (Phase 3).
- **`src/devforge/lib/_implement/_state.py`** and **`_wip.py`** — the new field only (Phase 1, ONLY under D7's recommendation).
- **`src/devforge/lib/_implement/_cmds_session.py`** — the counter (Phase 2, ONLY under D8 and OQ-2's answer).
- **`tests/lib/_implement/test_state.py`**, **`test_wip.py`** (both exist), and the session-state test module (Phases 1–2).
- **`src/commands/breakdown/main.md`** — `:627`, and `:506`–`:514` only if OQ-7 widened (Phase 4).
- **`CHANGELOG.md`**, **`src/CLAUDE.md`** (`:62`, `:101`–`:102`, plus classify-sites), **`README.md:79`**, **`DEVELOPMENT-STATUS.md`** (`:113`, `:121`–`:130`, and `:123` per D8), **`PLAN-STATUS-ARCHIVE.md`** (this plan's two lines only), **`src/devforge/storage-rules.md`** (Phase 5).

**READ-ONLY anchors — no phase of this plan writes any of these, and an anchor listed here is a file to READ, never an edit target:**

- `src/devforge/lib/_implement/_cmds_resolve.py` — the `{"state": "task", …}` payload and its `review_checkpoint` key `:387`.
- `src/devforge/lib/_implement/_handoff_reader.py:203`, `src/devforge/lib/_breakdown/handoff_schema.py:111`/`:126`/`:151`–`:154` — the field's carriage and its strict-bool validation.
- `src/devforge/lib/breakdown_helper.py` — `:142`, `:1067`, `:2892`, `:3216`, `:3392`–`:3418`, `:3730`.
- `src/devforge/lib/_implement/_cmds_gate.py`, `_cmds_review_panel.py`, `_cmds_verify.py`, `_cmds_commit.py` — the caps, the panel, the verify statuses and `clear_wip_marker`'s one call site.
- `src/devforge/lib/_implement/_cmds_preflight.py:306`–`:325` — `_check_wip_marker`, which ASSERTS absence and reads no field. ⚠ **The file's stale *"Phase 9"* naming is NOT repaired by any phase, and it does NOT all sit in this range: `:310` and `:323` do, while `:12` is MODULE-LEVEL** — so this anchor's range holds two of the three, and the third is found only by grepping the file (F14, Trap 11).
- `scripts/emitters/claude.py` — `_PROMOTED` `:57` and `write_references` `:83` (F16).
- `src/commands/audit/main.md` — `:4`, `:114`, `:118`: the flag-bearing `argument-hint` and the `$ARGUMENTS` precedent (F17, F20).
- `release/v-1.23.0`: `.claude/commands/execute-task.md`, `_multi-task-continuation.md`, `_context-maintenance.md` — ⚠ **branch-only; `git show`, never a working-tree path** (F9–F12).
- `https://code.claude.com/docs/en/slash-commands.md` — the argument-passing rules, the positional-only `arguments:` key, and the commands-merged-into-skills note (F20, F22). ⚠ **Reached through the `claude-code-guide` agent, which is the channel CLAUDE.md mandates — NOT by fetching the URL directly.** ⚠ **Three reads on 2026-09-23 returned three different field lists; re-establish, do not trust F20's summary at build time.**
- The neighbouring open plans named in `## Coordination with the neighbouring open plans`.

---

## When resuming work

1. **Read this plan in full** before touching anything — it encodes context that is not in the conversation. Then read `## Coordination with the neighbouring open plans` together with each neighbour's own `## Non-goals` and scope statements. ⚠ **Find every sibling plan by its TITLE if a filename has moved** — never by assuming a number.
2. **Check `### Phase 0 close record` first** — it sits at the end of `## Phase 0 — ratification`. It reads *NOT CLOSED — the plan was DECLINED AS A WHOLE*: nothing is ratified, **no build phase may start**, and **no flag name, field name, option token, note token or filename this plan proposed may be quoted in any file as if it were live or ratified.** Steps 3–9 below describe the build this plan would have needed; they apply only if a future maintainer reverses the decline, which takes a new Phase 0.
3. **Re-verify F1–F22 against the live tree. Grep the QUOTED TEXT, never the digits:** `logically incompatible with batch forms`, `No batch task targeting`, `AskUserQuestion`, `review_checkpoint`, `Review checkpoint`, `Review Checkpoint Placement`, `before tasks`, `shape not confirmed by the user — delegated`, `Never pick either reviewer's position`, `an open finding must never reach`, `Nothing commits before`, `There is no batch mode`, `write_wip_marker`, `read_wip_marker`, `ImplementState`, `both ends must honour it`, `treats \`Skipped\` as satisfied for dependency resolution`, `Three-tier context health check`, `Source Repo Checkpoint`, `Phase 9`, `per-task hard gate`, `_PROMOTED`, `write_references`. ⚠ **F9–F12 are re-derived with `git show release/v-1.23.0:<path>`.** ⚠ **F20 and F22 are re-established through `claude-code-guide`, NOT by a direct fetch and NOT from this document.** ⚠ **After a build phase some of these strings have changed by design — a differing result is then the built state, not drift, and the phase that changed it says so in its own commit.**
4. **Build order:** **Phases 1 and 2 are independent and both precede Phase 3**; **Phase 4 depends on Phase 0's OQ-7 answer and D2's arm**; **Phase 5 runs last**; **Phase 6 is the maintainer's.** ⚠ **Never ship Phase 3 alone under a ratified D7 or D8** — it would name a field no writer writes and a counter nothing counts.
5. **Route every edit through the house flow:**
   - python-engineer → python-reviewer for every Python edit, with a test per function, written and run in the same turn;
   - instruction-author → instruction-reviewer for every markdown edit;
   - `claude-code-guide` for every Claude-Code-integration fact — **owed by Phase 3 before it writes the frontmatter or the arg parse, and discharged by NEITHER F20 nor F22.** ⚠ **Through the agent, never a direct fetch: an agent invocation leaves a trace a claimed doc-read does not.**
6. **Commit by explicit path, never `git add -A`.** Re-read `git status` first, read every shared file live, **stage by hunk on `src/CLAUDE.md` and check `git diff --cached --stat` rather than the unstaged view**, and **never touch another session's plan file.**
7. **After each phase, cross-check.** Grep every flag, field, token, phase name and identifier touched — the ratified flag name, the ratified marker field, the ratified notes token, `review_checkpoint`, `AskUserQuestion`, `PHASE 7`, `Stage A`, `Stage B`, `wip.md`, `session-state.md` — and fix any dangling reference **in the SAME change.** ⚠ **The `per-task hard gate` sweep stops at `src/`, `README.md` and `DEVELOPMENT-STATUS.md`.** In `CHANGELOG.md` and in the repo root's plan files that phrase is a frozen historical record of what was true on another date, and **editing it falsifies the record.**
8. **Run Phase 5, then leave Phase 6 to the maintainer.** "Done" means BUILT and build-verified; it never means Phase 6 passed.
9. **Keep the evidence class attached.** Any summary of this plan repeats it: **NO consumer incident, none claimed, nothing measured; ONE maintainer request plus a code read of this tree on 2026-09-23.**
