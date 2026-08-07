# 70 — Pipeline Wall-Clock Profiling Plan

**Status:** DRAFT — awaiting Phase 0 maintainer ratification. NOT started, no code.
**Branch:** `develop-2.0-init`
**Date:** 2026-08-05

## Problem

A full pre-implement chain (`/research` → `/specify` → `/plan` → `/breakdown`, plus optional `/grill` / `/spec-check`) takes the maintainer ~2h wall-clock on 2.0 vs "much faster" on 1.x. The maintainer's felt cause is "Python added slowness." **That hypothesis is falsified empirically** (see grounding). We do not currently know where the 2h actually goes — the maintainer's own read is "im not sure." Optimizing blind risks cutting the wrong thing (e.g. dialing back quality gates that aren't the hog).

**This plan does NOT optimize. It measures.** It builds a tool that reads a Claude Code session transcript and reports, per pipeline command, the exact wall-clock split — LLM turn time vs helper (Bash) time vs agent (Task) sub-session time vs human-answer time. Only after the data names the hog do we open a follow-on plan to cut it.

Measure-first is the correct order and matches repo precedent (RTK `discover`, the CBM empirical probes, plan 41's live-`src/` gate): instrument what exists, then act on numbers.

## Empirical grounding (verified 2026-08-05)

Python helpers are NOT the wall-clock cost. Helper cold-start timings (measured 2026-08-05):

```
# python3 -c "pass"                      -> 0.05s   (interpreter baseline)
plan_helper        (cold import+dispatch)-> 0.074s
breakdown_helper                         -> 0.075s
research_helper                          -> 0.099s
specify_helper                           -> 0.112s
spec_check_helper                        -> 0.081s
audit_helper                             -> 0.077s
import z3   (spec-check heaviest dep)    -> 0.367s
```

Even 50 helper calls across a whole pre-implement ≈ 5s. Not 2h. **Python is NOT the cost.** What LOOKS like "python running" is the **Opus LLM turn wrapped around** the ~80ms helper call — the helper returns instantly; the surrounding turn (read output → narrate → compose next args → dispatch) is the cost.

Model tiers (`scripts/lib/install_defaults.py:30`, `src/agents-AUTHORING.md:19`): `think→opus`, `do→sonnet`, `verify→sonnet`, `scan→haiku`. Pre-implement leans on `think` agents (architect, devils-advocate, spec-formalizer, api-designer, security-reviewer) = **Opus** = slowest per token. Reviewers/engineers already Sonnet. So nothing is misconfigured to "all Opus" — the cost is turn VOLUME × Opus latency × Opus[1m] context prefill, not tier misassignment.

Transcript schema (verified against `~/.claude/projects/<encoded-cwd>/<uuid>.jsonl`):
- One JSON object per line; some meta/non-JSON lines exist → the parser must tolerate per-line parse failure.
- Fields present: `type` (`user` | `assistant` | `system` | `mode` | `attachment` | `file-history-snapshot` | `last-prompt` | `ai-title`), `timestamp` (ISO8601 `Z`, millisecond precision) on 64/82 lines sampled, `message.content[]` carrying `tool_use` (`{name, input}`) and `tool_result`, and a `durationMs` field on some tool events (observed 123213, 120921).
- Tool names seen: `Bash`, `Task`, `AskUserQuestion`.

The data needed for the split ALREADY EXISTS in the transcript. No runtime instrumentation required.

A project's harness transcripts live at `~/.claude/projects/<encoded-cwd>/<uuid>.jsonl` — the same path form as the schema note above, where `<encoded-cwd>` is the project's own absolute root path with every `/` replaced by `-`. Current machine reality (verified 2026-08-05): **mintEnvoy HAS a transcript dir** (`~/.claude/projects/-Users-mykolakudlyk-Projects-private-mintEnvoy/`) — it is the currently-available probe target; **testForge20 does NOT** have a transcript dir under `~/.claude/projects/` yet (its install exists but no harness transcript is present — treat as pending re-install / conditional). The 2h happens in a consumer install like these, not in the forge dev repo.

## Goal

A tool (shipped into consumer installs, per D2) that, given a session transcript (or auto-located latest for the project), prints and stores:

- Per pipeline command (`/research`, `/specify`, `/plan`, `/breakdown`, `/grill`, `/spec-check`): total wall-clock and the split into (a) LLM generation time, (b) Bash/helper time, (c) Task/agent sub-session time, (d) human-answer time (gap while awaiting a user message / `AskUserQuestion` reply — D4), plus counts (turns, helper calls, agent dispatches).
- Session totals + the same split, so the single largest time bucket is unambiguous.

Deliverable is a **diagnosis**, not a perf change.

## Non-code levers (available NOW, independent of build)

These need no code. Items 1 and 2 are zero-quality-cost and recommended now, regardless of what the profiler later finds; item 3 is not a new recommendation (see below):

1. **`/fast`** — Opus faster output, no model downgrade, no quality loss, at a higher per-token cost (research-preview; requires usage credits / org enablement). Cuts latency on every stacked Opus turn in the Opus-heavy pre-implement.
2. **`/clear` between `/research` → `/specify` → `/plan` → `/breakdown`.** Pipeline state persists to disk (the handoff JSON chain — `handoff.json`, `plan-handoff.json`, `breakdown-handoff.json`); the next command re-reads disk. Clearing drops the Opus[1m] context-prefill tax that grows every turn.
3. **`/grill` + `/spec-check` are ALREADY opt-in** per their own specs (plans 23 and 62) — this profiler does NOT change that, and this plan makes NO pre-measurement recommendation to skip them (that would be exactly the "cut a gate before knowing it's the hog" the Problem section warns against). A user who already skips them on low-stakes features for time/cost reasons will simply see that reflected in Phase 2's numbers; whether skipping is worth it is a Phase-3 evidence question, not a lever asserted now.

The profiler validates or refutes the relative value of items 1 and 2 against real numbers.

## Decisions

- **D1 — Transcript post-analysis, NOT runtime hooks.** The harness already timestamps every event and records `durationMs` on tool calls. A PreToolUse/PostToolUse hook would re-capture existing data, add runtime overhead + per-install `settings.json` wiring, and only cover future runs. Transcript analysis is zero-overhead, retroactive (can profile a 2h run that already happened if its transcript survives), and reads ground truth from the harness itself. **NO pipeline / hook / `settings.json` change.**

- **D2 (REVERSAL — supersedes the prior draft's maintainer-only `scripts/` stance) — The profiler SHIPS in `src/`, installs into consumers, and runs in the real install.** It lives at `src/devforge/lib/` as a `profile_helper` + `profile_helper.py` launcher shim + a `_profile/` subpackage, mirroring the existing `audit_helper` / `review_helper` / `summarize_helper` launcher+subpackage pattern. **Rationale:** the 2h happens in a consumer install (testForge20 / mintEnvoy), NOT the forge dev repo — which is what the maintainer explicitly does not care about profiling. The maintainer will release, run the pipeline a few times in a real install, and hand the logs over. A maintainer-only `scripts/` tool (plan 41's home) cannot run there. This is the deliberate departure from plan 41's tool home — the tool SHAPE (helper + launcher + `tests/lib/` fixture) still follows plan 41 / plan 53 precedent, only the SHIP surface differs.

- **D3 — Measure first; defer ALL perf changes.** No retiering, no "lite mode," no gate removal in this plan. Those are a follow-on plan gated on this plan's Phase 2 numbers (Phase 3 opens it). Prevents cutting the wrong thing.

- **D4 — Human-answer time is measured and reported SEPARATELY**, never folded into "LLM time." A gap ending at a `user` message (or spanning an `AskUserQuestion` tool_use → next user turn) is the maintainer thinking/typing, not the framework being slow. Conflating them would mis-blame the framework.

- **D5 — Per-run STORAGE in the install.** Each profiler run writes a per-run report `.devforge/profile/<session>-<timestamp>.json` (the raw bucket split) plus a rolling human-readable `.devforge/profile/summary.md`. After N runs the maintainer hands over the whole `.devforge/profile/` dir; the tool (or a session) aggregates across runs to name the hog. These artifacts are **EPHEMERAL-class per plan 49** — add `.devforge/profile/` to `src/files/devforge.gitignore` so the consumer git tree stays clean under plan 49's disposition model. No untrack migration is needed (the dir is brand-new, never previously tracked) — unlike plan 49/56, which had to `git rm --cached` already-tracked files.

- **D6 — Python routes python-engineer → python-reviewer** (repo discipline). This plan makes NO command / agent / `main.md` edits (it is pure tool + storage + gitignore + install wiring), so NO instruction-author / instruction-reviewer / claude-code-guide loop is needed for the CODE — no Claude Code integration claim is authored or changed. (This PLAN doc itself was authored via the instruction-author → instruction-reviewer loop per the maintainer's workflow directive; that governs the doc, not the code.)

- **D7 — No CI exists in the repo; the pytest test against a fixture transcript IS the correctness gate** (same posture as plan 41). The profiler is a diagnostic — it prints a report and writes storage; it has no pass/fail exit semantics.

## Open questions (resolve per the phase noted in each OQ below — do NOT pre-answer here)

- **OQ1 — Duration source.** Is `durationMs` present on EVERY `Bash` / `Task` tool event, or only some? If reliable, use it directly for helper/agent time; else derive duration as `tool_result.timestamp − tool_use.timestamp`. Phase 1 supports BOTH paths, prefers `durationMs`, and falls back to the timestamp-diff when it is absent. Probe at Phase 0.
- **OQ2 — Agent sub-session nesting.** Do a `Task` (agent) dispatch's internal turns appear inline in the SAME transcript, or in a separate sub-agent `.jsonl`? If separate, the parent `Task` event's duration is the single correct measure of agent time — do NOT double-count by also parsing the child file. Probe at Phase 0 against a REAL consumer transcript that ran `/grill` or a review panel (an ensemble dispatch is where nesting would show).
- **OQ3 — Command-boundary detection.** How to segment the transcript into per-command spans. Candidate signal: a `user` message whose text starts with a known slash command (`/research`…), OR the first `Bash` call whose command contains `<cmd>_helper`. `/clear` starts a NEW transcript file, so a cleared chain spans multiple `.jsonl` — the tool must support a `--dir` mode that stitches a chain by mtime, PLUS a single-file mode. This is a pure design choice that does NOT need the real-transcript probe — decide at Phase 1 (segmentation-signal selection is part of building the command-segmentation step).
- **OQ4 — Install wiring (state as Phase-1b TASKS, not settled facts).** The emitter `_PROMOTED` list (`scripts/emitters/claude.py`) is for COMMANDS only — helpers are NOT promoted there; they ride the full-install `cp -R` of `src/devforge/lib`. BUT plan 53 established that some new subpackages must ALSO be added to the `install.sh` + `update.sh` surgical `--only` always-copy set. Phase 1b must therefore: (a) confirm the `cp -R` full install ships `_profile/` + the `profile_helper` launcher; (b) check whether the surgical `--only` set needs the new module; (c) add the `.devforge/profile/` line to `src/files/devforge.gitignore` (D5). These are tasks to verify at build, not pre-decided outcomes.
- **OQ5 — Multi-run aggregation output shape.** How the per-run `<session>-<timestamp>.json` files roll up into a single cross-run verdict the maintainer hands over (e.g. per-command median bucket across runs, or a "largest bucket by run" table). Propose a shape at Phase 1; leave the final form to build.

## Phases

### Phase 0 — Ratify + probe (maintainer gate)

No build. The maintainer confirms D1–D7 and the goal. In the same phase, run a throwaway probe (NOT committed) against a REAL consumer transcript under `~/.claude/projects/`, NOT the forge dev repo — mintEnvoy (`~/.claude/projects/-Users-mykolakudlyk-Projects-private-mintEnvoy/`) is the currently-available target; testForge20 is conditional on a re-install producing a transcript dir — to resolve OQ1 (`durationMs` coverage across Bash/Task events) and OQ2 (Task sub-turns inline vs separate file). Record the answers inline in this plan before Phase 1.

**Verify:** maintainer sign-off recorded here; OQ1 + OQ2 each answered with the probe command + its output pasted into this plan.

### Phase 1 — Build the analyzer (python-engineer → python-reviewer)

`src/devforge/lib/_profile/` subpackage:
- Transcript parse — tolerant line-by-line JSON parse (skip meta/unparseable lines), normalizing each event to `{type, timestamp, tool_name, duration_ms, text}`.
- Command segmentation — split the event stream into per-command spans via the OQ3 signal (single-file and `--dir`-stitched-by-mtime modes). Selecting the primary segmentation signal here settles OQ3.
- Bucket profiling — per segment + total, compute `wall`, `llm_s`, `bash_s`, `task_s`, `human_s`, `n_turns`, `n_helpers`, `n_agents`. Human time is a distinct bucket, never folded into `llm_s` (D4).
- Report formatting — a plain table with the largest bucket flagged.
- Per-run + rolling storage writer (D5) — write `.devforge/profile/<session>-<timestamp>.json` (raw bucket split) and append/update `.devforge/profile/summary.md`.

`src/devforge/lib/profile_helper` + `src/devforge/lib/profile_helper.py` — the launcher shim (mirrors `audit_helper` / `review_helper` / `summarize_helper`): `--transcript <path>` (or auto-locate latest in the project's transcript dir), `--dir <transcript-dir>` (stitch a `/clear`-split chain by mtime), prints the report and writes storage.

`tests/lib/_profile/` — a hand-authored fixture `.jsonl` exercising, with every function tested + run in the same turn (repo discipline): tolerant parse (a bad line + meta lines skipped); `durationMs`-present vs timestamp-diff-fallback (OQ1 BOTH paths); one Bash + one Task + one AskUserQuestion → correct four-bucket split; a human-answer gap classified as `human_s` not `llm_s` (D4); multi-command segmentation; and the storage writer (per-run JSON shape + rolling `summary.md`).

**Verify:** the `_profile` pytest suite is green; running the launcher against a real recent consumer transcript prints a coherent table whose per-segment buckets sum (± rounding) to that segment's wall-clock, and writes `.devforge/profile/<session>-<timestamp>.json` + `summary.md`.

### Phase 1b — Install wiring (the OQ4 tasks)

- Add `.devforge/profile/` to `src/files/devforge.gitignore` (D5, EPHEMERAL-class per plan 49).
- Confirm the full-install `cp -R` of `src/devforge/lib` ships `_profile/` + the `profile_helper` launcher into a consumer's `.devforge/lib`.
- Check whether the `install.sh` + `update.sh` surgical `--only` always-copy set needs the new `_profile/` module (plan 53 precedent) — add it only if the surgical path would otherwise skip it.

**Verify:** a fresh install/update lands `.devforge/lib/_profile/` + `.devforge/lib/profile_helper` executable in a consumer; `.devforge/profile/` is gitignored (a written run leaves the consumer git tree clean); the surgical `--only` decision is recorded (added or confirmed unnecessary).

### Phase 2 — Real-run diagnosis (the deliverable)

The maintainer releases to a consumer install, runs the pre-implement pipeline a few times; the profiler writes `.devforge/profile/*` on each run; the maintainer hands over the `.devforge/profile/` dir. Aggregate the per-run JSONs (OQ5 shape) into a per-command time-split table and record it in this plan. This is the deliverable — the numbers that name the hog.

**Verify:** a per-command time-split table for a real 2h-class run (aggregated across N runs) is recorded in this plan; the single largest bucket (LLM turns / agent sub-sessions / human-answer / helper) is unambiguous.

### Phase 3 — Decide optimizations from the data (opens a follow-on plan)

Read the Phase 2 table. Pick targeted cuts matched to the actual hog — candidates, chosen by EVIDENCE, NOT pre-committed here:
- If LLM-turn count dominates → reduce scratch-chain turn multiplication (fewer verb round-trips per command) and confirm `/clear`-between-stages savings.
- If agent sub-sessions dominate → retier specific `think`→`verify` agents (Opus→Sonnet) or make `/grill` / `/spec-check` skips the default for low-stakes.
- If human-answer dominates → the framework is NOT slow; trim rubric turns only if the maintainer wants (memory: rubric verbosity was previously validated — do NOT cut without an explicit ask).
- If Opus[1m] prefill dominates → institutionalize `/clear` between stages (doc + workflow note).

**Verify:** a new `71-…-PLAN.md` is opened citing the Phase 2 numbers as its evidence. This plan closes at Phase 2 (measurement delivered).

## Context for next session

- The whole point is **measure before cutting.** Do NOT add a perf optimization inside this plan — that is Phase 3's follow-on.
- Python helpers are proven fast (~80ms); if a future session is tempted to "speed up the helpers," re-read the Empirical Grounding — that is the wrong layer.
- **D2 is a reversal:** the profiler SHIPS into consumers (`src/devforge/lib/_profile/` + `profile_helper` launcher), because the 2h happens in a consumer install, not the forge dev repo. A maintainer-only `scripts/` tool (plan 41's home) could not run there. The tool SHAPE still follows plan 41 / plan 53 precedent.
- Storage is EPHEMERAL-class (plan 49): `.devforge/profile/` is gitignored via `src/files/devforge.gitignore`; no untrack migration needed (brand-new dir).
- Install wiring (OQ4): the emitter `_PROMOTED` is COMMANDS-only — helpers ride the `cp -R`; plan 53 shows some subpackages ALSO need the surgical `--only` set — Phase 1b decides.
- Transcript location: `~/.claude/projects/<encoded-cwd>/<uuid>.jsonl` (`<encoded-cwd>` = the project's absolute root with every `/` → `-`); mintEnvoy has a transcript dir now (available probe target), testForge20 is pending re-install. Schema facts are in Empirical Grounding; re-probe if the harness format has changed.
- Precedent for tool shape: plan 41 (`scripts/lib/agent_reachability.py` + CLI + `tests/lib/…`, no CI so the pytest IS the gate) for the test-is-the-gate posture; plan 53 for the surgical `--only` install decision; plan 49 for the EPHEMERAL gitignore disposition.

## When resuming work

1. If Phase 0 not signed off → present D1–D7 + goal to the maintainer, run the OQ1/OQ2 probe against a REAL consumer transcript, NOT the forge repo (mintEnvoy is the available target; testForge20 conditional on re-install), record answers here.
2. If signed off, Phase 1 not built → dispatch python-engineer for the `_profile/` subpackage + `profile_helper` launcher + `tests/lib/_profile/` (brief: the schema facts above, the four buckets, D4 human-time separation, OQ1 dual duration path, D5 storage writer), then python-reviewer.
3. If Phase 1 green → do Phase 1b install wiring (gitignore line + `cp -R` confirm + surgical `--only` check).
4. If Phase 1b done → hand the maintainer the Phase 2 run recipe; the maintainer releases, runs the pipeline a few times in an install, hands over `.devforge/profile/`; aggregate and paste the table here.
5. If the Phase 2 table exists → open the Phase 3 follow-on plan citing it.
