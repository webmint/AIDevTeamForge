# 07-EXECUTE-TASK-REDESIGN-PLAN

**Status**: Drafted 2026-05-21.
**Branch**: `develop-2.0-init`
**Driver**: `/execute-task` is documented as a load-bearing command in the consumer-shipped template (`src/CLAUDE.md` — "Executes a single task from the breakdown using the assigned specialized agent. Follows enforced workflow: pre-flight → agent execution → post-execution verification → code review → memory update. WIP commits accumulate across tasks and are squashed by `/finalize`."), but no source spec exists at `src/commands/execute-task/`. Multiple downstream plans assume `/execute-task` exists and reference it as the integration surface — most concretely `01-CONSTITUTION-FORCING-FUNCTIONS-PLAN.md` Phase 5b (verify-gate wire-in) and `03-DISCOVER-HANDOFF-PLAN.md`'s deferred outcome-reminder wire-in. This plan delivers `/execute-task` as a buildable source spec + helper substrate and absorbs the dependent forcing-functions Phase 5b directly so the integration surface lands with the command, not as a separate post-hoc patch.

## Context for next session

`src/commands/` audit 2026-05-21 confirms 10 workflow commands documented in the consumer template have NO source spec yet:

```
MISSING: breakdown, execute-task, review, verify, summarize, finalize, fix, refactor, security, audit
```

This plan targets **`/execute-task` only**. Other missing commands stay out of scope; each needs its own plan when prioritized. `/breakdown` is the immediate upstream dependency (it produces the task files `/execute-task` consumes) — it is treated here as a **hard precondition**, not absorbed into scope.

The consumer-template description at `src/CLAUDE.md` is the canonical contract `/execute-task` must satisfy. This plan does NOT re-derive the contract — it implements it.

### Existing artifacts to read before resuming

- `src/CLAUDE.md` — consumer-template `/execute-task` description (the canonical workflow contract).
- `01-CONSTITUTION-FORCING-FUNCTIONS-PLAN.md` Phase 5b (will be absorbed into Phase 7 of this plan).
- `02-PLAN-COMMAND-REDESIGN-PLAN.md` — sibling plan for `/plan` command; same helper-owns-shape pattern.
- `03-DISCOVER-HANDOFF-PLAN.md` — upstream handoff schema this command may need to read.
- Existing helper subpackages under `src/devforge/lib/_research/`, `_specify/`, `_constitute/`, `_discover/` — pattern parents for the new `_execute_task/` subpackage.
- `feedback_helper_owns_shape_principle.md`, `feedback_test_first_python_helpers.md`, `feedback_iterative_review_loop_preferred.md`, `feedback_dual_agent_verify_command_statements.md`, `feedback_zero_escape_hatch_policy.md`.

### Wrapper-mode awareness

Per memory `project_wrapper_git_strategy.md`: wrapper mode auto-commits source per task; squashes at verify; uses `[TICKET-ID] - desc` commit format from branch name. `/execute-task` is the per-task commit-emitting command — must respect wrapper-mode vs non-wrapper-mode branching from `.devforge/project-config.json`.

### Crash recovery

Per `src/CLAUDE.md` template: `/execute-task` writes WIP marker `.devforge/wip.md` before execution + creates git checkpoints at each phase. If interrupted, next run detects via the marker and offers resume/rollback/skip. WIP marker carries `Command` field; mismatched-command invocation surfaces a "resolve previous session first" prompt.

## Design

### Helper-owns-shape conventions

- Source spec at `src/commands/execute-task/main.md` (LLM instructions, prose) + `src/commands/execute-task/references/*.md` (reference docs the spec cites).
- Helper subpackage at `src/devforge/lib/_execute_task/` (Python; structured state-machine helpers — read task file, write WIP marker, capture diff, etc.). Helper owns shape; LLM composes values.
- Thin helper shim at `src/devforge/lib/execute_task_helper` (POSIX launcher, mirrors `constitute_helper`).
- Emitter wire-in at `scripts/emitters/claude.py` `_PROMOTED` list per `feedback_emitter_promoted_cross_check.md`.

### Task file format (read contract — NOT owned here) — UPDATED 2026-05-25 per 09-BREAKDOWN

`/breakdown` **shipped** (`09-BREAKDOWN-COMMAND-REDESIGN-PLAN.md`, helper + spec). It is the format owner. The machine-readable contract `/execute-task` consumes is **NOT YAML frontmatter** — it is the structured `specs/<NNN-feature>/breakdown-handoff.json` (schema `src/devforge/lib/_breakdown/handoff_schema.py`, `handoff_kind="breakdown"`), produced by `breakdown_helper finalize-handoff`. The human `tasks/<NNN-short-title>.md` files stay pure markdown per `src/devforge/storage-rules.md` §Task File Format (a `**Agent**:` line, NOT frontmatter).

**Read-only contract** (`/execute-task` obeys this producer):
- `specs/<NNN-feature>/breakdown-handoff.json` carries a `tasks[]` array; each `TaskRow` declares `number`, `title`, `agent` (matches `.claude/agents/<agent-name>.md`), `depends_on`, `blocks`, `touched_files`, `expects`, `produces`, `ac_addressed`, `doc_refs`, `review_checkpoint`. `/execute-task N` loads this JSON and indexes by task number.
- `provenance.upstream_handoff_path` → the sibling `plan-handoff.json` (`handoff_kind="plan"`); `provenance.spec_path` → the feature `spec.md`.
- `tasks/README.md` declares the human dependency graph + execution order; `dependency_graph` + `additions` are also captured in the JSON.

⚠️ **SUPERSEDES**: the frontmatter-based sketches elsewhere in this DRAFT plan must be reworked to read `breakdown-handoff.json` when 07 is built — specifically the `parse_task_file` helper (reads "YAML frontmatter"), the agent-dispatch step ("`agent:` frontmatter"), and the Phase 11 hand-authored task file ("frontmatter `agent: backend-engineer`"). When 07 executes, replace those with a `read-breakdown-handoff` consumer of `breakdown_helper`'s output. The testForge20 smoke (Phase 11) should run real `/breakdown` to produce the JSON rather than hand-authoring frontmatter.

### Scope-aware verification

Per `src/CLAUDE.md` "Verification" section: after agent edits, identify touched files via `git diff` against task-start checkpoint; for each touched file, find its package via `PACKAGE_STACKS` path lookup (longest path prefix wins); run that package's `type_check_command` + `lint_command`. Build runs once per task, aggregated. Files outside any package fall back to primary-stack commands. Skip `"N/A"` silently.

Self-repair loop: type-check / lint failure → up to 3 auto-repair iterations before stop-and-report. Code-review findings reported but NOT auto-repaired.

### Forcing-functions integration (absorbs 01-CONSTITUTION-FORCING-FUNCTIONS Phase 5b)

After agent edits + post-execution verification but BEFORE user-presentation: invoke each enabled `constitute_helper verify-<rule>` verb (where `<rule>` ranges over `forcing_functions.<name>` keys in `.devforge/constitute.json` with `enabled: true`). For each verb:
- If exit 0: continue.
- If exit 2: STOP. Capture stdout JSON (the programmatic finding report). Relay the JSON to the user as a fenced code block — NOT stderr text (stderr `path:line: KIND` prefix is ambiguous when path contains `:`, per `_shared.emit_findings` Known Limitations). Do not declare task complete.

Per `01-CONSTITUTION-FORCING-FUNCTIONS-PLAN.md` Phase 5: the verify-gate is the load-bearing integration surface for the detector family; the pre-commit hook is the bonus that catches commits outside `/execute-task` agent workflow. Both surfaces consume the same verbs.

---

## Phase 0 — Scope + precondition audit

**Owner**: orchestrator (one-shot read-only sweep).

### Files

- (no edits) — this phase produces a written precondition list in the next-session context.

### Audit checklist

```bash
# Confirm gap state matches plan assumptions.
ls src/commands/execute-task/ 2>&1                                 # expect: No such file or directory
ls src/devforge/lib/execute_task_helper* 2>&1                       # expect: No such file or directory
ls src/devforge/lib/_execute_task/ 2>&1                             # expect: No such file or directory
ls src/commands/breakdown/ 2>&1                                     # expect: No such file or directory (precondition flag)
grep -nE "/execute-task|execute_task_helper" src/CLAUDE.md          # expect: hits in the template
grep -nE "execute-task" scripts/emitters/claude.py                  # expect: zero hits (no emitter wire-in yet)
grep -nE "^- \`/execute-task\`" src/commands/*/main.md 2>&1 | head  # expect: zero hits (no upstream command references it)
```

### Verify

```bash
# Audit ledger captured at audit-2026-05-21-execute-task.md (one-shot scratch; not committed).
ls audit-2026-05-21-execute-task.md 2>/dev/null
```

### Precondition declarations

- **PC1**: `/breakdown` source spec does NOT need to exist for this plan to ship — Phase 11 testForge20 smoke uses a hand-authored task file matching the documented format.
- **PC2**: `01-CONSTITUTION-FORCING-FUNCTIONS-PLAN.md` Phase 0+1+3+4 must be SHIPPED (all consumer-side verify-`<rule>` verbs available). Confirmed shipped at commits `ea18cd1`, `ccc25b8`, `a370229`, `4b058da`. PC2 met.
- **PC3**: `.devforge/project-config.json` schema must already define `PACKAGE_STACKS`, `wrapper_mode`, `COMMIT_ATTRIBUTION`. Verify via `configure_helper render-config` on testForge20.

---

## Phase 1 — Helper substrate

**Owner**: python-engineer.

### Files

- `src/devforge/lib/_execute_task/__init__.py` — subpackage marker; one-paragraph docstring naming the four state-machine domains the subpackage handles (task-file reading, WIP marker, scope-aware verify, forcing-functions gate).
- `src/devforge/lib/_execute_task/_state.py` — `ExecuteTaskState` dataclass (frozen) capturing: `task_file_path: Path`, `task_number: int`, `feature_dir: Path`, `agent_name: str`, `phase: Literal["preflight", "agent", "verify", "review", "gate", "commit", "complete"]`, `wip_marker_path: Path`, `checkpoint_sha: Optional[str]`, `touched_files: list[str]`.
- `src/devforge/lib/_execute_task/_wip.py` — `write_wip_marker(state)`, `read_wip_marker(devforge_dir) -> Optional[dict]`, `clear_wip_marker(devforge_dir)`. Mandatory `Command: /execute-task` field per `src/CLAUDE.md` crash-recovery spec.
- `src/devforge/lib/_execute_task/_task_file.py` — `parse_task_file(path: Path) -> dict` — read YAML frontmatter + body; required keys: `agent`, `number`, `title`. Raise `ValueError` if any required key missing.
- `src/devforge/lib/_execute_task/_cli.py` — subcommand router (mirrors `_constitute/_cli.py` shape).
- `src/devforge/lib/execute_task_helper` — POSIX launcher (mirror `constitute_helper`).
- `src/devforge/lib/execute_task_helper.py` — Python entry point (`from _execute_task._cli import main; sys.exit(main())`).
- `tests/lib/test_execute_task_state.py` — `ExecuteTaskState` dataclass tests (frozen, type validation, transition allowed-list).
- `tests/lib/test_execute_task_wip.py` — WIP marker round-trip tests; mismatched-command detection.
- `tests/lib/test_execute_task_task_file.py` — task-file parser tests (real-producer: write real `.md` files to tempdir, then parse).

### Verify

```bash
.venv-test/bin/pytest tests/lib/test_execute_task_state.py tests/lib/test_execute_task_wip.py tests/lib/test_execute_task_task_file.py -v
.venv-test/bin/python src/devforge/lib/execute_task_helper.py --help 2>/dev/null && echo "Phase 1 entry-point ok" || echo "Phase 1 not wired"
python3 -c "import sys; sys.path.insert(0,'src/devforge/lib'); from _execute_task._state import ExecuteTaskState; from _execute_task._wip import write_wip_marker, read_wip_marker; from _execute_task._task_file import parse_task_file; print('Phase 1 substrate ok')"
```

---

## Phase 2 — Pre-flight check subcommand

**Owner**: python-engineer + instruction-author.

### Files

- `src/devforge/lib/_execute_task/_cmds_preflight.py` — `cmd_preflight(args)`:
  1. Read `constitution.md` content into structured-finding output.
  2. Read `.devforge/memory.md` content.
  3. Verify branch state — refuse to run on `main` / default branch; require feature branch (e.g., `spec/NNN-name`).
  4. Detect existing WIP marker via `_wip.read_wip_marker` — if present + command mismatch, exit `EXIT_FINDINGS` with stderr instruction.
  5. Snapshot current git HEAD SHA into state.
  6. Validate task-file argument resolves to an existing file under `specs/<feature>/tasks/`.
  7. Emit JSON to stdout containing: constitution-summary digest, memory-summary digest, task-file path, agent-name, head-sha, branch-name.
- `src/commands/execute-task/main.md` — partial author (Phase 0 + Pre-flight steps only; other phases land in later spec passes).
- `tests/lib/test_execute_task_cmds_preflight.py` — full coverage of the 7 sub-checks.

### Verify

```bash
.venv-test/bin/pytest tests/lib/test_execute_task_cmds_preflight.py -v
.venv-test/bin/python src/devforge/lib/execute_task_helper.py preflight --help
grep -nE "Pre-flight|preflight" src/commands/execute-task/main.md
```

---

## Phase 3 — Agent dispatch + scope constraints

**Owner**: instruction-author (spec); python-engineer (helper for state capture).

### Files

- `src/commands/execute-task/main.md` — extend with agent-dispatch step: spec instructs the LLM to invoke the agent named in the task file's `agent:` frontmatter using the Task tool. Scope constraint: agent receives the task body + the relevant feature spec + the constitution as the brief; agent is told its scope is the task's `touched_files` list (if declared) or "whatever the task body specifies."
- `src/commands/execute-task/references/agent-brief.md` — reference doc describing the brief shape: goal, integration context, constraints, edge cases, success criteria, what NOT to do. Cross-refs `feedback_no_underspecification_when_delegating.md`.
- `src/devforge/lib/_execute_task/_cmds_capture.py` — `cmd_capture_touched_files(args)` — call `git diff --name-only <checkpoint-sha>` to capture the set of files the agent modified. Emit JSON list.
- `tests/lib/test_execute_task_cmds_capture.py` — test capture with seeded git tempdir.

### Verify

```bash
.venv-test/bin/pytest tests/lib/test_execute_task_cmds_capture.py -v
.venv-test/bin/python src/devforge/lib/execute_task_helper.py capture-touched-files --help
grep -nE "Agent dispatch|agent.*frontmatter" src/commands/execute-task/main.md
grep -nE "agent-brief" src/commands/execute-task/main.md
```

---

## Phase 4 — Scope-aware verification + self-repair loop

**Owner**: python-engineer.

### Files

- `src/devforge/lib/_execute_task/_cmds_verify.py` — `cmd_verify_touched(args)`:
  1. Read `touched_files` list from prior phase's JSON.
  2. Load `PACKAGE_STACKS` from `.devforge/project-config.json`.
  3. For each touched file: longest-path-prefix match against `PACKAGE_STACKS` → package's `type_check_command` + `lint_command`. Files outside any package → primary-stack fallback (`TYPE_CHECK_COMMANDS[0]` etc.).
  4. Aggregate type-check + lint invocations (de-dup commands; run each command once over the union of files it covers).
  5. Skip `"N/A"` commands silently.
  6. Build runs once per task at end, aggregated across touched packages.
  7. Self-repair loop: if a command exits non-zero, return `{phase: "self_repair", failed_command: ..., output: ...}` JSON to caller; caller decides whether to retry (up to 3 iters managed by command spec).
  8. After 3 failed iterations: emit `EXIT_FINDINGS` with structured stderr.
- `tests/lib/test_execute_task_cmds_verify.py` — fixture project with `.devforge/project-config.json` declaring 2 packages, multiple files; verify command-aggregation + self-repair-iteration counter.

### Verify

```bash
.venv-test/bin/pytest tests/lib/test_execute_task_cmds_verify.py -v
.venv-test/bin/python src/devforge/lib/execute_task_helper.py verify-touched --help
```

---

## Phase 5 — Code-review integration

**Owner**: instruction-author (spec); python-engineer (helper output capture).

### Files

- `src/commands/execute-task/main.md` — extend with code-review dispatch step: spec instructs LLM to invoke the `code-reviewer` agent (consumer-side `.claude/agents/code-reviewer.md`) with the touched_files list + the constitution + the task body. The agent's findings are surfaced to the user but do NOT auto-repair; critical-severity findings block task completion.
- `src/devforge/lib/_execute_task/_cmds_review.py` — `cmd_capture_review_findings(args)` — accept code-reviewer agent stdout JSON (assumes the agent returns structured JSON); parse + filter by severity; emit `EXIT_FINDINGS` if any critical-severity finding present.
- `tests/lib/test_execute_task_cmds_review.py` — fixtures for clean-review + critical-blocking review.

### Verify

```bash
.venv-test/bin/pytest tests/lib/test_execute_task_cmds_review.py -v
.venv-test/bin/python src/devforge/lib/execute_task_helper.py capture-review --help
grep -nE "code-reviewer|critical.*block" src/commands/execute-task/main.md
```

---

## Phase 6 — Memory + session-state update

**Owner**: python-engineer.

### Files

- `src/devforge/lib/_execute_task/_cmds_session.py` — `cmd_update_session_state(args)`:
  1. Read existing `.devforge/session-state.md` if present.
  2. Build new state: current feature, progress (N-of-M tasks complete), last 3 task-modification entries, last 3 decisions captured from task completion notes.
  3. Overwrite `.devforge/session-state.md` (fixed-size, max ~40 lines per `src/CLAUDE.md` Session Continuity contract).
  4. Append a one-line entry to `.devforge/memory.md` describing the task outcome + any lessons surfaced (read from code-review findings).
- `tests/lib/test_execute_task_cmds_session.py` — round-trip session-state writes + sliding-window enforcement.

### Verify

```bash
.venv-test/bin/pytest tests/lib/test_execute_task_cmds_session.py -v
.venv-test/bin/python src/devforge/lib/execute_task_helper.py update-session-state --help
```

---

## Phase 7 — Forcing-functions verify-gate integration (absorbs 01-CONSTITUTION-FORCING-FUNCTIONS Phase 5b)

**Owner**: instruction-author (spec); python-engineer (helper dispatch).

### Files

- `src/commands/execute-task/main.md` — extend with verify-gate step, inserted AFTER post-execution verification (Phase 4) + code-review (Phase 5) but BEFORE user-presentation. Step body:
  1. Read `forcing_functions` block from `.devforge/constitute.json`.
  2. For each `<rule>` with `enabled: true`:
     - Invoke `constitute_helper verify-<rule> --root <consumer-root>`.
     - On exit 0: continue to next rule.
     - On exit 2: STOP. Capture stdout JSON (the programmatic finding report). Relay to user as a fenced JSON code block. Stderr lines are supplementary; MUST NOT be the source of relayed findings (per `_shared.emit_findings` Known Limitations — `path:line: KIND` prefix ambiguous when path contains `:`). Do not declare task complete.
  3. If all enabled rules exit 0: declare task complete (proceed to commit phase).
- `src/commands/execute-task/references/forcing-functions-gate.md` — reference doc explaining the gate, the verbs (`verify-magic-enum`, `verify-cross-layer-imports`, `verify-any-leak`), the exit semantics, and how to triage findings.
- `src/devforge/lib/_execute_task/_cmds_gate.py` — `cmd_run_forcing_functions_gate(args)`:
  1. Read `forcing_functions` block.
  2. For each enabled rule, subprocess `constitute_helper verify-<rule>` with shared `--root` + `--config` flags.
  3. Aggregate per-rule exit codes + stdout JSON reports.
  4. Emit aggregate JSON `{gate: "forcing_functions", rules_run: [...], rules_failed: [...], aggregate_exit: 0|2}` to stdout.
  5. Exit 0 if no rule failed; exit 2 if any rule failed.
- `tests/lib/test_execute_task_cmds_gate.py` — fixture with 2 rules enabled, one passing, one failing → aggregate exit 2; both passing → exit 0; both disabled → exit 0 + empty report.

### Verify

```bash
.venv-test/bin/pytest tests/lib/test_execute_task_cmds_gate.py -v
.venv-test/bin/python src/devforge/lib/execute_task_helper.py run-forcing-functions-gate --help
grep -nE "forcing.functions|verify-magic-enum|verify-cross-layer-imports|verify-any-leak" src/commands/execute-task/main.md src/commands/execute-task/references/forcing-functions-gate.md
```

Cross-reference cleanup: update `01-CONSTITUTION-FORCING-FUNCTIONS-PLAN.md` Phase 5 to mark 5b as ABSORBED INTO 07-EXECUTE-TASK-REDESIGN-PLAN.md Phase 7. Update CLAUDE.md active-plans row for `01-` to reflect the absorption.

---

## Phase 8 — WIP commit + crash-recovery hardening

**Owner**: python-engineer + instruction-author.

### Files

- `src/devforge/lib/_execute_task/_cmds_commit.py` — `cmd_wip_commit(args)`:
  1. Stage `touched_files` only (NOT `git add -A` per `feedback_absolute_paths_in_destructive_commands.md`).
  2. Read wrapper-mode flag + ticket-id from `.devforge/project-config.json` + branch name.
  3. Compose commit message: wrapper-mode → `[TICKET-ID] - desc (Task NNN)`; non-wrapper → `[WIP] task: <task-title> (Task NNN)`.
  4. Honor `COMMIT_ATTRIBUTION` from project config (no hardcoded Co-Authored-By).
  5. Commit; capture new HEAD SHA into state; clear WIP marker.
- `src/commands/execute-task/main.md` — extend with WIP-commit step + crash-recovery offer-options spec (resume / rollback / skip / manual per `src/CLAUDE.md`).
- `src/commands/execute-task/references/crash-recovery.md` — reference doc for the 4 recovery options + WIP marker fields + Command-mismatch detection.
- `tests/lib/test_execute_task_cmds_commit.py` — wrapper-mode + non-wrapper-mode commit-message format verification; staging-respect-touched-files-only assertion.

### Verify

```bash
.venv-test/bin/pytest tests/lib/test_execute_task_cmds_commit.py -v
.venv-test/bin/python src/devforge/lib/execute_task_helper.py wip-commit --help
grep -nE "crash.recovery|resume.*rollback.*skip" src/commands/execute-task/main.md src/commands/execute-task/references/crash-recovery.md
```

---

## Phase 9 — Command spec finalization

**Owner**: instruction-author.

### Files

- `src/commands/execute-task/main.md` — full pass: ensure all 7 enforced-workflow phases (pre-flight → agent execution → verification → review → forcing-functions gate → memory update → commit) are present, ordered, and cite their reference docs. Frontmatter declares `model: sonnet` (per `feedback_avoid_command_model_override.md`, do NOT add `model:` casually — only if user confirms). Bash-tool permission allowlist declares the helper verbs explicitly.
- `src/commands/execute-task/references/` — confirm all 3 reference docs present (`agent-brief.md`, `forcing-functions-gate.md`, `crash-recovery.md`). Add `verification-flow.md` if scope-aware verify needs deeper-than-spec explanation.

### Verify

```bash
# Command spec sentence-level hallucination check (per feedback_sentence_level_hallucination_check_specs):
# every sentence either mechanically true / verifiable / explicit forward-ref.
# Manual review pass — flag any sentence that fails the check.

ls src/commands/execute-task/main.md
ls src/commands/execute-task/references/
grep -cE "^#" src/commands/execute-task/main.md   # expect ≥ 7 (one heading per phase)
```

Dispatch instruction-reviewer iteratively on `main.md` per `feedback_iterative_review_loop_preferred.md`. Loop until clean.

---

## Phase 10 — Emitter wire-in

**Owner**: python-engineer.

### Files

- `scripts/emitters/claude.py` — add `"execute-task"` to `_PROMOTED` list (per `feedback_emitter_promoted_cross_check.md`). Verify the emitter picks up the new `src/commands/execute-task/` source dir and emits to consumer's `.claude/commands/execute-task.md`.
- `manifest.json` — declare `.claude/commands/execute-task.md` + `.devforge/lib/execute_task_helper` + `.devforge/lib/_execute_task/` as emitted artifacts (so `install.sh` / `update.sh` ship them).
- `install.sh` / `update.sh` — verify the helper subpackage gets copied to consumer's `.devforge/lib/_execute_task/` (test via testForge20 install).

### Verify

```bash
grep -nE "execute-task" scripts/emitters/claude.py
grep -nE "execute-task|execute_task_helper" manifest.json
# Emitter end-to-end smoke against testForge20:
./scripts/generate.sh ~/Projects/testForge20 2>&1 | tail -20
ls ~/Projects/testForge20/.claude/commands/execute-task.md
ls ~/Projects/testForge20/.devforge/lib/execute_task_helper
ls ~/Projects/testForge20/.devforge/lib/_execute_task/
```

---

## Phase 11 — testForge20 install smoke

**Owner**: orchestrator (manual e2e).

### Procedure

1. Hand-author a task file at `~/Projects/testForge20/specs/NNN-test-feature/tasks/001-trivial.md` matching the documented format (frontmatter `agent: backend-engineer`, body = a trivial "add a comment to file X" instruction).
2. Run `/execute-task 1` (the consumer-side slash command emitted by Phase 10).
3. Observe:
   - Pre-flight reads constitution + memory; emits structured digest.
   - Agent dispatched with full brief; trivial edit lands.
   - Scope-aware verify runs the relevant package's type-check + lint commands (or `"N/A"` no-ops).
   - Code-reviewer agent dispatches; clean review for trivial change.
   - Forcing-functions gate runs each enabled `verify-<rule>`; exit 0 if no violations (likely, given trivial edit scope).
   - WIP commit lands with correct ticket-id-format message.
   - Session-state.md updated; memory.md appended.
4. Document outcome at `EXECUTE-TASK-SMOKE-2026-MM-DD.md`.

### Verify

```bash
ls EXECUTE-TASK-SMOKE-*.md
cd ~/Projects/testForge20 && git log --oneline -3
cat ~/Projects/testForge20/.devforge/session-state.md | head -20
```

Stop criteria for Phase 11:
- testForge20 smoke produces a clean exit-0 task completion.
- Forcing-functions gate fires (even if exit-0); the relay-stdout-JSON behavior is observable.
- WIP commit format matches wrapper-mode convention.

---

## Phase 12 — Documentation propagation

**Owner**: instruction-author.

### Files

- `CHANGELOG.md` — entry for `/execute-task` ship + forcing-functions gate integration.
- Repo-root `CLAUDE.md` — add `/execute-task` entry to active-plans table OR mark this plan as DONE under "Completed plans archived at `done-plans/`" line. Update `01-CONSTITUTION-FORCING-FUNCTIONS-PLAN.md` table entry to note Phase 5b ABSORBED.
- `DEVELOPMENT-STATUS.md` — single-line entry under "Active commands / helpers".
- `src/CLAUDE.md` (consumer template) — only verify that the existing `/execute-task` description matches the implemented spec. If the implemented spec drifts from the template description, choose: update template OR update spec. Document choice. Do NOT silently let drift land.

### Verify

```bash
grep -nE "/execute-task|execute_task_helper" CHANGELOG.md CLAUDE.md DEVELOPMENT-STATUS.md
# Cross-check: template description vs implemented spec; drift report.
diff <(sed -n '/^#### `\/execute-task`/,/^####/p' src/CLAUDE.md) <(echo '<implemented spec phase headings>')
```

---

## When resuming work

1. Read this plan top-to-bottom.
2. Cross-read `src/CLAUDE.md` `/execute-task` section (canonical contract).
3. Cross-read `01-CONSTITUTION-FORCING-FUNCTIONS-PLAN.md` Phase 5 + Phase 7 of THIS plan (gate integration).
4. Verify state of each phase on-disk:
   ```bash
   ls src/devforge/lib/_execute_task/ 2>/dev/null                                                        # Phase 1
   .venv-test/bin/python src/devforge/lib/execute_task_helper.py preflight --help >/dev/null 2>&1 && echo "Phase 2 wired"  # Phase 2
   .venv-test/bin/python src/devforge/lib/execute_task_helper.py capture-touched-files --help >/dev/null 2>&1              # Phase 3
   .venv-test/bin/python src/devforge/lib/execute_task_helper.py verify-touched --help >/dev/null 2>&1                     # Phase 4
   .venv-test/bin/python src/devforge/lib/execute_task_helper.py capture-review --help >/dev/null 2>&1                     # Phase 5
   .venv-test/bin/python src/devforge/lib/execute_task_helper.py update-session-state --help >/dev/null 2>&1               # Phase 6
   .venv-test/bin/python src/devforge/lib/execute_task_helper.py run-forcing-functions-gate --help >/dev/null 2>&1         # Phase 7
   .venv-test/bin/python src/devforge/lib/execute_task_helper.py wip-commit --help >/dev/null 2>&1                         # Phase 8
   ls src/commands/execute-task/main.md src/commands/execute-task/references/ 2>/dev/null                                  # Phase 9
   grep -nE "execute-task" scripts/emitters/claude.py manifest.json                                                        # Phase 10
   ls EXECUTE-TASK-SMOKE-*.md 2>/dev/null                                                                                  # Phase 11
   grep -nE "/execute-task|execute_task_helper" CHANGELOG.md CLAUDE.md DEVELOPMENT-STATUS.md                               # Phase 12
   ```
5. For each unfinished phase, dispatch the named owner with a complete brief per `feedback_no_underspecification_when_delegating.md`. Follow every python-engineer dispatch with a python-reviewer dispatch per `feedback_dual_agent_verify_command_statements.md`. Follow every instruction-author dispatch with an instruction-reviewer dispatch.
6. **Phase 7 is the forcing-functions gate ship.** Once Phase 7 lands, edit `01-CONSTITUTION-FORCING-FUNCTIONS-PLAN.md` to mark Phase 5b as ABSORBED HERE.
7. **Phase 11 is the empirical-validation stop.** Do not declare DONE until testForge20 smoke produces a clean task completion run.

## Out of scope (this plan)

- `/breakdown` command redesign — separate plan if also missing. This plan treats `/breakdown` task-file output as a documented read contract; absence of `/breakdown` requires hand-authored task files for Phase 11 smoke only.
- `/review`, `/verify`, `/summarize`, `/finalize`, `/fix`, `/refactor`, `/security`, `/audit` redesigns — each needs its own plan. `/execute-task` invokes the `code-reviewer` agent directly during its workflow; full `/review` command (which runs specialist review-agents at feature boundary, not task boundary) is distinct.
- Pre-commit hook script (the OTHER forcing-functions surface) — separate plan or absorbed by a future Phase 5a follow-up.
- New agent types — `/execute-task` consumes existing `.claude/agents/<name>.md` from the consumer install; agent ecosystem changes are out of scope.
- AC-verifier MCP / Chrome integration — that's `/verify` territory.
- Self-repair iteration count tuning (currently 3 per template) — tunable in future-work if empirical signal shows different number is right.
- `model:` frontmatter override on the command spec — per `feedback_avoid_command_model_override.md`, do NOT add unless user explicitly confirms; default-inherit session model.

## Related plans

- `01-CONSTITUTION-FORCING-FUNCTIONS-PLAN.md` — Phase 5b (verify-gate wire-in) is ABSORBED into Phase 7 of THIS plan. Update sibling plan's Phase 5 section to reflect absorption when Phase 7 ships.
- `02-PLAN-COMMAND-REDESIGN-PLAN.md` — sibling redesign for `/plan`; same helper-owns-shape pattern; this plan does NOT depend on `/plan` redesign landing (parallel work).
- `03-DISCOVER-HANDOFF-PLAN.md` — Step 8 referenced an outcome-reminder wire-in that was DEFERRED because `/execute-task` did not exist. Once this plan ships Phase 9, revisit `03-` Step 8 to land the outcome-reminder.
- `04-PR-REVIEW-PLAN.md` — sibling; does NOT depend on `/execute-task`.
- `05-structural-integration-check-plan.md` — adds Section 7 to `code-reviewer.md`; this plan's Phase 5 invokes `code-reviewer`, so `05-` improvements automatically propagate.
- `06-CONDITIONAL-CONTEXT-PLAN.md` — **ABORTED 2026-05-24** (archived to `done-plans/`); premise false + wrong mechanism. Superseded by `08-CLAUDE-MD-COMMAND-TRIM-PLAN.md`. No bearing on `/execute-task` shape.

## Open questions (surface to user before Phase 1)

1. **Agent ecosystem dependency** — what agents are expected to exist in the consumer install before `/execute-task` runs? At minimum: the task-assigned agent (varies per task) + `code-reviewer`. List of agents that ship by default with forge 2.0 needs confirmation.
2. **Wrapper-mode commit attribution** — wrapper repos may have different attribution conventions than the forge dev repo. Phase 8 honors `COMMIT_ATTRIBUTION` from project config, but the project-config schema may not declare this key yet. Verify against `configure_helper` schema.
3. **Self-repair loop ownership** — Phase 4 helper returns failed-command output; spec instructs LLM to attempt repair. Should the helper own the repair-loop counter (and refuse after 3 iterations) or should the command spec own it? Helper-owns-counter is safer (cannot be bypassed by LLM judgment); spec-owns-counter is more flexible. Recommend helper.
4. **Crash-recovery option presentation** — `src/CLAUDE.md` lists 4 options (resume / rollback / skip / manual). AskUserQuestion supports single-line questions; multi-line context falls through to prose prompt per `feedback_askuserquestion_single_line_only.md`. Confirm UI shape before Phase 8 ships.
5. **Verify-gate failure as task-incomplete signal** — Phase 7 says "do not declare task complete" on gate failure. Does this leave the WIP commit in place (so user can investigate + repair) or roll it back? Plan currently leaves it in place (commit landed; gate findings surfaced; user decides). Confirm.
