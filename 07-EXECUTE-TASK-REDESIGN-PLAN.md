# 07-IMPLEMENT-COMMAND-PLAN (was: EXECUTE-TASK-REDESIGN)

**Status**: Redesigned 2026-06-01 from the earlier `/execute-task` draft. **SHIPPED in the working tree (uncommitted)** — `/implement` command built/shipped: spec at `src/commands/implement/main.md` + `references/`, the `src/devforge/lib/_implement/` helper subpackage, and the `implement_helper` + `implement_helper.py` launcher all on disk. Per `13-IMPLEMENT-WRAPPER-MODE-PLAN.md`, Phases 0–12 shipped; wrapper-mode follow-on is tracked in `13`. testForge20 e2e (2026-06-07) findings recorded below (see "testForge20 e2e findings (2026-06-07)"). The original draft's design + per-phase build steps below are retained as the historical build record — do not re-execute them.
**Branch**: `develop-2.0-init`
**Driver**: The consumer chain documents a per-task execution command (`src/CLAUDE.md` workflow diagram + command catalog). The upstream `/breakdown` (shipped `362aaea`) already produces the structured read contract this command consumes (`breakdown-handoff.json`). This plan delivered that command — **renamed `/execute-task` → `/implement`** — as a buildable helper-owns-shape command, and absorbed the forcing-functions verify-gate from `01-CONSTITUTION-FORCING-FUNCTIONS-PLAN.md` Phase 5b.

## What changed from the original draft (2026-06-01 user redesign)

Six user decisions reshape the original 07 draft. Read these before any phase:

1. **Rename `/execute-task` → `/implement`.** Bare verb, matching `/specify` / `/plan` / `/breakdown`. Touches shipped code (see Phase 11). All identifiers rename: `execute_task_helper` → `implement_helper`, `_execute_task/` → `_implement/`, `src/commands/execute-task/` → `src/commands/implement/`.
2. **No arguments.** `/implement` takes NO `$ARGUMENTS`. The old `N` / `1,3,5` / `1-5` / `all` / `feature/task` forms are **deleted**. Rationale: per-task human approval is logically incompatible with batch forms. The command resolves the lowest-numbered incomplete feature and walks its tasks in dependency order. This deletes the entire queue-builder + `_multi-task-continuation` machinery.
3. **Single-task loop with a per-task HARD GATE before commit.** One invocation **drains the active feature task-by-task** (user choice: *loop until done/stopped*). Each task runs agent → verify → review → forcing-functions gate, then **STOPS at a hard gate**: the orchestrator shows the diff + results and asks `AskUserQuestion` with options **`approve` / `repair` / `skip` / `stop`**. Nothing the agent produced is committed until `approve`. On `approve` a single per-task WIP commit lands and the loop auto-advances to the next task.
4. **No-content-commit-until-approval, but keep crash-recovery affordances.** The old model's automatic WIP commits (after agent, per repair attempt, at completion) are **removed**. Agent work + self-repair edits sit in the working tree until the gate approves them. We KEEP the cheap pre-task `git commit --allow-empty` checkpoint + `.devforge/wip.md` marker so a mid-task crash is recoverable (user choice: *keep wip.md + empty checkpoint*).

5. **Autonomous review loop + sequential decision questions.** The per-task code review is a **bounded autonomous engineer⇄code-reviewer loop** (≤3 rounds, helper-owned counter), mirroring the framework's own python-engineer→python-reviewer discipline — NO human between rounds. It auto-converges to ready code AND **records each judgment-level decision it made on the user's behalf as a structured item** (reviewer finding + agent's resolution + the named alternative). At the gate these surface NOT as a text wall but as **focused `AskUserQuestion` questions, one at a time** — explanation carried in the option descriptions, the agent's resolution always the first (default) option. The user answers each in sequence, then does the final code read. **Most tasks record zero decisions → zero extra questions → the gate is the single code read.** Decision questions appear only when the loop made a contested call. An unconverged-at-cap review surfaces as one more question (`accept-anyway / send-back / skip / stop`). (See Phase 5 + Phase 7 + the control-flow diagram.)
6. **CBM post-commit refresh.** Because the loop drains dependency-ordered tasks, the codebase-memory-mcp graph goes stale mid-loop — later tasks would read pre-change structure. After each approved commit the orchestrator calls `mcp__codebase-memory-mcp__detect_changes` (incremental) + `cbm_sync_helper write`. MCP is orchestrator-layer (subprocess helpers cannot call MCP); reuses the existing `cbm_sync_helper`. (See Phase 8.)

**Self-repair stays automatic** (tsc/lint/build failures → ≤3 auto-fix iterations) — it makes no design decisions and, under the new model, no longer commits per attempt. The gate sits AFTER verify+review-loop+forcing-functions-gate, so the user only ever approves an already-green, review-converged change.

**Agents need no rewrite.** Spot-check 2026-06-01 of `code-reviewer.md` + `backend-engineer.md`: both already read `.devforge/memory.md`, exist in the roster, use `{{PLACEHOLDER}}` substitution. The only contract adjustment is `/implement`-side: `code-reviewer` emits a **markdown** verdict (`### Verdict: APPROVE / REQUEST CHANGES / BLOCK`), NOT JSON — so the original draft's Phase 5 JSON-parsing review helper is **dropped**; the orchestrator reads the markdown verdict directly. (Optional pre-build hardening: audit all 13 remaining agents for path/contract drift — not currently scheduled; the 2-agent spot-check is the evidence base.)

## testForge20 e2e findings (2026-06-07)

During testForge20 e2e verification of the shipped `/implement` command (feature `001-on-the-configuration-page`), reviewing the artifacts `/implement` produced surfaced two framework defects. Both are **FIXED** (via `instruction-author` → `instruction-reviewer`). Neither fix lives in `/implement` itself — the e2e run was the discovery context, not the fix location. Recorded here because the discovery happened during `/implement` e2e.

### Finding 1 — architect over-specification → forcing functions (FIXED in `/plan` + architect; e2e PENDING)

**Discovery**: in testForge20 feature `001-on-the-configuration-page`, the architect (at `/plan`) specified a 3-state discriminated union return shape (`loaded | empty | failed`) where the acceptance criteria only exercised 2 states — `empty` and `failed` were handled identically. Speculative generality the architect's soft "minimal scope" rule did not prevent.

**Fix** (shipped to the working tree via `instruction-author` → `instruction-reviewer`):

- `src/agents/architect.md` — Rule 9 gained a **state-cardinality forcing step**: before declaring any multi-state type (discriminated union / enum / status field / nullable branch), map every state to the AC or named spec section that exercises it, and collapse any unexercised state. Added a `### State Cardinality` block to the Output Format for Decisions template and a co-occurrence convention for the `Why` cell. Rule 3 was reworked to **"Follow existing patterns — flag every departure"**: default to the established convention; departing from an *already-established* pattern is a flagged judgment call; choosing where none is established is *establishing*, not departing (greenfield-exempt). The state→AC mapping and the `DEPARTURE:` flag ride **inline in the existing `Why` column** of the Key Design Decisions table — no new column, so `_breakdown` / `_plan` schemas are unaffected.
- `src/commands/plan/main.md` — a conditional `### Established-Convention Departures` subsection in the plan template (omitted entirely when there are no departures, so greenfield / first-touch stays silent), a Phase 2.5 "Surface departures" step, and a conditional Phase 3 approval-summary line.

**PENDING e2e** (NOT done — same testForge20-run class as `14` Step 5 and this plan's Phase 13 e2e): run `/plan` on a real feature and confirm the architect actually emits the `States:` mapping (and, when a convention is departed from, a `DEPARTURE:` note) in the Key Design Decisions `Why` column, and that the `### Established-Convention Departures` section appears only when ≥1 departure is flagged (greenfield → absent).

**Provenance note**: this fix is **NOT in `/implement`** — it corrects `/plan` + the architect. It is recorded in this plan only because `/implement` e2e was the discovery context.

### Finding 2 — architect wrongly assigned as a coding implementer (FIXED → see `14`)

The same testForge20 e2e showed `/breakdown` assigned `Agent: architect` to a code task (Task 001), contradicting the architect charter; fixed in `14-ARCHITECT-NOT-IMPLEMENTER-PLAN.md` (Steps 1–4 shipped, working tree). The `/implement` architect-guard added there (`implement/main.md` + `references/agent-brief.md`) is part of that fix.

## Context for next session

`/breakdown` is **SHIPPED** (`09-BREAKDOWN-COMMAND-REDESIGN-PLAN.md`, `362aaea`) and is the format owner. The machine-readable contract `/implement` consumes is the structured `specs/<NNN-feature>/breakdown-handoff.json` (schema `src/devforge/lib/_breakdown/handoff_schema.py`, `handoff_kind="breakdown"`), produced by `breakdown_helper finalize-handoff`. The human `tasks/<NNN-title>.md` files stay pure markdown (a `**Agent**:` line + `**Status**:` + Completion Notes skeleton, per `src/devforge/storage-rules.md`).

### Read contract (`/implement` obeys this producer)

- `specs/<NNN-feature>/breakdown-handoff.json` carries `tasks[]`; each `TaskRow` declares `number`, `title`, `agent`, `depends_on`, `blocks`, `touched_files`, `expects`, `produces`, `ac_addressed`, `doc_refs`, `review_checkpoint`. `/implement` loads this JSON and indexes by task number.
- `provenance.upstream_handoff_path` → sibling `plan-handoff.json`; `provenance.spec_path` → feature `spec.md`.
- Task **completion status** is tracked in the human `tasks/<NNN>.md` `**Status**:` line + `tasks/README.md` index (the schema has no per-task status field). `resolve-next-task` reads status from these markdown files and the structured contract from the JSON.

### Existing artifacts to read before resuming

- `src/CLAUDE.md` — consumer-template command catalog + workflow diagram (the `/implement` entry replaces `/execute-task`).
- `src/commands/breakdown/main.md` + `src/devforge/lib/_breakdown/` — upstream producer; **Phase 11 edits it** (rename + drop the `NNN` arg from its handoff block).
- `src/commands/plan/main.md`, `src/devforge/lib/_plan/`, `_breakdown/` — pattern parents for the new `_implement/` subpackage (helper-owns-shape, VERBATIM-block discipline, `AskUserQuestion` gates).
- `01-CONSTITUTION-FORCING-FUNCTIONS-PLAN.md` Phase 5b (absorbed into Phase 6 here).
- `03-DISCOVER-HANDOFF-PLAN.md` — Step 8 outcome-reminder wire-in was deferred until this command exists; revisit after Phase 10.
- Memory: `feedback_helper_owns_shape_principle`, `feedback_test_first_python_helpers`, `feedback_iterative_review_loop_preferred`, `feedback_dual_agent_verify_command_statements`, `feedback_zero_escape_hatch_policy`, `feedback_no_underspecification_when_delegating`, `feedback_absolute_paths_in_destructive_commands`, `feedback_emitter_promoted_cross_check`, `feedback_avoid_command_model_override`, `feedback_askuserquestion_single_line_only`.

### Wrapper-mode + paths

`.devforge/` is the runtime home: `.devforge/wip.md`, `.devforge/session-state.md`, `.devforge/memory.md`, `.devforge/project-config.json`, `.devforge/constitute.json`. (The legacy pending draft used `.claude/*` — do NOT carry those paths forward.) Wrapper mode (`SOURCE_ROOT != "."`) auto-commits source per task; honor `wrapper_mode` + `COMMIT_ATTRIBUTION` from `.devforge/project-config.json`. The hard-gate approval still applies in wrapper mode — the per-task commit lands only after `approve`.

## Design

### Helper-owns-shape conventions

- Source spec at `src/commands/implement/main.md` (LLM prose) + `src/commands/implement/references/*.md`.
- Helper subpackage at `src/devforge/lib/_implement/` (Python state-machine helpers). Helper owns shape; LLM composes values + runs the loop.
- Thin launcher `src/devforge/lib/implement_helper` (POSIX) + `src/devforge/lib/implement_helper.py` (entry point), mirroring `breakdown_helper`.
- Emitter wire-in at `scripts/emitters/claude.py` `_PROMOTED` (per `feedback_emitter_promoted_cross_check`).

### Control flow (the loop)

The orchestrator (LLM following `main.md`) runs the loop in-conversation. Per iteration:

```
resolve-next-task ──(all-complete? → report + end)
  → preflight (constitution populated, branch, memory digest) + checkpoint --allow-empty + write wip.md
  → dispatch assigned agent (brief = task body + spec slice + constitution + memory pitfalls + touched_files scope)
  → capture-touched-files (git diff vs checkpoint)
  → verify-touched (scope-aware tsc/lint/build; auto self-repair ≤3; helper owns the counter)
  → AUTONOMOUS review loop: code-reviewer agent ⇄ implementing agent, ≤3 rounds (helper owns counter),
       iterate until the markdown verdict is clean (APPROVE / warnings-only) or the cap escalates.
       NO human between rounds. Each judgment-level call the loop made is RECORDED as a structured
       decision item (reviewer finding + agent resolution + named alternative) for Stage A below.
  → run-forcing-functions-gate (each enabled .devforge/constitute.json forcing_functions rule)
  → ┌─ HARD GATE (two stages) ────────────────────────────────────────────────────────────────┐
    │  Stage A — Decision questions (ONLY if the loop recorded decisions / escalated):          │
    │     one focused AskUserQuestion PER decision, asked sequentially; explanation lives in the │
    │     option descriptions; option 1 = agent's resolution (default).                          │
    │       accept(default)            → keep that resolution                                    │
    │       use-alternative / specify  → repair: relaunch agent → re-verify → re-review-loop      │
    │       stop                       → end the loop                                            │
    │  Stage B — Final code read (ALWAYS): the READY diff →                                      │
    │       approve → mark-complete → wip-commit → CBM detect_changes + cbm_sync_helper write → next │
    │       repair  → free-text → relaunch agent → re-run verify→review-loop→gate                 │
    │       skip    → reset to checkpoint, mark Skipped, clear wip.md, advance                    │
    │       stop    → keep wip.md + working tree, end the loop                                    │
    └─────────────────────────────────────────────────────────────────────────────────────────┘
  → update-session-state + append-memory → loop
```

**The gate pushes decisions to the user; the user never scrolls a summary.** The autonomous review loop burns down reviewer findings before the gate and records each *judgment* call it made on the user's behalf. Stage A surfaces those one at a time as focused `AskUserQuestion` questions — no text wall, the explanation carried in the option descriptions, the agent's choice pre-selected as option 1. **Most tasks record zero judgment decisions, so Stage A is empty and the gate is just Stage B — the single code read** the user wanted. Stage A appears only when the loop decided something contested, or escalated at the round cap (one more question: accept-anyway / send-back / skip / stop).

**Gate-blocked paths never reach the approve prompt:** if verify exhausts 3 self-repair attempts, or the forcing-functions gate exits 2, the orchestrator surfaces the findings and offers `repair` / `skip` / `stop` only (no `approve`). Because no content commit has happened, there is nothing to roll back — the working tree holds the partial work; the user repairs or stops.

### Scope-aware verification

Per `src/CLAUDE.md` "Verification": capture touched files via `git diff` vs the task-start checkpoint; for each, longest-path-prefix match against `PACKAGE_STACKS` → that package's `type_check_command` + `lint_command`; build runs once per task aggregated; files outside any package fall back to primary-stack (`TYPE_CHECK_COMMANDS[0]` etc.); skip `"N/A"` silently. Self-repair loop (helper owns the ≤3 counter): a failing command returns `{phase: "self_repair", failed_command, output}`; after 3 failed iterations the helper exits `EXIT_FINDINGS`.

### Forcing-functions integration (absorbs 01-CONSTITUTION Phase 5b)

After verify + code review but BEFORE the hard gate: for each `forcing_functions.<rule>` with `enabled: true` in `.devforge/constitute.json`, invoke `constitute_helper verify-<rule>`. Exit 0 → continue. Exit 2 → STOP before the approve prompt; relay the stdout JSON finding report (NOT stderr — `path:line: KIND` is ambiguous when a path contains `:`, per `_shared.emit_findings` Known Limitations) as a fenced block; offer `repair` / `skip` / `stop`.

---

## Phase 0 — Scope + precondition audit

> **Historical (command now SHIPPED — see top Status + "testForge20 e2e findings (2026-06-07)").** This audit captured the *starting* precondition when the build had not begun, so the `expect: No such file or directory` lines below are now inverted on disk (the files exist). Retained as the pre-build record; do not re-run as a current check.

**Owner**: orchestrator (one-shot read-only sweep).

### Audit checklist

```bash
ls src/commands/implement/ 2>&1                                    # expect: No such file or directory
ls src/devforge/lib/implement_helper* 2>&1                         # expect: No such file or directory
ls src/devforge/lib/_implement/ 2>&1                               # expect: No such file or directory
ls src/commands/breakdown/main.md 2>&1                             # expect: EXISTS (read contract producer)
ls src/devforge/lib/_breakdown/handoff_schema.py 2>&1              # expect: EXISTS
grep -nE "/execute-task|execute_task_helper|render-execute-task-handoff" \
   src/CLAUDE.md src/commands/*/main.md src/devforge/lib/breakdown_helper.py \
   src/devforge/lib/_breakdown/handoff_schema.py                   # expect: hits — these are Phase 11 rename targets
grep -nE "implement|/implement" scripts/emitters/claude.py         # expect: zero hits (no emitter wire-in yet)
```

### Precondition declarations

- **PC1**: `/breakdown` is SHIPPED (read-contract producer present). Confirmed via `09-BREAKDOWN-COMMAND-REDESIGN-PLAN.md` (`362aaea`). PC1 met.
- **PC2**: `01-CONSTITUTION-FORCING-FUNCTIONS` Phases 0+1+3+4 SHIPPED (all consumer-side `verify-<rule>` verbs). Confirmed `ea18cd1`, `ccc25b8`, `a370229`, `4b058da`. PC2 met.
- **PC3**: `.devforge/project-config.json` defines `PACKAGE_STACKS`, `wrapper_mode`, `COMMIT_ATTRIBUTION`. Verify via `configure_helper render-config` on testForge20.
- **PC4** (agents): `code-reviewer` + the 13 task-assigned engineers exist in `src/agents/` and are `.devforge/`-path-aligned. Spot-checked `code-reviewer` + `backend-engineer` 2026-06-01. No agent rewrite scheduled.

---

## Phase 1 — Helper substrate + handoff reader

**Owner**: python-engineer → python-reviewer.

### Files

- `src/devforge/lib/_implement/__init__.py` — subpackage marker; docstring naming the domains (task resolution, WIP marker, scope-aware verify, forcing-functions gate, per-task commit).
- `src/devforge/lib/_implement/_state.py` — `ImplementState` (frozen) dataclass: `feature_dir: Path`, `task_number: str`, `task_title: str`, `agent_name: str`, `touched_files: List[str]`, `phase: Literal["preflight","agent","verify","review","forcing_functions","gate","commit","complete"]`, `wip_marker_path: Path`, `checkpoint_sha: Optional[str]`.
- `src/devforge/lib/_implement/_handoff_reader.py` — `read_breakdown_handoff(feature_dir) -> Breakdown` (parse + schema-validate `breakdown-handoff.json` via the `_breakdown.handoff_schema` dataclasses — import, do not re-implement); `task_row(handoff, number) -> TaskRow`. Raise `ValueError` on missing/malformed/wrong-kind.
- `src/devforge/lib/_implement/_wip.py` — `write_wip_marker`, `read_wip_marker(devforge_dir) -> Optional[dict]`, `clear_wip_marker`. Mandatory `Command: /implement` field.
- `src/devforge/lib/_implement/_cli.py` — subcommand router (mirror `_breakdown`/`_plan` CLI shape).
- `src/devforge/lib/implement_helper` (POSIX launcher) + `src/devforge/lib/implement_helper.py` — thin shim: sets the lib dir on `sys.path`, imports `from _implement._cli import main`, calls `sys.exit(main())` under `if __name__ == "__main__"` (matching `breakdown_helper.py`).
- `tests/lib/_implement/test_state.py`, `test_handoff_reader.py`, `test_wip.py`.

### Verify

```bash
python3 -m pytest tests/lib/_implement/ -v
python3 src/devforge/lib/implement_helper.py --help
python3 -c "import sys; sys.path.insert(0,'src/devforge/lib'); from _implement._state import ImplementState; from _implement._handoff_reader import read_breakdown_handoff; from _implement._wip import write_wip_marker; print('Phase 1 substrate ok')"
```

Real-producer test discipline: `_handoff_reader` tests round-trip through a real `breakdown_helper finalize-handoff` output (or a fixture validated against the live `_breakdown.handoff_schema`), NOT a hand-authored JSON blob.

---

## Phase 2 — Task resolution (no-args) + preflight

**Owner**: python-engineer → python-reviewer + instruction-author → instruction-reviewer.

### Files

- `src/devforge/lib/_implement/_cmds_resolve.py` — `cmd_resolve_next_task(args)`:
  1. Scan `specs/*/` for features with a `breakdown-handoff.json`.
  2. Determine each feature's incomplete-task set by reading `tasks/<NNN>.md` `**Status**:` lines (status ≠ `Complete` and ≠ `Skipped`) cross-referenced with the handoff `tasks[]`.
  3. Pick the **lowest-numbered feature** with ≥1 incomplete task (finish earlier features first).
  4. Within it, pick the **lowest-numbered task whose `depends_on` are all Complete or Skipped**.
  5. Emit JSON: `{state: "task", feature_dir, number, title, agent, depends_on, touched_files, expects, produces, ac_addressed, doc_refs, review_checkpoint}`. If no incomplete tasks anywhere → `{state: "all-complete"}`. If a feature has incomplete tasks but none are dependency-ready (cycle / unmet dep) → `{state: "blocked", reason, blocking_tasks}` (exit 2).
- `src/devforge/lib/_implement/_cmds_preflight.py` — `cmd_preflight(args)`:
  1. Constitution-populated check (`_Run /constitute to populate_` → exit 2 with stderr instruction).
  2. Branch check — refuse `main`/default; require a feature branch.
  3. Defensive `wip.md` assert: the Phase 9 recovery branch (runs once at loop start) is the SOLE interrupted-session detector. Preflight only asserts no stale `wip.md` remains at per-task entry; if one is unexpectedly present, exit 2 pointing the user back to the recovery branch (it should have been handled or cleared already).
  4. Snapshot git HEAD as `checkpoint_sha` (this is the rollback target). The orchestrator then creates the pre-task marker commit `git commit --allow-empty -m "[checkpoint] pre-task NNN"` per `main.md`; rollback (`skip`/recovery) resets to `checkpoint_sha`, discarding both the marker and any task edits.
  5. Emit JSON: constitution digest, `.devforge/memory.md` digest, head-sha, branch-name.
- `src/commands/implement/main.md` — author the header + frontmatter (`name: implement`, `description:`, `argument-hint: ""`, `disable-model-invocation: true`), the loop overview, and Phase 0 (resolution) + preflight steps. NO argument-parsing section (bare verb).
- `tests/lib/_implement/test_cmds_resolve.py`, `test_cmds_preflight.py`.

### Verify

```bash
python3 -m pytest tests/lib/_implement/test_cmds_resolve.py tests/lib/_implement/test_cmds_preflight.py -v
python3 src/devforge/lib/implement_helper.py resolve-next-task --help
python3 src/devforge/lib/implement_helper.py preflight --help
grep -nE "resolve-next-task|preflight|lowest-numbered" src/commands/implement/main.md
grep -cE "\$ARGUMENTS" src/commands/implement/main.md   # expect 0 (bare verb)
```

---

## Phase 3 — Agent dispatch + scope capture

**Owner**: instruction-author → instruction-reviewer (spec); python-engineer → python-reviewer (capture helper).

### Files

- `src/commands/implement/main.md` — agent-dispatch step: orchestrator invokes the agent named in the TaskRow `agent` field (resolved by Phase 2) via the Task tool. Brief = task body (read from `tasks/<NNN>.md`) + the spec AC slice (`ac_addressed`) + constitution rules + `.devforge/memory.md` pitfalls + the `touched_files` scope constraint + an explicit "make ONLY the changes this task describes" rule. If the named agent is absent from `.claude/agents/`, fall back to `architect` (mirrors `/breakdown` Agent Assignment fallback).
- `src/commands/implement/references/agent-brief.md` — brief shape (goal / integration context / constraints / edge cases / success criteria / what NOT to do), cross-ref `feedback_no_underspecification_when_delegating`.
- `src/devforge/lib/_implement/_cmds_capture.py` — `cmd_capture_touched_files(args)` — `git diff --name-only <checkpoint-sha>` (+ `git status --porcelain` for untracked new files). Emit JSON list.
- `tests/lib/_implement/test_cmds_capture.py` — seeded git tempdir.

### Verify

```bash
python3 -m pytest tests/lib/_implement/test_cmds_capture.py -v
python3 src/devforge/lib/implement_helper.py capture-touched-files --help
grep -nE "agent-brief|touched_files|fall back to .architect" src/commands/implement/main.md
```

---

## Phase 4 — Scope-aware verification + self-repair

**Owner**: python-engineer → python-reviewer.

### Files

- `src/devforge/lib/_implement/_cmds_verify.py` — `cmd_verify_touched(args)`:
  1. Read `touched_files` list (from Phase 3 JSON).
  2. Load `PACKAGE_STACKS` from `.devforge/project-config.json`.
  3. Longest-path-prefix match each file → package `type_check_command` + `lint_command`; non-matching files → primary-stack fallback.
  4. Aggregate + de-dup commands (run each once over the union it covers). Build once per task at end.
  5. Skip `"N/A"` silently. Wrapper-mode `cd SOURCE_ROOT &&` prefix already baked into stored commands — do not re-prefix.
  6. Self-repair loop, **helper owns the counter** (resolves original draft OQ3): a non-zero command returns `{phase: "self_repair", iteration: M, failed_command, output}`; the orchestrator relaunches the agent to fix; after 3 failed iterations emit `EXIT_FINDINGS` with structured stdout.
- `src/commands/implement/main.md` — verify step + the self-repair relaunch instruction (≤3, helper-enforced).
- `tests/lib/_implement/test_cmds_verify.py` — fixture config with 2 packages; assert command aggregation + self-repair iteration counter caps at 3.

### Verify

```bash
python3 -m pytest tests/lib/_implement/test_cmds_verify.py -v
python3 src/devforge/lib/implement_helper.py verify-touched --help
```

---

## Phase 5 — Autonomous review loop (engineer ⇄ code-reviewer)

**Owner**: instruction-author → instruction-reviewer (spec); python-engineer → python-reviewer (loop-control helper).

**Design (2026-06-01 user decision — full auto-converge + sequential decision questions):** the per-task review is a **bounded autonomous loop**, mirroring the framework's own python-engineer→python-reviewer discipline, with NO human between rounds. `code-reviewer.md` emits a markdown `### Verdict:` block (NOT JSON — confirmed by the 16-agent read; the original draft's JSON-parsing helper is dropped). The loop converges to a ready diff AND records each judgment call it made as a structured **decision item** — those drive the gate's Stage A sequential questions (Phase 7), so the user is never handed a text wall to scroll.

**Change from original draft**: the JSON-parsing review helper (`_cmds_review.py`) is **dropped**. A small loop-control helper (counter + verdict parsing) replaces it.

### Files

- `src/devforge/lib/_implement/_cmds_review_loop.py` — `cmd_review_loop_step(args)`: given the code-reviewer agent's returned markdown (path or stdin) + the current iteration `N`, parse the `### Verdict:` line and return JSON `{clean: bool, escalate: bool, iteration: N}`. `clean = true` for `APPROVE` / warnings-only; `clean = false` for `REQUEST CHANGES` / `BLOCK`. `escalate = true` when `N >= cap` (cap helper-owned, mirrors the ≤3 self-repair cap — **default 3**; one constant, code-commented). The helper owns the counter so the loop cannot be silently bypassed (zero-escape-hatch).
- `src/commands/implement/main.md` — the review-loop step: after verify passes, run:
  1. Invoke `code-reviewer` (consumer `.claude/agents/code-reviewer.md`) with `touched_files` + constitution + task body.
  2. `implement_helper review-loop-step` on the returned markdown.
  3. If `clean` → exit loop; carry any warnings into Stage B. If `!clean && !escalate` → relaunch the **implementing agent** with the reviewer's findings (the autonomous repair leg; no human), then re-invoke `code-reviewer` and repeat. If `escalate` → exit loop and record a `could-not-converge: <reviewer objection>` decision item.
  4. **Record decision items.** During each repair leg, the orchestrator (LLM) classifies what it changed to clear a finding: a **judgment** call (scope-creep call, abstraction/module choice, constitution interpretation — changed the *shape* of the solution) is recorded as a structured decision item `{finding, agent_resolution, alternative}` for Stage A. A **mechanical** fix (missing docstring, named in-scope type fix, null guard) resolves silently — not recorded. Bias rule: **when unsure whether a cleared finding was a judgment call, record it** — a surplus decision question costs one click; a missed one silently lands a contested decision.
- `src/commands/implement/references/review-loop.md` — explains the loop, the clean/escalate verdict mapping, the mechanical-vs-judgment classification + bias-toward-recording rule, the decision-item shape, and the cap.
- `tests/lib/_implement/test_cmds_review_loop.py` — verdict-parsing matrix (APPROVE / warnings-only / REQUEST CHANGES / BLOCK → clean bool); counter caps at 3 → escalate.

### Verify

```bash
python3 -m pytest tests/lib/_implement/test_cmds_review_loop.py -v
python3 src/devforge/lib/implement_helper.py review-loop-step --help
grep -nE "code-reviewer|review loop|could-not-converge|decision item|judgment" \
   src/commands/implement/main.md src/commands/implement/references/review-loop.md
```

---

## Phase 6 — Forcing-functions verify-gate (absorbs 01-CONSTITUTION Phase 5b)

**Owner**: python-engineer → python-reviewer (helper); instruction-author → instruction-reviewer (spec).

### Files

- `src/devforge/lib/_implement/_cmds_gate.py` — `cmd_run_forcing_functions_gate(args)`:
  1. Read `forcing_functions` block from `.devforge/constitute.json`.
  2. For each enabled rule, subprocess `constitute_helper verify-<rule>` with shared `--root` + `--config`.
  3. Aggregate per-rule exit codes + stdout JSON reports.
  4. Emit `{gate: "forcing_functions", rules_run, rules_failed, aggregate_exit: 0|2}`; exit 0 if none failed, 2 if any failed.
- `src/commands/implement/main.md` — gate step inserted AFTER verify + review, BEFORE the hard gate. On exit 2: relay stdout JSON as a fenced block; the hard gate offers `repair` / `skip` / `stop` only.
- `src/commands/implement/references/forcing-functions-gate.md` — explains the gate, the verbs (`verify-magic-enum`, `verify-cross-layer-imports`, `verify-any-leak`), exit semantics, triage.
- `tests/lib/_implement/test_cmds_gate.py` — 2 enabled rules (one passing/one failing → exit 2); both passing → 0; both disabled → 0 + empty report.

### Verify

```bash
python3 -m pytest tests/lib/_implement/test_cmds_gate.py -v
python3 src/devforge/lib/implement_helper.py run-forcing-functions-gate --help
grep -nE "forcing.functions|verify-magic-enum|verify-cross-layer-imports|verify-any-leak" \
   src/commands/implement/main.md src/commands/implement/references/forcing-functions-gate.md
```

Cross-reference cleanup: mark `01-CONSTITUTION-FORCING-FUNCTIONS-PLAN.md` Phase 5b as ABSORBED INTO 07 Phase 6 (it currently says "ABSORBED INTO 07 Phase 7" — renumbered here).

---

## Phase 7 — Hard gate + single per-task commit

**Owner**: instruction-author → instruction-reviewer (spec); python-engineer → python-reviewer (commit helper).

### Files

- `src/commands/implement/main.md` — the HARD GATE step, **two stages** (2026-06-01 user decision — push decisions as sequential questions, no scrollback / no text wall):

  **Stage A — Decision questions (run ONLY if Phase 5 recorded ≥1 judgment decision, or escalated):** iterate the recorded decision items. For EACH, one `AskUserQuestion` (per `feedback_askuserquestion_single_line_only` — the question is single-line; the explanation lives in the option `description` fields, NOT a multi-line body):
     - Single-line question, e.g. `"Reviewer flagged <X> — keep which resolution?"`.
     - Options (each with a full `description` carrying the explanation): `["<agent's resolution> (recommended)", "<named alternative>", "let me specify", "stop"]`. Option 1 is ALWAYS the agent's resolution, marked `(recommended)` so agreeing is one click.
     - **accept (option 1)** → keep the resolution; next decision question.
     - **use-alternative / let-me-specify** → treat as a `repair` (free-text for "specify"): relaunch the implementing agent with the chosen direction; re-run verify → review-loop; rebuild the decision set; restart Stage A.
     - **stop** → keep `wip.md` + working tree; end the loop.
     - A `could-not-converge` escalation is one more Stage-A question: `["accept anyway", "send back with direction", "skip", "stop"]`.
     Ask them ONE AT A TIME (sequential `AskUserQuestion` calls), never batched. Most tasks have zero recorded decisions → Stage A is skipped entirely.

  **Stage B — Final code read (ALWAYS):** present the ready diff (`git diff --stat` + the diff, bounded for large diffs) + verify/review/forcing-functions results. Then `AskUserQuestion` — single-line `"Approve task NNN — <title>?"`, options `["approve", "repair", "skip", "stop"]`:
     - **approve** → mark task complete (Phase 8 `mark-complete`, so the commit captures the completed task file + index); run `wip-commit`; CBM refresh (Phase 8); advance.
     - **repair** → free-text follow-up; relaunch the assigned agent with notes; re-run verify → review-loop → gate → return here.
     - **skip** → reset the working tree to the task-start checkpoint (`git reset --hard <checkpoint_sha>`, discarding the skipped task's edits so they don't bleed into the next task's diff); set `**Status**: Skipped` in the task file + index; clear `wip.md`; advance. (Skipping a task whose `produces` feed a downstream `expects` is surfaced as a warning before the skip lands.)
     - **stop** → keep `wip.md` + working tree; report state; end the loop.
- `src/devforge/lib/_implement/_cmds_commit.py` — `cmd_wip_commit(args)`:
  1. Stage `touched_files` + the task file + index ONLY (never `git add -A`, per `feedback_absolute_paths_in_destructive_commands`).
  2. Read `wrapper_mode` + ticket-id (from branch) + `COMMIT_ATTRIBUTION` from `.devforge/project-config.json`.
  3. Compose message: wrapper → `[TICKET-ID] - <task-title> (Task NNN)`; non-wrapper → `[WIP] task: <task-title> (Task NNN)`. (WIP commits are squashed by `/finalize` — the approval gates the content, not the commit granularity.)
  4. Honor `COMMIT_ATTRIBUTION` (no hardcoded Co-Authored-By).
  5. Commit; capture new HEAD; clear `wip.md`.
- `tests/lib/_implement/test_cmds_commit.py` — wrapper + non-wrapper message format; staging-respects-touched-files-only assertion.

### Verify

```bash
python3 -m pytest tests/lib/_implement/test_cmds_commit.py -v
python3 src/devforge/lib/implement_helper.py wip-commit --help
grep -nE "Stage A|Stage B|approve.*repair.*skip.*stop|HARD GATE|git diff" src/commands/implement/main.md
```

---

## Phase 8 — Loop control + completion + session-state/memory

**Owner**: python-engineer → python-reviewer (helpers); instruction-author → instruction-reviewer (loop spec).

### Files

- `src/devforge/lib/_implement/_cmds_complete.py` — `cmd_mark_complete(args)`: in `tasks/<NNN>.md` set `**Status**: Complete`, tick verified Done-When boxes, fill Completion Notes (`Completed`, `Files changed`, `Contract: Expects X/Y | Produces X/Y`, `Notes`); update `tasks/README.md` index row.
- `src/devforge/lib/_implement/_cmds_session.py` — `cmd_update_session_state(args)`: overwrite `.devforge/session-state.md` (≤40 lines, sliding window: current feature, N-of-M progress, last 3 task mods, last 3 decisions); append a one-line outcome to `.devforge/memory.md`.
- `src/commands/implement/main.md` — the loop spec: after `approve`, run **`mark-complete`** first (so the commit captures the completed task file + index), then **`wip-commit`**, then the **CBM refresh** step, then session/memory update, then re-invoke `resolve-next-task`. On `state: "all-complete"` → report `"✅ All feature tasks complete. Next: run /review → /verify → /summarize → /finalize"` and end. On `state: "task"` → start the next iteration (loop until done/stopped — auto-advance, no per-task continue prompt; `stop` at the hard gate is the only loop exit besides completion).
- **CBM post-commit refresh (orchestrator-layer, MCP — NOT a subprocess-helper call)**: because the loop drains dependency-ordered tasks (task B's `Expects` read task A's just-committed `Produces`), the codebase-memory-mcp graph goes stale mid-loop. After each approved commit the orchestrator calls `mcp__codebase-memory-mcp__detect_changes` (incremental — re-indexes only the committed delta, including new inline docs; reserve full `index_repository` for a missing/severely-drifted graph), then `cbm_sync_helper write` to advance the stamp (`.devforge/cbm-last-indexed-sha`). This reuses the EXISTING `cbm_sync_helper` (no new helper) and mirrors the `cbm-sync-session-start` hook pattern. The MCP call lives in `main.md` because subprocess helpers cannot reach MCP.
- `tests/lib/_implement/test_cmds_complete.py`, `test_cmds_session.py`.

> No new helper for the CBM refresh — `cbm_sync_helper write` already exists. Phase 8 only adds the orchestrator-side `detect_changes` + `write` sequence to `main.md` and a one-line note that it runs per approved commit.

### Verify

```bash
python3 -m pytest tests/lib/_implement/test_cmds_complete.py tests/lib/_implement/test_cmds_session.py -v
python3 src/devforge/lib/implement_helper.py mark-complete --help
python3 src/devforge/lib/implement_helper.py update-session-state --help
grep -nE "all-complete|loop|resolve-next-task" src/commands/implement/main.md
```

---

## Phase 9 — Crash recovery (wip.md + checkpoint)

**Owner**: instruction-author → instruction-reviewer (spec); python-engineer → python-reviewer (recovery read helper, if needed beyond `_wip.read_wip_marker`).

### Files

- `src/commands/implement/main.md` — Phase 0 recovery branch: at loop start, before `resolve-next-task`, read `wip.md`. This recovery branch is the SOLE interrupted-session detector for `wip.md` (per-task preflight only asserts, per Phase 2). If present, `AskUserQuestion` (single-line) options `["resume", "rollback", "skip", "manual"]` (resolves original draft OQ4):
  - **resume** → re-enter the task at its recorded phase.
  - **rollback** → `git reset --hard <checkpoint_sha>` (the empty checkpoint), clear `wip.md`, re-resolve.
  - **skip** → mark the in-flight task Skipped, clear `wip.md`, advance.
  - **manual** → keep state, end the loop for hand inspection.
  - `Command` mismatch (marker written by `/fix` or `/refactor`) → "resolve previous session first" prompt; do not proceed.
- `src/commands/implement/references/crash-recovery.md` — the 4 options + WIP marker fields + Command-mismatch detection.

### Verify

```bash
grep -nE "resume.*rollback.*skip.*manual|Command mismatch|wip.md" \
   src/commands/implement/main.md src/commands/implement/references/crash-recovery.md
```

---

## Phase 10 — Command spec finalization

**Owner**: instruction-author → instruction-reviewer (iterate until clean, per `feedback_iterative_review_loop_preferred`).

### Files

- `src/commands/implement/main.md` — full pass: all loop phases present, ordered, citing their reference docs. NO `model:` frontmatter (per `feedback_avoid_command_model_override` — inherit session model). Bash-tool permission allowlist declares the `implement_helper` verbs + `constitute_helper verify-*` explicitly. Sentence-level hallucination check (per `feedback_sentence_level_hallucination_check_specs`): every sentence mechanically-true / verifiable-now / explicit-forward-ref.
- `src/commands/implement/references/` — confirm `agent-brief.md`, `review-loop.md`, `forcing-functions-gate.md`, `crash-recovery.md` present.

### Verify

```bash
ls src/commands/implement/main.md src/commands/implement/references/
grep -cE "^##" src/commands/implement/main.md   # expect ≥ 7 (one heading per loop phase)
```

---

## Phase 11 — Rename blast radius (edits SHIPPED code)

**Owner**: instruction-author → instruction-reviewer (specs/docs) + python-engineer → python-reviewer (`breakdown_helper` + tests).

**This phase edits already-shipped `/breakdown`.** The bare-verb rename means `/breakdown` must stop emitting `/execute-task NNN` (with a task-number argument) and emit `/implement` (no argument).

### Files

- `src/commands/breakdown/main.md`:
  - Frontmatter `description` + line 23 workflow diagram + lines 273/280/361/386/397 `/execute-task` → `/implement`.
  - The finalize block (lines 399–410): the verb call `render-execute-task-handoff` → `render-implement-handoff`; the block heading `## Manual next step — run /execute-task` → `run /implement`; the literal `/execute-task NNN` → `/implement` (drop the number — bare verb); the closing sentence.
- `src/devforge/lib/breakdown_helper.py` + `src/devforge/lib/_breakdown/`: rename the `render-execute-task-handoff` verb → `render-implement-handoff`; update the emitted block text (heading + `/implement` no-arg); update the schema docstring `handoff_schema.py:4` ("consumed by `/execute-task`" → "`/implement`"). Update the corresponding `tests/lib/_breakdown/` assertions on that block's text.
- `src/CLAUDE.md`: workflow diagram (2 occurrences), the `#### /execute-task` catalog entry → `#### /implement` (drop the `[number]` arg-hint, rewrite the 5-step body to the loop+gate model), the Hard-Gates line "before `/execute-task` can start", Session-Continuity "Updated automatically by `/execute-task` (Phase 7)" → `/implement` (Phase 8), the Crash-Recovery paragraph's `/execute-task` mention + the `Command` field example list.
- `src/commands/plan/main.md`, `src/commands/specify/main.md`, `src/commands/onboard/main.md`: workflow-diagram `/execute-task` → `/implement`.
- `src/agents/architect.md` (lines 27, 29, 140) + `src/agents/tech-writer.md` (lines 45, 49, 91, 101, 132, 155): `/execute-task` → `/implement` (9 references total; these are the only two agent files that name the command — confirmed by a full 16-agent read 2026-06-01).

### Verify

```bash
python3 -m pytest tests/lib/_breakdown/ -v          # block-text assertions updated, still green
grep -rnE "/execute-task|execute_task_helper|render-execute-task-handoff" \
   src/CLAUDE.md src/commands/ src/devforge/lib/ src/agents/ | grep -v _pending   # expect: ZERO hits outside _pending
# Confirm breakdown now emits bare /implement (no NNN):
grep -nE "/implement" src/devforge/lib/_breakdown/ -r
```

(The `src/_pending/` legacy drafts are NOT renamed — they're archived pre-pivot material.)

---

## Phase 12 — Emitter wire-in + manifest

**Owner**: python-engineer → python-reviewer.

### Files

- `scripts/emitters/claude.py` — add `"implement"` to `_PROMOTED` (per `feedback_emitter_promoted_cross_check`). If `"execute-task"` was ever added, remove it.
- `src/manifest.json` — declare `.claude/commands/implement.md` + `.devforge/lib/implement_helper` + `.devforge/lib/_implement/` as emitted artifacts.
- `install.sh` / `update.sh` — verify the helper subpackage copies to consumer `.devforge/lib/_implement/`.

### Verify

```bash
grep -nE "implement" scripts/emitters/claude.py src/manifest.json
./scripts/generate.sh ~/Projects/testForge20 2>&1 | tail -20
ls ~/Projects/testForge20/.claude/commands/implement.md
ls ~/Projects/testForge20/.devforge/lib/implement_helper ~/Projects/testForge20/.devforge/lib/_implement/
# No stray execute-task artifacts emitted:
ls ~/Projects/testForge20/.claude/commands/execute-task.md 2>&1   # expect: No such file
```

---

## Phase 13 — testForge20 install smoke (empirical-validation stop)

**Owner**: orchestrator (manual e2e, user-driven).

### Procedure

1. On testForge20, run the real chain to produce a `breakdown-handoff.json` with ≥2 tasks (or reuse an existing feature breakdown). Confirm `breakdown` now ends by printing `run /implement` (no task number).
2. Restart Claude Code; run `/implement` (no args).
3. Observe the loop on the first task:
   - `resolve-next-task` picks the lowest incomplete feature + first dependency-ready task.
   - Preflight reads constitution + memory; checkpoint + `wip.md` written.
   - Assigned agent dispatched with full brief; edit lands in the working tree (NOT yet committed).
   - Scope-aware verify runs the package's tsc/lint (or `"N/A"` no-ops); self-repair if needed.
   - Autonomous review loop runs: `code-reviewer` dispatches, markdown verdict read; for a trivial edit it converges clean (APPROVE) in round 1, so the gate's Stage A is empty.
   - Forcing-functions gate runs each enabled `verify-<rule>`.
   - **Hard gate** shows the diff + results; `AskUserQuestion` approve/repair/skip/stop.
   - On `approve` → single WIP commit (correct message format); task marked Complete; session-state + memory updated.
   - CBM `detect_changes` fires after the approved commit; the `.devforge/cbm-last-indexed-sha` stamp advances.
   - Loop auto-advances to task 2; same gate; `stop` ends the loop cleanly leaving remaining tasks pending.
4. Document at `IMPLEMENT-SMOKE-2026-MM-DD.md`.

### Stop criteria

- `/implement` with no args drains task-by-task; each task hits the hard gate; nothing commits before `approve`.
- `skip` and `stop` behave per spec; `wip.md` survives `stop`, cleared on completion.
- Forcing-functions gate is observably invoked (even if exit 0); the relay-stdout-JSON behavior is reachable.
- CBM refresh runs after the approved commit (incremental `detect_changes`); the stamp advances.
- WIP commit format matches wrapper/non-wrapper convention.

---

## Phase 14 — Documentation propagation

**Owner**: instruction-author → instruction-reviewer.

### Files

- `CHANGELOG.md` — `/implement` ship (rename from `/execute-task` + loop/hard-gate model + forcing-functions gate).
- Repo-root `CLAUDE.md` — flip this plan's active-plans row to reflect the rename + SHIPPED status when done; note `01-` Phase 5b ABSORBED into 07 Phase 6; add the `/implement` "Where to find what" row.
- `DEVELOPMENT-STATUS.md` — single-line entry.
- `src/CLAUDE.md` — already reconciled in Phase 11; here only verify no `/execute-task` residue and the catalog entry matches the implemented spec (drift report; no silent drift).

### Verify

```bash
grep -nE "/implement|implement_helper" CHANGELOG.md CLAUDE.md DEVELOPMENT-STATUS.md
grep -rnE "/execute-task" CLAUDE.md src/CLAUDE.md CHANGELOG.md DEVELOPMENT-STATUS.md   # expect ZERO (outside historical changelog notes)
```

---

## When resuming work

> **The `/implement` build is SHIPPED in the working tree (see top Status; Phases 0–12 per `13`).** The dispatch-the-owner steps below describe the original build run and are retained as the historical build procedure — they are NOT a current to-do list. The remaining live work is the testForge20 e2e (Phase 13) plus the Finding-1 e2e in "testForge20 e2e findings (2026-06-07)"; wrapper-mode follow-on is tracked in `13`.

1. Read this plan top-to-bottom + the "What changed" section.
2. Cross-read `src/commands/breakdown/main.md` + `_breakdown/handoff_schema.py` (read contract) and `01-CONSTITUTION-FORCING-FUNCTIONS-PLAN.md` Phase 5/6 (gate).
3. Verify each phase on disk:
   ```bash
   ls src/devforge/lib/_implement/ 2>/dev/null                                                  # Phase 1
   for v in resolve-next-task preflight capture-touched-files verify-touched review-loop-step \
            run-forcing-functions-gate wip-commit mark-complete update-session-state; do
     python3 src/devforge/lib/implement_helper.py $v --help >/dev/null 2>&1 \
       && echo "verb ok: $v" || echo "MISSING: $v"
   done
   ls src/commands/implement/main.md src/commands/implement/references/ 2>/dev/null              # Phases 2-10
   grep -rnE "/execute-task" src/CLAUDE.md src/commands/ src/devforge/lib/ | grep -v _pending    # Phase 11 (expect 0)
   grep -nE "implement" scripts/emitters/claude.py src/manifest.json                             # Phase 12
   ls IMPLEMENT-SMOKE-*.md 2>/dev/null                                                           # Phase 13
   ```
4. For each unfinished phase, dispatch the named owner with a complete brief. Follow every python-engineer dispatch with python-reviewer; every instruction-author with instruction-reviewer (per `feedback_dual_agent_verify_command_statements` + `feedback_iterative_review_loop_preferred`).
5. **Phase 6 is the forcing-functions gate ship** — on land, edit `01-` to mark Phase 5b ABSORBED HERE.
6. **Phase 11 edits shipped `/breakdown`** — its helper tests must stay green; the bare-verb rename drops the `NNN` arg from breakdown's handoff block.
7. **Phase 13 is the empirical-validation stop** — not DONE until the testForge20 loop runs clean.

## Out of scope (this plan)

- `/review`, `/verify`, `/summarize`, `/finalize`, `/fix`, `/refactor`, `/security` redesigns — each its own plan. `/implement` invokes `code-reviewer` directly per task; the full `/review` (feature-boundary specialist review) is distinct.
- **`tech-writer` / feature-level `docs/` generation** — that is `/finalize`'s job, NOT per-task. `/implement` relies on the implementing engineer writing **inline docs** (docstrings/JSDoc) as part of the code, verified by `code-reviewer` (per `tech-writer.md:49`/`:132`). Do NOT wire `tech-writer` or per-task `docs/` regeneration into `/implement` — `main.md` should carry an explicit "not called here" note so a future session does not add it.
- **`docs/` markdown re-index** — the CBM post-commit refresh (Phase 8) re-indexes committed *code* (incl. inline docs); `docs/` markdown only changes at `/finalize`, which owns its own CBM refresh.
- New agent types — `/implement` consumes existing `.claude/agents/<name>.md`. No agent rewrite scheduled (PC4). The unrelated `api-designer.md:7` stray-`b` typo is a separate trivial fix, not part of this plan.
- Re-adding optional explicit task targeting (`/implement N`) — deliberately dropped (decision 2); revisit only if empirical need surfaces.
- AC-verifier / Chrome integration — `/verify` territory.
- Self-repair iteration-count tuning (3) — future-work if empirical signal differs.
- `model:` frontmatter override — per `feedback_avoid_command_model_override`, do NOT add.

## Related plans

- `01-CONSTITUTION-FORCING-FUNCTIONS-PLAN.md` — Phase 5b ABSORBED into Phase 6 here (was "Phase 7" in the prior draft; renumbered).
- `09-BREAKDOWN-COMMAND-REDESIGN-PLAN.md` — SHIPPED producer of the read contract; Phase 11 edits its spec + helper for the rename.
- `02-PLAN-COMMAND-REDESIGN-PLAN.md` — sibling helper-owns-shape pattern parent.
- `03-DISCOVER-HANDOFF-PLAN.md` — Step 8 outcome-reminder wire-in deferred until `/implement` exists; revisit after Phase 10.
- `05-structural-integration-check-plan.md` — added §7 to `code-reviewer.md`; Phase 5 invokes `code-reviewer`, so it propagates automatically.

## Resolved questions (were "open" in the prior draft)

1. **Agent ecosystem** — `code-reviewer` + 13 task agents exist + `.devforge`-aligned (PC4). RESOLVED: no rewrite.
2. **Wrapper-mode commit attribution** — Phase 7 honors `COMMIT_ATTRIBUTION` from config. Verify the key exists via `configure_helper` schema before Phase 7 ships.
3. **Self-repair loop ownership** — helper owns the ≤3 counter (Phase 4). RESOLVED: helper-owns.
4. **Crash-recovery UI** — `AskUserQuestion` single-line, options resume/rollback/skip/manual (Phase 9). RESOLVED.
5. **Gate-failure vs commit** — under no-commit-until-approval, a gate failure never reaches the approve prompt, so no commit exists to roll back; partial work sits in the working tree; user repairs/skips/stops (Phase 6/7). RESOLVED.
</content>
</invoke>
