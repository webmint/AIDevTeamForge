# 17 — /implement Per-Task Reviewer Panel + Test Gate

**Status**: DRAFTED 2026-06-07, not started. All eleven decisions (D1–D11) RESOLVED (D8 amended 2026-06-07 with one narrow verdict-line carve-out); no open decisions. Hard precondition SATISFIED — plan 15 SHIPPED `720253f` (2026-06-07). This plan is CONSUMER wiring of plan-15's finished reviewer roster into `/implement`'s per-task loop — it makes NO SUBSTANTIVE agent charter change (the lone exception is Phase 3 sub-track A's verdict-line markdown-level normalization; see D8).
**Branch**: `develop-2.0-init`

## Driver

`/implement` drains a feature's breakdown tasks one at a time. Today each task's per-task review (PHASE 6) runs a SINGLE `code-reviewer` agent, and PHASE 5 (scope-aware verify) runs type-check + lint + build but NO tests. The deferred review dimensions — test adequacy, security depth, performance — currently run only at feature-level `/review`, AFTER all N tasks are built.

That ordering is wrong for agent-driven development. The framework's engineer→reviewer loop earns its keep by catching compounding bugs early (shift-left). And in agent-driven development the dominant cross-task pollution mechanism is **pattern replication**: a later task's agent reads existing code and copies its patterns, good or bad. A bad pattern established in task 1 therefore propagates to every downstream task unless it is caught at the task that introduced it. A task-1 defect surfaced only at feature-level `/review` is already built upon by the time anyone sees it.

**Core principle**: per-task review must hunt the FULL spectrum, not just code-reviewer's generalist pass, so compounding defects are caught at the task that introduced them. This plan widens the per-task review to a full READ-ONLY PANEL (code-reviewer + qa-reviewer + security-reviewer + performance-analyst) and adds a per-task test gate (test EXECUTION in PHASE 5, test ADEQUACY assessment in the PHASE 6 panel).

Plan 15 (Agent Standardization) just made this clean to build. Its Phase 1 (committed `fcc4947`) standardized the read-only reviewers — all tools-locked to read-only (`Read, Grep, Glob, Bash`; no `Edit`/`Write`/`Agent`), all on a unified severity scale (`Critical/High/Medium/Info`), all single-responsibility. So a per-task panel of read-only reviewers CANNOT step on each other (they cannot write), and their findings merge on one severity scale. The earlier alternative — collapsing all dimensions into one "mega-verifier" — was REJECTED because it would undo plan 15's split/standardization. This plan makes no SUBSTANTIVE agent-charter change; it wires the existing roster into the per-task loop. (Plan 15 is now FULLY SHIPPED — `720253f`, 2026-06-07. It unified the severity scale + verdict TOKENS but left the verdict LINE FORMAT heterogeneous; because plan 15 is closed, the lone format-normalization edit moves into this plan's Phase 3 sub-track A — the one permitted agent-file edit, markdown level only. See D8.)

## Scope and non-scope

This plan is CONSUMER wiring of plan-15's reviewer roster into `/implement`'s per-task loop, plus a per-task test gate — plus ONE narrow verdict-line-format normalization of two reviewer files (the D8 carve-out; see below). It edits:

- the `/implement` command spec (`src/commands/implement/main.md` PHASE 5/6/7) and its references (`src/commands/implement/references/{review-loop.md,agent-brief.md}`);
- the `_implement` helper subpackage (a NEW `_cmds_review_panel.py` module + a PHASE 5 test-execution extension to `_cmds_verify.py` + `_cli.py` registration);
- the verdict LINE of two agent sources (`src/agents/security-reviewer.md` + `src/agents/performance-analyst.md`) — markdown level only, normalized to `### Verdict:` in Phase 3 sub-track A (the D8 carve-out; no substantive charter change);
- the `/configure` config subsystem (`_configure/_schema.py`, a set-verb, `_configure/_validators.py`, the `## Packages` render) — for the new `test_commands` field (D11);
- docs (`src/CLAUDE.md`, the repo-root `CLAUDE.md` active-plans list, `CHANGELOG.md`).

It does NOT change:

- any SUBSTANTIVE `src/agents/*.md` charter — role, boundaries, checklist, tools grant, severity scale, behavior (D8 — plan 15 owns the roster). The ONLY agent-file edit is the verdict-line markdown-level normalization above;
- the forcing-functions gate (`run-forcing-functions-gate` / `_cmds_gate.py`) — it stays exactly where it is, after the PHASE 6 loop;
- the helper-owned review-loop cap (`REVIEW_LOOP_CAP = 3`, D7);
- feature-level `/review` / `/verify` — they keep their specialist panel for full-solution depth; this plan only adds per-task coverage.

The four reviewers wired into the panel (canonical names from the plan-15 roster): `code-reviewer`, `qa-reviewer`, `security-reviewer`, `performance-analyst`. All four are pure read-only reviewers in plan 15's four-family split.

## Hard precondition

**Plan 15 (`15-AGENT-STANDARDIZATION-PLAN.md`) is FULLY landed — SHIPPED `720253f` (2026-06-07), all phases 0–5 — so this precondition is SATISFIED.** This plan depends on plan-15's standardized read-only reviewer roster (all four panel reviewers tools-locked to read-only, on the unified `Critical/High/Medium/Info` severity scale, single-responsibility); that dependency is now met.

Phase 0 of this plan re-confirms that shipped state before any edit (a re-confirm of a satisfied precondition, NOT a wait-gate).

## Current state (verified this session — treat as settled)

- **PHASE 5 runs type-check + lint + build, NO tests, with a self-repair cap of 3.** `src/devforge/lib/_implement/_cmds_verify.py` runs each touched file's package `type_check_command` + `lint_command` (longest-path-prefix match against `PACKAGE_STACKS`) plus `build_command` once per task; `"N/A"` commands are silently skipped; the self-repair counter is helper-owned at `SELF_REPAIR_CAP = 3` (`_cmds_verify.py` module docstring lines 34–43). It loads `PACKAGE_STACKS + TYPE_CHECK_COMMANDS + LINT_COMMANDS + BUILD_COMMANDS` only — there is NO test command anywhere in its load set.
- **PHASE 6 runs a single `code-reviewer` loop, then the forcing-functions gate.** `src/commands/implement/main.md:176` (`## PHASE 6: Autonomous review loop`) invokes the `code-reviewer` agent and parses its verdict via the helper verb `review-loop-step` (`main.md:186`), implemented in `src/devforge/lib/_implement/_cmds_review_loop.py`. That parser recognizes ONLY code-reviewer's verdict vocabulary (`### Verdict: APPROVE → clean=true`; `REQUEST CHANGES` / `BLOCK → clean=false`; the unfilled three-token template → parse error exit 2 — module docstring lines 9–17); the cap is `REVIEW_LOOP_CAP = 3` (`_cmds_review_loop.py:47`). After the loop converges, PHASE 6 runs the forcing-functions gate `run-forcing-functions-gate` (`main.md:198`, helper `src/devforge/lib/_implement/_cmds_gate.py`).
- **PHASE 7 is the human hard gate (`main.md:209`).** Stage A (`main.md:213`) surfaces recorded judgment decision items one at a time; Stage B (`main.md:231`) shows the diff and asks `["approve", "repair", "skip", "stop"]` (`main.md:238`). The cap-escalation `could-not-converge` Stage A item currently offers `["accept anyway", "send back with direction", "skip", "stop"]` (`main.md:223–227`, mirrored in `src/commands/implement/references/review-loop.md:44`).
- **The 4 panel reviewers are standardized, read-only, tools-locked, on unified severity, but carry DISTINCT verdict vocabularies AND (as plan 15 shipped them) DISTINCT markdown structures for the verdict line** (verified against the source files this session — do not read the four lines as a parallel-shaped list). Phase 3 sub-track A of THIS plan normalizes the two odd-shaped lines to `### Verdict:` headings, after which all four share one structure (see the Motivation sub-bullet below):
  - `code-reviewer` (`src/agents/code-reviewer.md:70`): `### Verdict: APPROVE / REQUEST CHANGES / BLOCK` — clean = `APPROVE`. Structure: an **`### Verdict:` h3 heading**.
  - `qa-reviewer` (`src/agents/qa-reviewer.md:47`): `### Verdict: ADEQUATE / GAPS FOUND` — clean = `ADEQUATE`. Structure: an **`### Verdict:` h3 heading** (same shape as code-reviewer).
  - `security-reviewer` (`src/agents/security-reviewer.md:60`): `- Verdict: PASS / FAIL` — clean = `PASS`. Structure: a **`- Verdict:` bullet-list item** (NOT an `###` heading), inside the agent's `## Security Review` output code-block template.
  - `performance-analyst` (`src/agents/performance-analyst.md:41`): `Verdict: MEETS TARGETS / BOTTLENECKS FOUND` — clean = `MEETS TARGETS`. Structure: a **bare `Verdict:` plain-text line** (no `###`, no bullet), inside the agent's output code-block template.
  - Motivation for Phase 3 sub-track A: the two heading-shaped verdicts (code-reviewer, qa-reviewer) and the two non-heading verdicts (security-reviewer bullet, performance-analyst bare text) are NOT the same markdown shape. The single-reviewer parser (`_cmds_review_loop.py`) anchors on `^###\s*verdict\s*:` and finds ONLY the two heading-shaped verdicts. Rather than build a multi-FORMAT parser, this plan normalizes the two odd-shaped lines: Phase 3 sub-track A edits `security-reviewer.md` and `performance-analyst.md` so each emits an `### Verdict:` h3 heading too. After sub-track A all four reviewers carry the SAME `### Verdict:` shape, so sub-track B's parser matches ONE structure (the existing `^###\s*verdict\s*:` anchor). The remaining per-reviewer difference is VOCABULARY (distinct clean tokens), not FORMAT — see Phase 3.
- **The config schema carries `build/type_check/lint` commands ONLY — there is NO test command field.** Primary command arrays `build_commands` / `type_check_commands` / `lint_commands` are at `src/devforge/lib/_configure/_schema.py:44–46`; the per-package `_PACKAGE_STACK_FIELDS` record carries `build_command` / `type_check_command` / `lint_command` at `_schema.py:83–91`. No `test_commands` / `test_command` field exists. `_configure/_validators.py` (the resolvability probe, lines 345–400) probes exactly those three primary arrays + the three per-package fields — no test field.
- **`_implement` helper module layout** (verified via glob this session): `_cli.py` (arg registration/dispatch), `_cmds_verify.py`, `_cmds_review_loop.py`, `_cmds_gate.py`, `_state.py`, plus `_cmds_capture.py`, `_cmds_commit.py`, `_cmds_complete.py`, `_cmds_preflight.py`, `_cmds_resolve.py`, `_cmds_session.py`, `_handoff_reader.py`, `_wip.py`, `_workspace.py`. Tests live in `tests/lib/_implement/test_*.py`, one per module.
- **Plan 15 status**: FULLY SHIPPED — all phases 0–5 landed (`720253f`, 2026-06-07; Phase 0 + Phase 1 had landed earlier at `348561b`, `fcc4947`). The reviewer roster is final: 17 emitted agents; the four panel reviewers standardized read-only + tools-locked + on the unified severity scale; the consumer rewire complete. Plan 15 unified the severity scale + verdict TOKENS but did NOT unify the verdict LINE FORMAT (that unification moves into THIS plan's Phase 3 sub-track A — see D8). The four reviewer source files carry their final read-only + tools-locked + unified-severity form (verified this session via the verdict-line greps above).

## Locked decisions

### D1 — Full panel from the start

Per-task PHASE 6 runs all four reviewers — `code-reviewer` + `qa-reviewer` + `security-reviewer` + `performance-analyst` — from day one, not staged. (User-chosen.) The panel is wired complete in Phase 4; there is no incremental rollout of individual reviewers.

### D2 — Separate plan, sequenced after plan 15

This is its own plan file, not a section of plan 15. Plan 15 DONE is the hard precondition (see `## Hard precondition`). (User-chosen.) Rationale: plan 15 owns the roster + the `_implement` consumer-rewire audit; folding the net-new panel into plan 15 would entangle a roster-standardization plan with a consumer-feature plan.

### D3 — Test split (execution is mechanical; adequacy is judgment)

The test dimension splits in two:

- **(a) Test EXECUTION** (run the tests; they must pass) is MECHANICAL → it belongs in PHASE 5's scope-aware verify gate, driven by a new per-package `test_command` config field (added in Phase 1, consumed in Phase 2).
- **(b) Test ADEQUACY** (coverage gaps, untested ACs, weak assertions) is JUDGMENT → it is the `qa-reviewer`'s job in the PHASE 6 panel.

Do NOT put test-running inside any review agent. Reviewers are read-only (plan-15 tools-lock); running tests is a verify-gate concern, not a reviewer concern.

### D4 — All findings fixed before the human hard gate

Stage B (the `approve` gate) is reachable ONLY when the panel verdict is fully clean — every reviewer returns its clean verdict, zero outstanding findings. Unresolved reviewer findings must NEVER reach `approve`.

Concretely: the `accept anyway` option is REMOVED from the cap-escalation (`could-not-converge`) Stage A item (Phase 5). At the cap the human gets `["send back with direction", "skip", "stop"]` only — `send back with direction` relaunches the loop under human control (it does not ship an open finding); `skip` takes the Stage B skip path (the task is not approved); `stop` halts the loop. `accept anyway` is an escape hatch that would let an unfixed finding land — forbidden by the repo zero-escape-hatch policy.

NOTE the distinction: a JUDGMENT decision item (the loop resolved a finding one way; the human confirms the SHAPE at Stage A) is NOT an open finding — the finding IS fixed, the human only picks the shape; those still surface to Stage A exactly as today (`main.md:213–221`). Only genuinely UNRESOLVED findings are blocked from the gate.

### D5 — Read-only panel ⇒ no write-collisions

Because plan 15 tools-locks all 4 reviewers to read-only (no `Edit`/`Write`/`Agent`), they cannot modify the tree, so they cannot collide ("step on each other's legs"). The ONLY writer in PHASE 6 is the single implementing agent during a repair leg. A "conflict" therefore means two reviewers proposing INCOMPATIBLE changes to the same code region — a findings-level contradiction (resolved per D10), never a write race.

### D6 — Merge by unified severity; panel-clean = ALL-clean

Findings from all 4 reviewers merge on the shared `Critical/High/Medium/Info` scale (anchored to `_audit/findings_schema.py` `SEVERITY_ENUM`, the same enum plan 15 anchors the reviewers' severity vocab to). That findings merge is the ORCHESTRATOR's semantic work in Phase 4 (it reads the 4 reviewers' returned markdown), NOT the helper's — the `merge-review-panel` helper does only the deterministic verdict aggregation that gates the loop. The panel is "clean" for loop-exit purposes IFF EVERY reviewer returns its own clean verdict (the per-vocab mapping in `## Current state`: code-reviewer `APPROVE` / qa-reviewer `ADEQUATE` / security-reviewer `PASS` / performance-analyst `MEETS TARGETS`); the helper emits that all-clean signal as its `clean` field. One dirty reviewer keeps the loop going.

### D7 — Reuse the helper-owned ≤3 cap

Keep `REVIEW_LOOP_CAP = 3`, helper-owned; the orchestrator cannot extend it. The panel-merge helper (Phase 3) IMPORTS this SAME constant from `_cmds_review_loop.py` as its single source of truth (it computes `escalate` from it) so the panel loop and the legacy single-reviewer loop cap identically; `_cmds_review_loop.py` is otherwise untouched.

### D8 — No agent CHARTER changes (one narrow verdict-line-format carve-out)

This plan makes NO SUBSTANTIVE charter change to any `src/agents/*.md` file — every reviewer's role, boundaries, checklist, tools grant, severity scale, and behavior stay exactly as plan 15 shipped them. It is pure consumer wiring of the existing plan-15 roster; any role-name or charter concern is plan 15's responsibility (see `## Hard precondition`).

The ONE permitted agent-file edit is the narrow verdict-LINE-format normalization in Phase 3 sub-track A: `security-reviewer.md` and `performance-analyst.md` change their verdict line to an `### Verdict:` h3 heading (matching code-reviewer/qa-reviewer). That edit changes ONLY the markdown level of the verdict line — not the tokens, not the severity scale, not the role, checklist, or boundaries — so no reviewer's behavior changes. This carve-out exists because plan 15 is SHIPPED (closed; cannot be extended), so the verdict-line unification it left undone moves into this plan (see Phase 3 sub-track A). Outside that one line in those two files, this plan touches no agent source.

### D9 — Full-panel re-review each round (no delta-scoping in v1)

On each repair round, re-run the FULL panel over all `touched_files` (not just the files the repair changed). This is the simplest, zero-hole choice — it cannot miss a cross-file regression introduced by a repair. Delta-scoped intermediate re-review is noted as a DEFERRED future optimization, explicitly out of scope for v1 (see `## Out of scope`). The cost is bounded: reviewers are read-only + dispatched in parallel, most rounds converge in one, and atomic tasks keep `touched_files` small.

### D10 — Severity-aware conflict escalation

Only INCOMPATIBLE findings of COMPARABLE severity escalate to Stage A as a conflict decision (the human breaks the tie; the loop then applies the choice and re-reviews to clean). A low-severity finding contradicting a higher-severity one resolves MECHANICALLY by severity order (higher severity wins) — no human needed. The ORCHESTRATOR identifies these conflicts in Phase 4 (it reads the 4 reviewers' returned markdown and applies this comparable-severity rule) — conflict detection is semantic and is NOT the `merge-review-panel` helper's job; the helper supplies only the deterministic clean/escalate gate.

### D11 — Test-command config: full split

The test-command config takes the FULL SPLIT — both the mechanical test-execution half AND the judgment adequacy half ship. (User-chosen.) The mechanical test-execution half (D3a) requires a new `test_commands` primary array + per-package `test_command` field in `_configure/_schema.py`, captured by `/configure` (a set-verb + any wizard render), validated by a `_validators.py` resolvability probe, rendered into `project-config.json` + the `## Packages` CLAUDE.md doc, and run by PHASE 5. That pulls the `/configure` subsystem into scope (Phase 1 builds the field; Phase 2 runs it). The full split gives both mechanical test-execution (PHASE 5) and judgment adequacy (qa-reviewer in PHASE 6).

The adequacy-only alternative — drop the config field, let `qa-reviewer` assess tests (it can read tests and note when they are absent or failing), and defer mechanical test-execution to a follow-on — was considered and DECLINED in favour of running tests as a hard gate. Phases 1 and 2 are written against the full split.

## Execution discipline (applies to every phase)

- Every Python helper change goes through the `python-engineer` → `python-reviewer` loop, with a test written + actually run in the SAME turn (repo test-immediately-after-write rule). Parsers must be tested against REAL producer output shapes — round-trip the actual reviewer markdown verdict lines. After Phase 3 sub-track A all four reviewers emit the uniform `### Verdict: <token>` shape, so sub-track B's parser tests round-trip that one line shape with the four distinct tokens (`### Verdict: APPROVE`, `### Verdict: ADEQUATE / GAPS FOUND`, `### Verdict: PASS / FAIL`, `### Verdict: MEETS TARGETS / BOTTLENECKS FOUND`) — NOT the old `- Verdict:` bullet / bare `Verdict:` forms (those no longer exist) and NOT hand-faked fixtures.
- Every command/spec/agent markdown edit (`src/commands/implement/main.md`, its `references/*.md`, `src/CLAUDE.md`, the repo-root `CLAUDE.md`) goes through `instruction-author` → `instruction-reviewer` (route-spec-edits-through-agent-flow).
- For any Claude-Code-integration concern — specifically the PHASE 6 PARALLEL multi-subagent dispatch (firing 4 reviewer Task calls in one turn and consuming all four returns) — verify current conventions via the `claude-code-guide` agent BEFORE writing the spec. Confidence is not verification.
- Each phase leaves the system buildable and tests green.
- This plan lives at repo root and is committed alongside the work it drives.

## Phase 0 — Precondition re-confirm + grounding (no edits)

Re-confirm the (already-satisfied) hard precondition and the verified `## Current state` facts before any edit begins. Plan 15 SHIPPED `720253f` (2026-06-07); this phase re-confirms that shipped state, it is NOT a wait-gate.

- Re-confirm plan 15 is landed: 17 emitted agents; `qa-reviewer` / `security-reviewer` / `performance-analyst` standardized read-only + tools-locked; the consumer rewire complete (no `qa-engineer` reviewer-role remaining downstream). Check `git log --oneline` on `develop-2.0-init` for `720253f`.
- Re-confirm the Current-state facts still hold: PHASE 5 has no test command; PHASE 6 runs a single `code-reviewer`; `_schema.py` has no `test_command`; the 4 reviewer verdict vocabularies match.
- Zero edits in this phase.

### Verify

```bash
# Plan-15 roster landed: the 4 panel reviewers exist read-only + tools-locked:
grep -l "^tools:" src/agents/{code-reviewer,qa-reviewer,security-reviewer,performance-analyst}.md  # expect: all 4
grep -nE "tools:.*(Edit|Write|Agent)" src/agents/{code-reviewer,qa-reviewer,security-reviewer,performance-analyst}.md  # expect: 0
# The 4 verdict vocabularies present (panel-merge parser anchors to these):
grep -n "APPROVE / REQUEST CHANGES / BLOCK" src/agents/code-reviewer.md        # expect: 1
grep -n "ADEQUATE / GAPS FOUND"             src/agents/qa-reviewer.md          # expect: present
grep -n "PASS / FAIL"                       src/agents/security-reviewer.md    # expect: present
grep -n "MEETS TARGETS / BOTTLENECKS FOUND" src/agents/performance-analyst.md  # expect: present
# Current state: no test command in PHASE 5's config or schema:
grep -n "test_command" src/devforge/lib/_configure/_schema.py                  # expect: 0
grep -n "test_command\|test_commands" src/devforge/lib/_implement/_cmds_verify.py  # expect: 0
# Current state: PHASE 6 single code-reviewer loop + forcing-functions gate:
grep -n "code-reviewer\|review-loop-step\|run-forcing-functions-gate" src/commands/implement/main.md
# Plan-15 SHIPPED 720253f (17 emitted agents, consumer rewire complete):
git log --oneline develop-2.0-init | grep -n 720253f   # expect: present
```

DoD: precondition re-confirmed satisfied (plan 15 SHIPPED `720253f` — 17 emitted agents, 4 panel reviewers read-only + tools-locked, consumer rewire complete); the Current-state facts re-confirmed (no test field in PHASE 5/schema; single code-reviewer in PHASE 6; the 4 verdict vocabs match); zero edits in this phase.

## Phase 1 — Test-command config plumbing

Add the test-command config field so PHASE 5 can run tests (Phase 2 consumes it). This phase is in scope per D11 (full split); Phase 2 consumes its `test_command` field to run tests in the PHASE 5 scope-aware gate.

- Add `test_commands` (primary `string_array`) to `FIELD_SCHEMA` and a per-package `test_command` to `_PACKAGE_STACK_FIELDS` in `src/devforge/lib/_configure/_schema.py`, clustered with the existing `build_commands` / `type_check_commands` / `lint_commands` (primary, `:44–46`) and `build_command` / `type_check_command` / `lint_command` (per-package record, `:83–91`).
- Add a `/configure` set-verb mirroring the existing build/type_check/lint command setters (read the existing `_configure` set-verb for build commands and follow its shape — helper-owns-shape: the setter owns validation + atomic write; the LLM composes values).
- Add a resolvability probe in `src/devforge/lib/_configure/_validators.py` mirroring the build/type_check/lint probes (the `:345–400` block) — probe `test_commands[0]` (primary) + each `package_stacks` record's `test_command`.
- Render the field into `project-config.json`, and extend the `PACKAGE_STACKS` render logic (the configure-helper render path that populates the `{{PACKAGE_STACKS_SECTION}}` placeholder) so each rendered per-package record includes `test_command`. This propagates to generated installs' `CLAUDE.md`; do NOT hand-edit `src/CLAUDE.md`'s `## Packages` section directly.
- Helper edits via `python-engineer` → `python-reviewer` (+ a test in the same turn); any `/configure` command-markdown edit via `instruction-author` → `instruction-reviewer`.

### Verify

```bash
# New field in schema (primary array + per-package record field):
grep -n "test_commands" src/devforge/lib/_configure/_schema.py   # expect: in FIELD_SCHEMA
grep -n "test_command" src/devforge/lib/_configure/_schema.py    # expect: in _PACKAGE_STACK_FIELDS
# Resolvability probe added:
grep -n "test_command\|test_commands" src/devforge/lib/_configure/_validators.py  # expect: present in the probe block
# Set-verb registered + a round-trip test asserts it persists:
grep -rn "test_command" src/devforge/lib/_configure/   # expect: set-verb + render present
python -m pytest tests/lib/_configure/   # expect: green, incl. the new set-verb round-trip test
```

DoD: config carries `test_commands` (primary) + per-package `test_command`; the set-verb round-trips through the config file; the field is resolvability-probed and rendered into `project-config.json` + the `## Packages` doc; helper tests written + run + green; markdown edits through the author→reviewer loop.

## Phase 2 — PHASE 5 test execution

Extend the scope-aware verify gate to run tests (D3a). Depends on Phase 1 (the `test_command` config field).

- Extend `src/devforge/lib/_implement/_cmds_verify.py` to run each touched file's package `test_command` via the same longest-path-prefix match it uses for `type_check_command` / `lint_command`, skipping `"N/A"` silently, folding test execution into the EXISTING self-repair loop and its `SELF_REPAIR_CAP = 3` (a failing test is a verify failure handled by the same self-repair counter — no new cap).
- Update `src/commands/implement/main.md` PHASE 5 + the `src/CLAUDE.md` "Verification (explicit, scope-aware …)" section to document test execution in the scope-aware gate.
- Helper via `python-engineer` → `python-reviewer` (+ a test asserting verify runs the `test_command` and fails the gate on a failing test, written + run in the same turn); markdown via `instruction-author` → `instruction-reviewer`.

### Verify

```bash
# Verify runs the per-package test_command + fails the gate on a failing test:
grep -n "test_command" src/devforge/lib/_implement/_cmds_verify.py   # expect: loaded + matched
python -m pytest tests/lib/_implement/test_cmds_verify.py            # expect: green, incl. the new failing-test-blocks-gate case
# main.md PHASE 5 + src/CLAUDE.md Verification section document test execution:
grep -n "test" src/commands/implement/main.md                       # expect: PHASE 5 mentions test execution
grep -n "test" src/CLAUDE.md                                        # expect: Verification section mentions tests
```

DoD: PHASE 5 runs each touched package's `test_command` in the scope-aware gate; a failing test blocks the gate via the existing self-repair loop; `_cmds_verify.py` test green incl. the failing-test case; main.md PHASE 5 + the `src/CLAUDE.md` Verification section document test execution.

## Phase 3 — Verdict-line normalization + panel-merge helper (two ordered sub-tracks)

Build the helper that parses all 4 reviewer verdicts and merges their findings — but first normalize the two odd-shaped verdict lines so the parser has ONE structure to match. Split into two ordered sub-tracks (mirroring plan-15's Phase-4 sub-track pattern): **sub-track A lands BEFORE sub-track B**, because A removes the multi-FORMAT problem that B's parser would otherwise have to solve.

### Sub-track A — Reviewer verdict-line normalization (markdown loop; lands first)

Normalize the two non-heading verdict lines to the `### Verdict:` h3 heading used by code-reviewer/qa-reviewer. Via `instruction-author` → `instruction-reviewer`:

- Edit `src/agents/security-reviewer.md` — the `- Verdict: PASS / FAIL` line in its output code-block template (currently line 60; line numbers are pre-edit — locate by content) → `### Verdict: PASS / FAIL`.
- Edit `src/agents/performance-analyst.md` — the bare `Verdict: MEETS TARGETS / BOTTLENECKS FOUND` line in its output code-block template (currently line 41; pre-edit — locate by content) → `### Verdict: MEETS TARGETS / BOTTLENECKS FOUND`.
- Change ONLY the verdict line's markdown level. Leave the tokens, severity scale, role, checklist, and boundaries untouched (D8 carve-out — this is the one permitted agent-file edit).
- Regenerate the emitted agents (`scripts/generate-agents.py --src src/agents --target <scratch>`) and run `tests/scripts/test_generate_agents.py`.
- Cross-ref sweep (verified clean this session — state it as the expected result): the ONLY code that parses a reviewer verdict LINE is `src/devforge/lib/_implement/_cmds_review_loop.py` (its `_VERDICT_RE` `^###\s*verdict\s*:` anchor, code-reviewer only); `/audit` and `/review` reference "verdict" only in prose/docstrings (e.g. `_audit/_report.py`, `_audit/_inline.py`) and consume findings STRUCTURALLY, not by parsing a verdict line. So normalizing these two lines breaks no existing consumer.

### Sub-track B — Multi-VOCAB panel-merge helper (python loop; lands after A)

Build the panel-merge helper. Via `python-engineer` → `python-reviewer`:

- Add a NEW helper module `src/devforge/lib/_implement/_cmds_review_panel.py` exposing a `merge-review-panel` verb. **Decision (stated, not deferred): a NEW module, NOT an extension of `_cmds_review_loop.py`** — so the tested single-reviewer parser stays intact. The new module IMPORTS `_VERDICT_RE` (the `^###\s*verdict\s*:` anchor) and `REVIEW_LOOP_CAP` from `_cmds_review_loop.py` as the single source of truth for the verdict-line shape and the cap; it adds its OWN per-reviewer TOKEN → clean vocab table (the 4-reviewer mapping, which `_cmds_review_loop.py` does not carry — that module only knows code-reviewer's vocab). `_cmds_review_loop.py` is left untouched.
- The verb accepts one reviewer-output file PER reviewer keyed by agent name (e.g. repeated `--reviewer <agent-name>:<path>`, in CLI order), parses each with the agent-appropriate verdict vocab (the `## Current state` mapping: code-reviewer `APPROVE` / qa-reviewer `ADEQUATE` / security-reviewer `PASS` / performance-analyst `MEETS TARGETS` = clean), and emits the VERDICT-AGGREGATION JSON `{clean, escalate, iteration, per_reviewer:[{agent, verdict, clean}, ...]}` (`per_reviewer` in CLI order).
  - `clean` = all reviewers clean (D6).
  - `escalate` = iteration `>= REVIEW_LOOP_CAP` (the cap constant imported from `_cmds_review_loop.py` — single source of truth per D7).
  - `iteration` = the integer iteration the orchestrator passed in.
  - `per_reviewer` = one `{agent, verdict, clean}` record per reviewer, in CLI order.
- **The helper does the DETERMINISTIC verdict aggregation ONLY — it does NOT parse, merge, or conflict-detect findings.** Findings synthesis (collapsing all 4 reviewers' findings into the ONE repair brief) and conflict identification (deciding which findings genuinely contradict) move to the ORCHESTRATOR in Phase 4. Rationale: conflict detection is inherently SEMANTIC — whether two findings contradict cannot be decided mechanically from 4 heterogeneous reviewer markdown formats — and mechanically merging findings by `file:line` across those formats is fragile and duplicates the read the orchestrator already performs to build the repair brief. The deterministic value the helper adds is the verdict aggregation, which gates the loop (`clean`/`escalate`).
- **The verdict-line regex is ONE pattern** — `_VERDICT_RE` (`^###\s*verdict\s*:`), imported from `_cmds_review_loop.py` as the single source of truth — valid because sub-track A normalized all four verdict lines to that `### Verdict:` shape. **Precision: sub-track A removed the multi-FORMAT problem, NOT the multi-VOCAB mapping.** The parser still needs a per-reviewer TOKEN → clean map keyed by agent name (code-reviewer `APPROVE`, qa-reviewer `ADEQUATE`, security-reviewer `PASS`, performance-analyst `MEETS TARGETS` = clean); the one imported regex locates the verdict line, the keyed vocab table classifies its token. On a parse error the verb exits 2 with stderr naming the failing reviewer (no JSON). Tests round-trip the POST-normalization `### Verdict:` line for all four reviewers with their distinct tokens (NOT the old `- Verdict:` bullet or bare `Verdict:` shapes — those no longer exist after sub-track A).
- Register the verb in `src/devforge/lib/_implement/_cli.py` alongside the existing verb registrations.
- Tests in `tests/lib/_implement/test_cmds_review_panel.py` round-tripping each reviewer's real post-normalization markdown verdict line, written + run in the same turn. The single-reviewer parser (`_cmds_review_loop.py`) is UNTOUCHED.

### Verify

```bash
# Sub-track A — the two odd-shaped verdict lines normalized to ### headings:
grep -n "^### Verdict:" src/agents/security-reviewer.md      # expect: present (was '- Verdict:')
grep -n "^### Verdict:" src/agents/performance-analyst.md    # expect: present (was bare 'Verdict:')
grep -n "^- Verdict:" src/agents/security-reviewer.md        # expect: 0 (bullet gone)
# Sub-track A — all four reviewers now share the ### Verdict: shape:
grep -ln "^### Verdict:" src/agents/{code-reviewer,qa-reviewer,security-reviewer,performance-analyst}.md  # expect: all 4
# Sub-track A — regenerate + emitter test green:
python -m pytest tests/scripts/test_generate_agents.py       # expect: green
# Sub-track A — the only verdict-LINE parser is _cmds_review_loop.py (cross-ref sweep):
grep -rni "verdict" src/devforge/lib/   # read: only _cmds_review_loop.py parses a verdict LINE (+ the new _cmds_review_panel.py after sub-track B); /audit (_audit/_report.py, _audit/_inline.py) + /review mention 'verdict' in prose/docstrings only, not as a parsed line
# Sub-track B — new module + verb registered:
ls src/devforge/lib/_implement/_cmds_review_panel.py   # expect: present
grep -n "merge-review-panel" src/devforge/lib/_implement/_cli.py   # expect: registered
# Sub-track B — single-reviewer parser untouched (cap still owned there):
grep -n "REVIEW_LOOP_CAP" src/devforge/lib/_implement/_cmds_review_loop.py   # expect: 47 (unchanged)
# Sub-track B — new test module parses all 4 tokens against the uniform ### Verdict: shape:
python -m pytest tests/lib/_implement/test_cmds_review_panel.py   # expect: green
python -m pytest tests/lib/_implement/test_cmds_review_loop.py    # expect: green (single-reviewer parser intact)
```

DoD (sub-track A BEFORE sub-track B):
- **Sub-track A:** `security-reviewer.md` and `performance-analyst.md` each emit an `### Verdict:` h3 heading (markdown level changed only — tokens/severity/role/checklist/boundaries untouched); the emitted agents are regenerated and `tests/scripts/test_generate_agents.py` is green; the cross-ref sweep confirms the only verdict-LINE parser is `_cmds_review_loop.py` (code-reviewer) and that `/audit` + `/review` do not parse these verdict lines.
- **Sub-track B:** `merge-review-panel` parses the verdict line with the ONE imported regex `_VERDICT_RE` (`^###\s*verdict\s*:`, single source of truth from `_cmds_review_loop.py`) and classifies the token via the per-reviewer vocab map (code-reviewer `APPROVE` / qa-reviewer `ADEQUATE` / security-reviewer `PASS` / performance-analyst `MEETS TARGETS` = clean), emits the verdict-aggregation JSON `{clean (all-clean per D6), escalate (the imported `REVIEW_LOOP_CAP` per D7), iteration, per_reviewer:[{agent, verdict, clean}, ...]}` (CLI order), and exits 2 + stderr (no JSON) naming the failing reviewer on a parse error; it does NOT parse, merge, or conflict-detect findings (that is the orchestrator's job in Phase 4 — semantic synthesis + conflict-ID); the new test module round-trips the post-normalization `### Verdict:` line for all four reviewers with their distinct tokens (NOT the old bullet/bare shapes) and is green; the single-reviewer `_cmds_review_loop.py` parser is untouched (its `_VERDICT_RE` + `REVIEW_LOOP_CAP` are the imported single source of truth) and still green.

## Phase 4 — PHASE 6 panel rewiring (main.md + references)

Rewrite PHASE 6 to fan out the full panel. Depends on Phase 3 (`merge-review-panel`). **Verify Claude-Code parallel-subagent dispatch via the `claude-code-guide` agent BEFORE writing** (the 4-Task-calls-in-one-turn dispatch is a Claude-Code-integration concern).

- Rewrite `src/commands/implement/main.md` PHASE 6: fan out the 4 reviewers IN PARALLEL via the Task tool (one turn, four Task calls) over the frozen `touched_files`; write each return to a scratch file; call `merge-review-panel` with one `--reviewer <agent>:<path>` per reviewer to get the `{clean, escalate, iteration, per_reviewer}` verdict-aggregation signal; branch on that aggregate:
  - **clean** ⇒ proceed to the forcing-functions gate (`run-forcing-functions-gate`, unchanged) then PHASE 7.
  - **not-clean + not-escalate** ⇒ the ORCHESTRATOR reads the 4 reviewers' returned markdown directly and (a) SYNTHESIZES all of their findings into the ONE implementing-agent repair brief, and (b) IDENTIFIES genuine conflicts — incompatible findings of COMPARABLE severity on the same region (D10) — recording them (plus judgment calls; the existing mechanical-vs-judgment classification still applies) as Stage A decision items; then ONE implementing-agent repair leg addresses all non-conflicting synthesized findings; then re-run the FULL panel (D9) at iteration `N + 1`. (The helper provides the clean/escalate gate; the LLM provides the semantic findings-merge + conflict-ID — findings parsing/merge/conflict-detect is NOT in the helper. See Phase 3 sub-track B.)
  - **escalate** ⇒ record `could-not-converge` and exit to PHASE 7.
- Keep the forcing-functions gate EXACTLY where it is (after the loop) — do not move or change it.
- Update `src/commands/implement/references/review-loop.md` to describe the PANEL loop: the per-vocab → clean mapping (all 4), the all-clean rule (D6), the orchestrator-side findings synthesis + conflict-ID (the helper returns only the verdict-aggregation signal `{clean, escalate, per_reviewer}`; the LLM merges findings + identifies conflicts), the conflict decision-item shape (D10), and the full-panel-each-round rule (D9).
- Update `src/commands/implement/references/agent-brief.md` so the PHASE 6 re-dispatch brief carries the orchestrator-SYNTHESIZED panel findings (all 4 reviewers, not just code-reviewer's) into the repair leg.
- All via `instruction-author` → `instruction-reviewer`.

### Verify

```bash
# PHASE 6 names all 4 reviewers + the panel-merge verb:
grep -n "code-reviewer" src/commands/implement/main.md       # expect: present in PHASE 6
grep -n "qa-reviewer\|security-reviewer\|performance-analyst" src/commands/implement/main.md  # expect: all 3 present in PHASE 6
grep -n "merge-review-panel" src/commands/implement/main.md  # expect: present in PHASE 6
# Forcing-functions gate still present + after the loop (unchanged position):
grep -n "run-forcing-functions-gate" src/commands/implement/main.md  # expect: still present, after PHASE 6 loop
# review-loop.md documents the 4 vocabs + full-panel-each-round:
grep -nE "ADEQUATE|PASS|MEETS TARGETS|APPROVE" src/commands/implement/references/review-loop.md  # expect: all 4 verdict vocabs documented
```

DoD: PHASE 6 fans out 4 read-only reviewers in parallel, calls `merge-review-panel` for the `{clean, escalate, per_reviewer}` verdict-aggregation gate, then the orchestrator synthesizes the 4 reviewers' findings + identifies conflicts (D10) from their returned markdown (the helper does NOT parse/merge/conflict-detect findings — Phase 3 sub-track B), repairs once per round addressing all synthesized non-conflicting findings, re-reviews the full panel each round (D9), and is capped (D7); the forcing-functions gate is unchanged and still after the loop; `review-loop.md` + `agent-brief.md` reconciled to the panel; the rewritten `review-loop.md` panel description must NOT introduce or carry over an `accept anyway` option (Phase 5 removes it from the could-not-converge path; Phase 4 must not re-add it); parallel-dispatch verified via `claude-code-guide` before writing.

## Phase 5 — PHASE 7 all-findings-fixed + conflict decision (main.md + references)

Implement D4 (no open finding reaches `approve`) and D10's human tie-break path.

- Stage B reachable ONLY from a fully-clean panel (D4): document that the `approve` option appears only when the PHASE 6 panel converged clean.
- REMOVE `accept anyway` from the `could-not-converge` Stage A options (`main.md:223–227`): the options become `["send back with direction", "skip", "stop"]` (D4 — `accept anyway` is the forbidden escape hatch).
- Add the conflict decision-item kind (D10): a Stage A tie-break for an incompatible comparable-severity conflict → apply the chosen finding → re-review to clean.
- Update `src/commands/implement/main.md` PHASE 7 Stage A + `src/commands/implement/references/review-loop.md` (the decision-item shapes — both the existing judgment item and the new conflict item; remove the `accept anyway` option from `review-loop.md`'s could-not-converge Stage A options section — line 44 in the pre-Phase-4 state; after Phase 4 has rewritten this file, locate it by content, not line number).
- Via `instruction-author` → `instruction-reviewer`.

### Verify

```bash
# accept anyway removed from main.md + the review-loop reference:
grep -n "accept anyway" src/commands/implement/main.md                        # expect: 0
grep -n "accept anyway" src/commands/implement/references/review-loop.md      # expect: 0
# could-not-converge options are now send back / skip / stop:
grep -n "send back with direction" src/commands/implement/main.md            # expect: present (cap-escalation options)
# conflict decision-item kind present:
grep -niE "conflict" src/commands/implement/main.md src/commands/implement/references/review-loop.md  # expect: the conflict decision item documented
```

DoD: no path reaches `approve` with an open finding (`accept anyway` gone from `main.md` AND `review-loop.md`; cap-escalation options are `send back with direction / skip / stop`); the conflict decision-item kind is handled at Stage A (D10); references consistent; all via the author→reviewer loop.

## Phase 6 — Docs + cross-ref sweep

Reconcile all docs to the new per-task panel + test gate and run the dangling-reference sweep.

- Update the `src/CLAUDE.md` `/implement` description (per-task panel + test gate) and its "Verification (explicit, scope-aware …)" section (test execution + panel).
- Add this plan (17) to the repo-root `CLAUDE.md` active-plans list, and cross-reference it from the `07-EXECUTE-TASK-REDESIGN-PLAN.md` entry (07 owns the `/implement` command; 17 extends its PHASE 5 / 6 / 7).
- Add a `CHANGELOG.md` entry.
- Run a cross-ref sweep: no dangling references; the panel reviewer names EXACTLY match the plan-15 roster (`code-reviewer`, `qa-reviewer`, `security-reviewer`, `performance-analyst`); the forcing-functions gate wiring is untouched; `accept anyway` is removed everywhere it was referenced.
- Via `instruction-author` → `instruction-reviewer`.

### Verify

```bash
# src/CLAUDE.md /implement description + Verification section updated:
grep -n "panel\|qa-reviewer\|security-reviewer\|performance-analyst" src/CLAUDE.md  # expect: panel reviewers named in /implement description
# Plan 17 in the active-plans list + cross-referenced from 07:
grep -n "17-IMPLEMENT-PER-TASK-PANEL-PLAN" CLAUDE.md            # expect: present in active-plans + the 07 entry
# CHANGELOG entry present:
grep -n "per-task" CHANGELOG.md   # expect: the new entry
# Sweep: no stale accept-anyway / single-reviewer-only language survives anywhere:
grep -rn "accept anyway" src/commands/implement/   # expect: 0
grep -rn "single code-reviewer\|only code-reviewer" src/commands/implement/  # expect: 0 (panel language replaced it)
# Panel reviewer names match the plan-15 roster (no non-existent role):
grep -rnoE "qa-engineer|qa-reviewer|security-reviewer|performance-analyst|code-reviewer" src/commands/implement/  # read: only roster names, no qa-engineer reviewer-role
```

DoD: `src/CLAUDE.md` `/implement` description + Verification section reconciled to the panel + test gate; plan 17 in the repo-root active-plans list + cross-referenced from the 07 entry; `CHANGELOG.md` entry added; the cross-ref sweep is clean (no dangling references; panel names match the plan-15 roster; forcing-functions gate untouched; `accept anyway` gone everywhere).

## Phase 7 — testForge20 e2e (USER-DRIVEN HARD GATE)

Run `/implement` on a real task in testForge20 and confirm the panel + test gate + all-findings-fixed behavior end to end:

- the 4-reviewer panel fans out IN PARALLEL (one turn, four Task calls);
- findings merge across reviewers on the unified severity scale;
- the loop drives all findings to zero, OR escalates to Stage A with `send back with direction / skip / stop` (never `accept anyway`);
- the PHASE 5 `test_command` runs and a failing test blocks the gate;
- Stage B (`approve`) is offered ONLY on a fully-clean panel.

This phase is user-driven (requires a live testForge20 install of the post-phase-6 source).

### Verify

```bash
# (User-driven — run against a testForge20 install with the new source emitted.)
# Observe during the /implement run:
#   - PHASE 6 dispatches 4 reviewer Task calls in a single turn (parallel panel).
#   - merge-review-panel JSON shows {clean, escalate, iteration, per_reviewer} for all 4 (verdict aggregation only — no merged_findings/conflicts in the helper output).
#   - The orchestrator synthesizes the 4 reviewers' findings + flags conflicts itself (semantic, not from the helper).
#   - The cap-escalation question offers send back / skip / stop (NO accept anyway).
#   - A deliberately-failing test blocks the PHASE 5 gate.
#   - Stage B 'approve' appears only after a fully-clean panel.
```

DoD: e2e confirms the parallel 4-reviewer panel, cross-reviewer merge, all-findings-fixed loop (no `accept anyway`), the PHASE 5 test gate (failing test blocks), and Stage-B-only-on-clean behavior; user-driven sign-off.

## Out of scope (do NOT plan here)

- **Any SUBSTANTIVE `src/agents/*.md` charter change** (role, boundaries, checklist, tools grant, severity scale, behavior) (D8) — plan 15 owns the roster. The ONE exception is Phase 3 sub-track A's narrow verdict-LINE markdown-level normalization of `security-reviewer.md` + `performance-analyst.md` (the D8 carve-out — see D8); that is the only agent-file edit this plan makes.
- **Delta-scoped intermediate re-review** (D9 defers it) — v1 always re-runs the full panel over all `touched_files`.
- **Feature-level `/review` / `/verify` changes** — they keep their specialist panel for full-solution depth; this plan only adds per-task coverage.

## Context for next session

- This plan widens `/implement`'s PER-TASK review (PHASE 6) from a single `code-reviewer` to a full READ-ONLY PANEL of 4 reviewers (`code-reviewer` + `qa-reviewer` + `security-reviewer` + `performance-analyst`) and adds a per-task test gate (test EXECUTION in PHASE 5, test ADEQUACY in the panel). The motive: in agent-driven dev, a bad pattern set in task 1 propagates by pattern-replication to downstream tasks unless caught per-task; feature-level `/review` is too late.
- **All eleven decisions (D1–D11) are RESOLVED.** Key ones: D1 full panel from day one; D3 test split (execution = mechanical PHASE 5 gate, adequacy = qa-reviewer in PHASE 6); D4 no open finding reaches `approve` (`accept anyway` REMOVED); D5 read-only ⇒ no write-collisions; D6 merge by unified severity, panel-clean = all-clean; D7 reuse the helper-owned `REVIEW_LOOP_CAP = 3`; **D8 NO SUBSTANTIVE charter change — amended with ONE narrow carve-out: Phase 3 sub-track A may edit `security-reviewer.md` + `performance-analyst.md` to change their verdict line's markdown level to `### Verdict:` (tokens/severity/role/behavior untouched)**; D9 full-panel re-review each round; D10 severity-aware conflict escalation; **D11 test-command full split — Phase 1 builds the `test_commands` config field, Phase 2 runs it in the PHASE 5 gate (the adequacy-only alternative DECLINED)**.
- **Hard precondition: plan 15 is FULLY landed — SHIPPED `720253f` (2026-06-07), all phases 0–5 — so the precondition is SATISFIED.** This plan is pure consumer wiring on top of that finished read-only reviewer roster (Phase 0 re-confirms the shipped state, not a wait-gate).
- Verified file:line facts (this session): PHASE 5 runs type-check + lint + build, NO tests, `SELF_REPAIR_CAP = 3` (`_cmds_verify.py` docstring lines 34–43); PHASE 6 single `code-reviewer` via `review-loop-step` (`main.md:176,186`, `_cmds_review_loop.py`, `REVIEW_LOOP_CAP = 3` at `:47`), then `run-forcing-functions-gate` (`main.md:198`); PHASE 7 Stage A `could-not-converge` options `["accept anyway", "send back with direction", "skip", "stop"]` (`main.md:223–227`, `review-loop.md:44`); Stage B options `["approve", "repair", "skip", "stop"]` (`main.md:238`). The 4 verdict vocabs (and their PRE-normalization markdown shapes): code-reviewer `### Verdict: APPROVE/REQUEST CHANGES/BLOCK` h3 heading (`code-reviewer.md:70`), qa-reviewer `### Verdict: ADEQUATE/GAPS FOUND` h3 heading (`qa-reviewer.md:47`), security-reviewer `- Verdict: PASS/FAIL` bullet (`security-reviewer.md:60`), performance-analyst bare `Verdict: MEETS TARGETS/BOTTLENECKS FOUND` text (`performance-analyst.md:41`). **Phase 3 sub-track A of THIS plan normalizes the security-reviewer bullet + performance-analyst bare line to `### Verdict:` headings** — after sub-track A lands, those two `:60` / `:41` shape facts are stale (all four become `### Verdict:` headings; tokens unchanged). Config schema has NO test field — primary arrays at `_schema.py:44–46`, per-package record fields at `_schema.py:83–91`, validators probe at `_validators.py:345–400`. `_implement` modules: `_cli.py`, `_cmds_verify.py`, `_cmds_review_loop.py`, `_cmds_gate.py`, `_state.py` + capture/commit/complete/preflight/resolve/session/handoff_reader/wip/workspace; one test per module under `tests/lib/_implement/`.
- These `main.md` line numbers reflect the PRE-Phase-4 state; after Phase 4 rewrites PHASE 6 (and Phase 5 edits PHASE 7), re-read `main.md` from scratch rather than navigating by these numbers.
- **Phase 3 now has two ordered sub-tracks** (mirroring plan-15's Phase-4 sub-track pattern): **sub-track A (markdown loop, lands FIRST)** normalizes `security-reviewer.md` + `performance-analyst.md` verdict lines to `### Verdict:` headings via `instruction-author` → `instruction-reviewer` (the D8 carve-out; regenerate emitted agents + run `tests/scripts/test_generate_agents.py`); **sub-track B (python loop, lands AFTER A)** builds the verdict-aggregation helper. It is a NEW module `_cmds_review_panel.py` (verb `merge-review-panel`) — NOT an extension of `_cmds_review_loop.py`; the single-reviewer parser stays intact. It IMPORTS `_VERDICT_RE` + `REVIEW_LOOP_CAP` from `_cmds_review_loop.py` as the single source of truth (verdict-line shape + cap) and adds its own per-reviewer TOKEN→clean vocab table. The verb emits the verdict-aggregation JSON `{clean, escalate, iteration, per_reviewer:[{agent, verdict, clean}, ...]}` (CLI order) and exits 2 + stderr (no JSON) naming the failing reviewer on a parse error. **The helper does the DETERMINISTIC verdict aggregation ONLY — it does NOT parse, merge, or conflict-detect findings; findings synthesis + conflict-ID are the orchestrator's SEMANTIC job in Phase 4** (conflict detection cannot be done mechanically from 4 heterogeneous reviewer markdown formats, and finding-merge by `file:line` across them is fragile and duplicates the orchestrator's read). Because sub-track A unified the verdict-line FORMAT, the verdict-line regex is ONE pattern (the imported `_VERDICT_RE`, `^###\s*verdict\s*:`); the per-reviewer TOKEN→clean VOCAB map (keyed by agent name) is still needed — A removed the multi-format problem, not the multi-vocab one.

## When resuming work

1. Re-read this plan in full + `15-AGENT-STANDARDIZATION-PLAN.md` (the hard precondition) + `src/commands/implement/main.md` PHASE 5 / 6 / 7 + the 4 reviewer sources (`code-reviewer.md`, `qa-reviewer.md`, `security-reviewer.md`, `performance-analyst.md`) to re-confirm the verdict vocabularies.
2. Re-confirm plan 15 is landed (Phase 0 verify block — SHIPPED `720253f`) BEFORE any edit; the precondition is already satisfied, so this is a re-confirm, not a wait-gate.
3. Run phases in order (0 → 1 → 2 → 3 → 4 → 5 → 6 → 7). Phase 1 + Phase 2 build the test gate (D11 — full split); **within Phase 3, sub-track A (verdict-line normalization, markdown loop) lands BEFORE sub-track B (panel-merge parser, python loop)**; Phase 4 depends on Phase 3 (`merge-review-panel`); Phase 5 depends on Phase 4; Phase 7 is the user-driven e2e gate.
4. Route every Python helper change through `python-engineer` → `python-reviewer` with a test written + run in the same turn (round-trip the REAL reviewer markdown vocab, not hand-faked fixtures); route every command/spec markdown edit through `instruction-author` → `instruction-reviewer`.
5. Verify the PHASE 6 parallel multi-subagent dispatch (4 Task calls in one turn) via the `claude-code-guide` agent BEFORE writing the Phase 4 spec.
6. Commit alongside the work in repo commit style (lowercase, terse, scope prefix — e.g. `feat(implement): per-task reviewer panel + test gate`).

## Related plans

- `15-AGENT-STANDARDIZATION-PLAN.md` — HARD PRECONDITION (SATISFIED — SHIPPED `720253f`, 2026-06-07, phases 0–5); provides the read-only, tools-locked, unified-severity reviewer roster this plan wires into the per-task loop. Plan 15 unified the severity scale + verdict TOKENS but NOT the verdict LINE FORMAT; because plan 15 is closed, that verdict-line unification moves into THIS plan (Phase 3 sub-track A). This plan makes NO SUBSTANTIVE charter change (D8) beyond that one narrow verdict-line-markdown-level edit; it otherwise consumes plan 15's finished output.
- `07-EXECUTE-TASK-REDESIGN-PLAN.md` — owns the `/implement` command (source spec + `_implement` helper + launcher). This plan EXTENDS its PHASE 5 (adds the test gate), PHASE 6 (single reviewer → full panel), and PHASE 7 (all-findings-fixed; `accept anyway` removed). Keep the two consistent: the forcing-functions gate that 07 wired after the PHASE 6 loop is unchanged here.
- `01-CONSTITUTION-FORCING-FUNCTIONS-PLAN.md` — owns the forcing-functions gate (`run-forcing-functions-gate` / `_cmds_gate.py`) that runs AFTER the PHASE 6 review loop. This plan leaves that gate exactly where it is, unchanged.
