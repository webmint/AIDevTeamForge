# RESEARCH — 2026-09-27 — v2 wall-clock and token cost against v1: diagnosis

**Disposition:** diagnostic report. No code, spec, or plan file was changed to produce it. Untracked at
the time of writing; the maintainer decided on 2026-11-07 to commit it. It names no client, no install
path, no ticket, no component, and no symbol from any consumer codebase — the two transcript
populations are called "client installs A/B/C" and "the benchmark install" throughout.

**Question asked (maintainer, 2026-09-27):** "v2 runs several times longer than v1", then "is v2
more expensive in tokens?", then "is the price/time worth it?"

**One-line answer.** Yes on both costs, and not proven worth it on outcome. A pre-implement chain on
v2 costs 3–4× the wall-clock of v1 and 2–2.5× the output tokens / 4–6× the cached-context tokens.
Python is not the cost. The cost is the number of model turns (×2–4 per command) and the number of
stops for the human (×3), plus two mandatory commands v1 did not have. On the only shared benchmark
the outcome column is the same for both versions (probe failed); v2's measured advantage is analysis
quality, and that advantage lives in a small fraction of v2's mass.

---

## 1. Method

**Sources.** Claude Code session transcripts under `~/.claude/projects/<encoded-cwd>/*.jsonl`, plus
their `<session>/subagents/*.jsonl` children. Two populations, both on this machine:

| Population | Installs | Sessions | Dates (2026) | Generation markers |
|---|---|---|---|---|
| v1 | client installs A, B, C + the benchmark's post-implement session | 92 + 1 | Aug 28 – Sep 27 | bare `/research` etc.; no `*_helper` calls |
| v2 | the benchmark install (two transcript dirs) | 10 + 5 | Aug 31 – Sep 21 | `/devforge:*` markers; `*_helper` calls |
| v2, real work (added 2026-09-28, F10) | client install D — v2 `2.0.12`, wrapper mode, one feature end to end | 3 | Sep 25 – Sep 28 | `/devforge:*` markers; `*_helper` calls |

**Tools.**
- The shipped `profile_helper` (plan 70) for the per-segment bucket split (LLM / Bash / Task /
  Human / AgentBusy) and the segment windows. Run with `--workspace-root` pointed at scratch; nothing
  was written into any install or into this repo.
- Two scratch scripts (not in the repo) for what the profiler does not report: stop counts, idle
  vs. answering split, and token usage. Segmentation by the `<command-name>` user marker (valid for
  v1, where every command is user-typed); for v2 tokens the profiler's own segment windows were
  used because v2 commands can be model-invoked and then carry no user marker.
- Token sums deduplicate assistant messages by `message.id` (streaming repeats `usage` per content
  block). Subagent usage is attributed to the segment whose time window contains it. ⚠ Correction
  2026-09-28: in SUBAGENT transcripts the first event of a message carries a placeholder `usage`
  (`output_tokens` ≈ 8) and only a later event of the same id carries the real count, so the first
  pass under-counted agent OUTPUT tokens; the agent figures below are recomputed as the max per
  message id. Main-thread transcripts repeat the same `usage` on every event of a message, so
  main-thread figures were unaffected. Agent cache-read figures were unaffected either way.
- "Framework time" = wall − human gaps. "Answering" = human gaps under 30 min. "Idle" = human gaps
  of 30 min or more (breaks, overnight). Segments with fewer than 3 assistant turns were dropped as
  aborted invocations.

**Static weight** was taken from `git ls-tree main` (v1) and the working tree of `develop-2.0-init`
(v2) on 2026-09-27.

## 2. Findings

### F1 — Static weight: ×30 by lines, ×15 by files

| | v1 (`main`) | v2 (`develop-2.0-init`) |
|---|---|---|
| Files in repo | 62 | 908 tracked |
| Lines, all text | ~10.5K | ~340K |
| Python helpers | 0 | 117K lines, 334 files |
| Tests | 0 | 202K lines, 12,007 `def test_` for 2,258 helper `def`s |
| Command prose | 24 files, ~6K lines | 21 commands, 14K lines (`main.md` + references) |
| Plans at repo root | 0 | 121 files, 48K lines |
| Consumer setup | one `setup-wizard.md`, 567 lines | 4 commands, ~2.4K lines prose + ~30K lines Python |

Largest Python subpackages: `_generate_docs` 13.5K, `_research` 10.5K, `_constitute` 8.4K,
`_specify` 7.0K, `_pr_review` 6.8K, `_configure` 6.6K. `_generate_docs` alone is larger than all of
v1. `REGRESSION-ANCHORS.md` records 3 regressions ever fixed, all three in v2's own machinery.

### F2 — Python is not the cost

Bash bucket per v2 command run: 1–3.5 min, under 5% of wall. Plan 70 measured helper cold start at
~80 ms per call on 2026-08-05; a research run makes 31–40 helper calls ≈ 3 s of Python. What
looks like "the helper running" is the ~10 s model turn wrapped around each call.

### F3 — Per-turn cost is equal; turn count is ×2–4

Framework seconds per assistant turn: v1 8–17 s, v2 5–15 s. The difference is the count.

| Command | v1: framework min / turns / runs (median) | v2: LLM min / turns / helper calls (per run) |
|---|---|---|
| research | 14 / 98 / 32 | 68 / 172 / 31 · 30 / 258 / 40 · 35 / 249 / 31 |
| specify | 11.5 / 50 / 17 | 19 / 197 / 63 · 11 / 41 / 1 · 39 / 110 / 2 |
| plan | 7 / 44 / 28 | 3.5 / 18 / 4 · 4 / 77 / 7 · 23 / 81 / 4 |
| breakdown | 6 / 24 / 30 | not visible as its own segment (see caveats) |
| spec-check | — | 14 / 36 / 8, plus 12 min agent |
| grill | — | 31 / 70 / 17, plus 34 min agent |
| execute-task → implement | 60 / 192 / 41 | 83 / 483 / 54, plus 4 h agent (1 run) |
| review | 11 / 27 / 32 | 25 / 90 / 17 · 28 / 58 / 10 |
| verify | 11 / 32 / 38 | 1–5 / 14–26 / 3–8 |

Chain totals. v1 research→breakdown: ~40 min framework + ~10 min answering ≈ 50 min. v2
research→grill: 2.3–3.7 h framework and agent time + 30–60 min answering. This matches the "~2 h"
plan 70 recorded on 2026-08-05.

Where the turns come from (static, `src/commands/*/main.md`): research has 77 helper invocations,
34 phase/step headings, 9 phases marked MANDATORY; specify 74 helper invocations; discover 58;
generate-docs 55. Each `set-*` call is one full model turn.

### F4 — Stops for the human are ×3, and every stop can become an idle gap

| Command | v1 stops (median) | v2 stops (median) | v2 static: `AskUserQuestion` / "end the turn" |
|---|---|---|---|
| research | 4 | 12 | 13 / 15 |
| specify | 1 | 2 | — |
| plan | 0 | 2 | — |
| review | 3 | 9 | — |
| implement | 6 (execute-task) | 75 | — |
| configure | — | 14 | — |
| constitute | — | 8 | — |

Idle observed in v2 runs: grill 6 h, one research 7 h, implement 76 h, review 17–63 h. A stop the
user is not watching turns into an idle gap; v2 has three times as many chances.

### F5 — Two mandatory commands v1 did not have

`/devforge:plan` blocks without a fresh `spec-check.md` (`plan_helper verify-spec-check`);
`/devforge:breakdown` blocks without a completed grill (`breakdown_helper verify-grill-ran`, plan
85). Measured: spec-check ≈ 26 min (14 LLM + 12 agent), grill ≈ 65 min (31 LLM + 34 agent). About
1.5 h per feature, roughly a quarter of the v2 chain. Neither appears in the benchmark report's
"what v2 got right" list; spec-check returned CONSISTENT on the defective spec.

### F6 — Setup chain

configure: 8–15 min LLM, 26 min answering, 14 stops, 108–169 turns, 17–26 helper calls.
constitute: 11–22 min LLM, 35 min answering, 8 stops. Once per project, ~1.5–2 h with answering;
by token volume equal to one whole v1 feature chain. No outcome evidence exists for it either way.

### F7 — Tokens

Medians per run (v1) and per-run values (v2, substantive runs only). `rd` = cache-read input,
`wr` = cache-creation input.

| Command | v1: out k / rd M / wr k | v2: out k / rd M / wr k |
|---|---|---|
| research | 46 / 4.8 / 215 | 132 / 37.0 / 261 · 144 / 30.9 / 613 · 91 / 17.6 / 213 |
| specify | 42 / 5.0 / 110 | 101 / 22.8 / 183 · 51 / 28.6 / 2275 · 20 / 9.4 / 33 |
| plan | 33 / 3.2 / 121 | 20 / 5.4 / 65 · 62 / 8.8 / 147 (+3.5 M agent rd) |
| breakdown | 37 / 3.2 / 54 | folded into the previous segment |
| spec-check | — | 50 / 3.1 / 88 (+1.3 M agent rd) |
| grill | — | 47 / 13.0 / 486 (+12.5 M agent rd) |
| execute-task → implement | 89 / 24.8 / 334 (agents: +102 k out, 19.7 M rd, 12 agents median) | 175 / 71.5 / 2790 (agents: see the corrected line below the table) |
| configure | — | 128 / 40.6 / 1525 · 43 / 8.0 / 91 · 31 / 7.1 / 78 |
| constitute | — | 44 / 9.2 / 67 · 39 / 6.7 / 45 |

Corrected subagent figures (2026-09-28, max per message id — see Method): the largest v2 implement
run's 57 agents emitted 597 k output tokens over 46.6 M cache-read (the table's first pass said
71 k); grill's 3 agents 150 k output over 12.5 M; spec-check's 2 agents 77 k over 1.3 M; review's
agents 33 k over 12.5 M (median of 4 runs). v1 medians: execute-task agents 102 k over 19.7 M,
review agents 41 k over 5.8 M, verify agents 19 k over 4.7 M. Subagent output is therefore a
first-order cost in implement, grill and spec-check, not the rounding error the first pass showed.

Chain totals: v1 research→breakdown ≈ 160 k output, 16 M cache-read. v2 research→grill ≈ 260–400 k
output, 60–100 M cache-read, +17 M agent cache-read. Cache-read per turn doubled too (research 124 k
→ 260 k): each turn carries a 1,500-line `main.md`, helper output and references. Cost = turns ×
context, and both doubled.

Model mix differs, so no dollar conversion is made: v1 messages are ~83% `claude-opus-5`, ~15%
`claude-opus-5-5`; v2 are ~67% `claude-opus-5`, ~25% `claude-fable-5`, ~8% `claude-fable-5-1`.
Cache-read is the cheapest token class, so the money multiplier on that line is below ×4–6; output
at ×2–2.5 is the more expensive line.

### F8 — Outcome evidence (the frozen brownfield benchmark, 20 runs, 6 frameworks)

From the two untracked evidence files (plans 77 and 81), identifiers removed:

| Framework | Runs | Named the hidden second surface | Passed the probe |
|---|---|---|---|
| three other tools | 7 | 0 | 0 |
| one other SDD tool | 3 | 1 | 0 |
| DevForge v1 | 6 | 6 | 1 per the narrative ("the single run that passed"); 0 in the report's table |
| DevForge v2 | 1 | 1, and wrote the correct AC requiring both surfaces to change | 0 |

v2 was built to close v1's "discovery-to-lock inversion" (plan 77) and did close it; it then failed
on a different inference (the identical-tuple reading), which plan 81 addressed with six inference
rules. The plan 81 acceptance re-run has not happened. Confound named by the report itself: the v2
run was on `claude-fable-5`, all six v1 runs on `claude-opus-5`.

The report's own sentence on mass: "artifact volume varied 24×, test volume 14×, active time 17×,
review depth from none to mutation-tested — none of it correlates with the outcome."

### F9 — Side finding: the profiler's primary segmentation signal never fires

`src/devforge/lib/_profile/_segment.py` anchors `_COMMAND_MARKER_RE` at the start of the text and
uses `re.match`. Real user messages of both generations begin with `<command-message>…` and carry
`<command-name>` on the second line. Verified on 2026-09-27 against live text of both shapes: the
matcher returns `None` for both; it returns the name only when the marker is the first thing in the
text. Consequence: every segment the profiler reports comes from the `*_helper` Bash fallback; v1
transcripts (no helpers) profile as one `(preamble)` per session, and model-invoked v2 commands are
detected only through their helper calls. Not changed here.

### F10 — Addendum 2026-09-28: one feature on a v2 install in real client work

Client install D runs v2 `2.0.12` in wrapper mode on a brownfield monorepo. Three sessions,
2026-09-25 → 09-28, carried one feature from `/devforge:research` through three tasks of
`/devforge:implement`. Same tools as §1; subagent output counted with the corrected method. No
identifier from that install appears here.

**Per command, per run** (LLM min in the main thread / turns / helper calls; agent busy min;
cache-read main + agents; output main):

| Command | Runs | LLM / turns / helpers | Agent busy | Cache-read | Output | Stops · answering |
|---|---|---|---|---|---|---|
| research | 1 | 23 / 227 / 33 | — | 32 M | 100 k | 19 · 29 min |
| specify | 3 | 17 / 165 / 28 · 8 / 35 / 12 · 11 / 77 / 9 | — | 19 + 8 + 13 M | 98 + 44 + 34 k | 4 · 14 min (median) |
| spec-check | 3 | 15 / 22 / 6 · 15 / 17 / 4 · 17 / 20 / 4 | 16 · 14 · 19 | 17 M + 5 M | 108 k (+207 k agents) | 3 · 5 min |
| plan | 3 (+1 aborted) | 28 / 40 / 7 · 61 / 30 / 5 · 27 / 54 / 5 | 18 · 53 · 17 | 34 M + 22 M | 109 k | 2 · 6 min |
| grill | 2 | 52 / 49 / 10 · 75 / 51 / 9 | 58 · 101 | 18 M + 40 M | 91 k (+64 k agents) | 4 · 2 min |
| breakdown | 2 | 16 / 54 / 8 · 5 / 13 / 2 | 8 · — | 15 M + 3 M | 53 k | 3 · 3 min |
| implement | 1 (3 tasks) | 210 / 257 / 26 | 287 (37 agents) | 57 M + 55 M | 60 k (+213 k agents) | 5 · 6 min |

Research's tool mix repeats the benchmark's: 119 tool calls, 53 CBM MCP calls returning 86 KB of
its 169 KB, 34 helper calls returning 6 KB. Per-command LLM minutes, turn counts and helper counts
sit inside the benchmark ranges of F3, so F3–F5 hold on a second codebase and a newer build.

**Two multipliers the benchmark did not show.**

1. **The re-entry loop.** Both grill runs returned `RE-ENTER-UPSTREAM` with target `spec`
   (`grill-seed.json` records `cycle_count: 2`), so specify → spec-check → plan ran three times
   and grill twice for one feature; the third pass went on to breakdown instead of a third grill.
   The two passes that ended in grill cost 112 and 159 min of main-thread model time plus 92 and
   168 min of agent time; the third, ending in breakdown, 76 + 44 min. The feature's pre-implement
   total was ≈ 6.2 h main thread + ≈ 5 h agents, ≈ 230 M cache-read and ≈ 920 k output (main +
   agents). The v1 chain median is ≈ 50 min, 16 M, 160 k. Whether the two re-entries improved the
   plan is not measured; their cost is.
2. **One session, no `/clear`, from specify through implement.** Cache-read per message grew from
   276 k (first specify) to 580 k (plan) and 457 k (implement); the 1 M context window absorbed it
   and no compaction fired. Every command after the first ran at 4–8× the context a fresh session
   would carry, so every one of its turns cost that much more. Grill's main thread in the benchmark
   (§2.2 L3 discussion; 296 k → 422 k per message) showed the same effect.

**Implement, 3 tasks:** 7 engineer launches (3 implement, 4 repair, per the dispatch descriptions:
five `backend-engineer`, two `qa-engineer`) and 30 reviewer dispatches (`code-reviewer` 7,
`qa-reviewer` 9, `security-reviewer` 7, `performance-analyst` 7) — 37 agents in all; the
four-reviewer panel ran 2–3 rounds per task. 5 stops (one gate-blocked
question, one Stage A judgment, three Stage B approvals), 7 h 10 min human time in a 10 h 48 min
wall, almost all of it idle between approvals. ≈ 2.5–3 h of compute per task against the v1
execute-task median of ≈ 1 h per run.

**What F10 adds to Part 2.** Two candidate levers not in §2.2: (L9) a fresh session per pipeline
command — the emitted `CLAUDE.md` or each command's Phase 0 says so, or `/devforge:breakdown` and
`/devforge:implement` offer it — worth 4–8× on cache-read for every command after the first in a
session, at zero quality cost; (L10) make the re-entry cost visible and bounded — grill's 7.2 prompt
states what a `RE-ENTER-UPSTREAM` pick will cost (one more pass up to the next grill: 3.4–5.5 h of
model and agent time on this feature), and a second
grill on a revised plan attacks the delta against the recorded seed rather than re-running two full
passes. L9 is quality-neutral by construction; L10 changes plan 85's loop and needs a decision.

## 3. Verdict

- **Cost is certain and structural.** Turn count, stop count and the two mandatory commands are
  written into the specs; more runs will not move them.
- **Benefit is unproven on outcome.** One v2 run, model not pinned, probe failed; the best v1 run
  passed. What v2 demonstrably improved is the analysis artifact.
- **The improvement is concentrated.** Emission matrix, Coupling decision point, Rule 5, derived
  "not modified" entries, the six inference rules — prose-level forcing functions plus a few helper
  verbs. Not the setter round-trips, not the mandatory grill/spec-check, not the setup chain, not
  the test corpus.
- **Revealed preference, corrected 2026-09-28.** In September v1 ran on three client installs (32
  research runs, 41 execute-task runs); v2 ran only in the benchmark until 2026-09-25, when a
  fourth client install started running `2.0.12` on real work — one feature so far, measured in
  F10. The per-command numbers there match the benchmark's and add two multipliers the benchmark
  did not show.

## 4. Caveats

- v2 sample: one install, one codebase, 1–5 runs per command. v1 sample: three installs, 17–41 runs
  per command on client codebases.
- v2 `breakdown` never appears as its own segment: after plan 63 the model chains it without a
  user marker, and the profiler's fallback only splits when a different `*_helper` stem appears.
- Several v2 profiler rows carry multi-day human gaps and one carries an impossible LLM bucket
  (382 h over 32 turns); such rows were excluded from medians, not from totals.
- Idle/answering split uses a 30 min cap; a long think counts as idle.

## 5. What would settle "worth it"

1. The plan 81 acceptance re-run with the model pinned, three or more runs.
2. An ablation next to it: the same v2 with grill and spec-check off, and with one state write per
   phase instead of 30–70 setter calls. If the probe result holds, the price falls by roughly a
   third to a half without touching the forcing functions that produced the analysis advantage.
3. If the probe still fails with the six inference rules in place, the problem is the rules, not
   the harness, and rules are cheaper to carry in a v1-shaped shell.

---

## Part 2 — Optimization assessment

Read against the live tree on 2026-09-27: `src/commands/*/main.md`, the helper CLIs under
`src/devforge/lib/_*/_cli.py`, `src/CLAUDE.md`, and plans 106–123. Every lever below names the
mechanism it would change and the plan work it touches. ⚠ Line digits drift — grep the quoted text.
Savings are estimates from static counts and the medians in Part 1, not from a run.

### 2.1 Where a v2 turn's cost actually sits

Tool calls per run and bytes their results return into context (medians; v2 from the profiler's
segment windows, v1 from the user marker):

| Command | Calls | helper | CBM (MCP) | direct reads | git | ask | Result bytes | of which CBM | of which helper |
|---|---|---|---|---|---|---|---|---|---|
| research v2 | 92 | 32 | 45 | 12 | 5 | 5 | 274 KB | 196 KB (4.3 KB/call) | 7 KB (0.3 KB/call) |
| research v1 | 52 | 0 | 0 | 40 | 5 | 1 | 121 KB | — | — |
| specify v2 | 28 | 2 (63 on the heavy path) | 0 | 22 | 2 | 0 | 41 KB | — | 1 KB |
| specify v1 | 26 | 0 | 0 | 18 | 4 | 1 | 59 KB | — | — |
| plan v2 | 32 | 7 | 0 | 14 | 0 | 1 | 26 KB | — | 2 KB |
| grill v2 | 34 | 18 | 0 | 12 | 0 | 1 | 93 KB | — | 29 KB |
| configure v2 | 57 | 17 | 0 | 12 | 0 | 9 | 65 KB | — | 8 KB |

Three facts fall out:

1. **Helpers cost turns, not bytes.** 0.3 KB per call; 32 calls are ~35% of research's tool calls
   and ~2.5% of its returned bytes.
2. **CBM costs bytes.** 45 MCP calls return 72% of research's context bytes. v1 read code directly
   (40 `Bash` reads, 95 KB); v2 replaced that with graph queries that return twice the bytes.
3. **The model's own output is the largest context component.** A research run emits 91–144 k
   output tokens (v1: 46 k). At the median turn the cache-read is ~250 k tokens ≈ 60 k prose
   (`main.md` ~50 k + `CLAUDE.md` ~9 k) + ~70 k tool results + ~130 k accumulated own output.
   Assistant turns ≈ 2 × tool calls in both generations (narration around each call), so turn
   count drives this component twice: once as the narration, once as the setter payloads that
   repeat text already in the conversation. 28 instructions in research and 37 in breakdown say
   "copy … VERBATIM into your next user-facing message", so a helper result enters context twice.

Prose loaded at invocation (≈ bytes/4): research 50 k tokens, specify 30 k, breakdown 27 k, plan
25 k, implement 15 k, configure 14 k, constitute 14 k; `CLAUDE.md` 9 k.

### 2.2 Levers, ranked by measured share × feasibility

**L1 — One state write per phase instead of one per field.**
- *Now:* `_research/_cli.py` has 61 verbs, `_specify/_cli.py` 58; no verb accepts a phase's fields
  as one JSON or file payload — the path-shaped flags that exist (`--file-line`, `--handoff-path`)
  each carry a single value. `research/main.md` has 77 helper sites,
  `specify` 73, `breakdown` 33, `constitute` 33; measured 32 helper calls per research run, 63 on
  specify's heavy path.
- *Change:* an `apply --from-json <path>` (or stdin) verb per helper that runs the same validators
  the setters run and reports the failing field by name; the prose collects a phase's fields and
  writes once. Read, verify and render verbs stay.
- *Saving:* research −20–25 tool calls of 92 and their narration turns (≈ −25% turns); specify
  heavy path −40–50; breakdown, constitute proportionally.
- *Risk:* the per-setter gates must move into the batch validator, not vanish — `set-scope
  --evidence` on "one place", `set-dp-default-applied --delegated-reply`, `record-intake-
  classification --kind`. A batch that reports only "invalid" costs more turns than it saves.
- *Plans:* 107 D2 (`--change-kind` on `record-affected-area`), 106 D3 (split
  `--seeded-by-upstream` producers) and 109 D4 (thin verbs on both intake helpers) each add
  per-call surface. Design the batch verb first or each of them lands twice.

**L2 — Cap the CBM chain in research.**
- *Now:* Phase 2.3–2.5b, nine sweeps marked MANDATORY; 2.4b, 2.4c and 2.4e are "mode-independent".
  Phase 2.1's own estimate is 15–120 calls; measured 45 per run, 196 KB.
- *Measured by verb, 2026-09-28 (four research runs with ≥ 50 turns; per run):*

  | Verb | Benchmark install (older CBM): calls · KB/call · KB | Client install D (newer CBM, compact output): calls · KB/call · KB |
  |---|---|---|
  | `search_code` | 26 · 4.9 · 129 | 24 · 1.5 · 37 |
  | `get_code_snippet` | 15 · 3.3 · 51 | 12 · 3.1 · 37 |
  | `trace_path` | 5 · 2.5 · 12 | 11 · 0.3 · 3 |
  | `search_graph` | 3 · 2.2 · 6 | 5 · 0.6 · 3 |
  | `query_graph` / `get_architecture` / `get_file_outline` | ≤ 1 each | ≤ 1 each |
  | all CBM | ≈ 50 · — · ≈ 200 | ≈ 53 · — · ≈ 86 |

  Three things the split shows. (1) The volume is the spec's: `research/main.md` Phases 2.3, 2.4,
  2.4b, 2.4c, 2.4d, 2.4e and 2.6 prescribe ≈ 45 CBM calls between them, every one of those phases
  is marked MANDATORY, and 2.4b/2.4c/2.4e are mode-independent; the runs made ≈ 50. The sweeps do
  not stop when an earlier phase has already answered: the benchmark runs issued 79 `search_code`
  patterns of which 62 were distinct, 14 of them single words. (2) `search_code` — text search
  through the graph — is half of the CBM calls and two thirds of the CBM bytes on the benchmark
  install (26 of ≈ 50; 129 of ≈ 200 KB) and 45% / 43% on client install D, because Phase 2.3
  forbids raw `Read` / `Grep` / `Glob` / `grep` / `find` / `cat` over source-file extensions
  ("blocked by runtime hooks") and its CBM chain names `search_code` as the text search (its "only
  sanctioned" wording is attached to `get_code_snippet`, the source-read step). Those calls went
  out with `limit` 30–60 (the tool's default is 10) and, on the older CBM, in JSON whose every row
  repeats the encoded project path inside the qualified name. The graph part — `trace_path`, where
  the benchmark's caller-enumeration advantage came from — is 5–11 calls and 3–12 KB per run: the
  cheap part. (3) The newer CBM already helps without a forge change: the same 24 `search_code`
  calls returned 37 KB instead of 129. The live tool schema (loaded from the installed
  `codebase-memory-mcp` on 2026-09-28) exposes `mode=compact`, `limit`, `match_limit`,
  `source_max_lines` and `max_output_tokens` on `search_code` (`get_code_snippet` sizes to 2,500
  tokens by default, `trace_path` and `search_graph` to 3,200), and the recorded runs already
  passed `limit` and `mode` to it; the spec sets none of them, and `research/main.md`'s Phase 2.4
  sentence "The supported `search_code` argument is `pattern` only" is stale against that schema —
  lever (c) below has to correct it, not work around it. v1 research, for comparison, made 40
  `grep` / `cat` / `sed` calls
  through Bash returning 95 KB. CBM did not replace those reads with fewer, sharper queries; the
  mandated sweeps added calls on top, so a graph adopted to save tokens became the largest single
  source of them.

- *Change:* (a) a per-sweep call budget in the prose with a named fallback when it is hit; (b)
  make 2.4/2.4b/2.4e conditional on the previous phase's result and on `scope` / mode, keep 2.4c
  (helper-API surface enumeration → `declare-caller-total`) and `trace_path` unconditional — that
  is where the measured value sits; (c) pin the CBM call shape in the spec's prescribed calls:
  `search_code` with `mode=compact`, `limit` 10 and `max_output_tokens`, `get_code_snippet` and
  `trace_path` with explicit `max_output_tokens`; deduplicate patterns across sweeps; (d) reuse
  Phase 0.2's index refresh output instead of re-querying it; (e) decide separately whether the
  raw-`grep` ban stays — `grep -n` yields the same exact `file:line` the grounding rule needs at
  ~1 KB a call, so the ban is a bet on CBM, not a technical necessity.
- *Saving:* on the benchmark-class CBM (c) alone ≈ 200 → 90 KB per run; (b) ≈ 50 → 25 calls and
  their narration turns, ≈ −25–30% of research time; together −30–50% of research context bytes
  and lower cache-read per turn for the rest of the run.
- *Risk:* the caller enumeration (2.4c → `declare-caller-total`) and the Phase 3 emission matrix
  are what the benchmark credited; the inference rules from plan 81 need complete value sets, not
  sampled ones. Cap those last and never below completeness.
- *Plans:* 113 (skip-list drops `target/` source dirs), 114 (glossary CBM `project` arg), 115
  (wrapper-mode `.gitignore` blinds the index) all make CBM return MORE where today it returns
  nothing. Land the budget with them, not after — otherwise fixing the blind spots raises research
  bytes further.

**L3 — Make the grill gate policy-driven; leave spec-check required.**
- *Now:* `plan_helper verify-spec-check` (plan 82) and `breakdown_helper verify-grill-ran` (plan
  85) exit 2 with no knob; `src/CLAUDE.md` calls spec-check "a required step". Measured ≈ 1.5 h
  and ≈ 30 M tokens per feature for the pair. `configure` Q9 writes `workflow_enforcement`
  (Strict / Moderate / Light); nothing in the pipeline reads it — the only consumer is
  `constitute`'s prose composition (`constitute/references/section-shapes.md`, "Composition
  source: … `workflow_enforcement`"). The knob the user answers today gates nothing.
- *Change:* `verify-grill-ran` reads `workflow_enforcement` from `.devforge/configure.yaml`:
  Strict = required (today), Moderate/Light = `/devforge:breakdown` offers `/devforge:grill` and
  proceeds on decline, recording the decline in the breakdown handoff.
- *Saving:* up to ~1 h and ~26 M tokens per feature under Moderate/Light; nothing under Strict.
- *Why not spec-check too:* plan 82's origin is an observed incident (a phantom AC passed
  CONSISTENT), and its fix — subject resolution before formalization — lives inside spec-check.
  Plan 85's origin is recorded as a maintainer decision with "no incident behind this plan".
  Reopening 85 costs a decision; reopening 82 costs the fix.
- *Plans:* none of 106–123 touches either gate.

**L4 — Research stops: 12 → 8, one of them a design change.**
- *Now:* Phase 0.5 echo-back (1, up to 2), rubric six dimensions one per turn — by explicit rule
  ("ask each dimension question separately and wait for the user's answer in its own turn … that is
  the forcing function this phase exists for"), Phase 2.1 cost gate (1), mode-flip/drift asks
  (0–2), design-reference prompt (1, non-gating), save prompt (1). Measured 12.
- *Change (a), no principle touched:* delete the Phase 2.1 cost gate. It asks proceed/cancel on
  a call-count estimate the user cannot act on; the cancel arm's value is unmeasured and its cost
  is one stop on every run. −1.
- *Change (b), via plan 123:* gate the design-reference prompt on project type. −1 on non-UI
  projects.
- *Change (c), maintainer decision:* ask the rubric in two rounds (symptom + affected_area +
  repro_or_current; desired + scope + unchanged_behavior), still persisting per dimension with its
  own `--state`. −3. This contradicts the per-turn rule quoted above, and `specify` already runs
  the opposite rule for decision points ("bundle every question that is NOT conditionally
  dependent into a single `AskUserQuestion` call"). The two commands disagree on the principle
  today; the assessment records the conflict rather than picking a side.
- *Risk:* (c) weakens the intake forcing function the plan-77/81 analysis advantage rests on (the
  Coupling decision point is a rubric outcome). (a) and (b) carry no such risk.

**L5 — Setup chain stops, one-time per project.**
- *Now:* `configure` Phase 4 asks Q9, Q10, Q12, Q13 one `AskUserQuestion` each; Q11 is four calls
  plus four subagent probes (one per model alias); Phase 3 is a bulk echo. `constitute` has a
  per-section bulk confirmation, three forcing-function echo blocks, Q-mode and the hook opt-in.
  Measured: configure 14 stops / 26 min answering; constitute 8 / 35 min.
- *Change:* bundle Q9, Q10, Q12, Q13 into one call (four questions, the tool's cap) → −3; probe
  all aliases in one subagent → −3 dispatches; Q11 in two calls (think+do, verify+security) → −2.
  Delegation rules stay per question.
- *Saving:* about a third of configure's stops; roughly −10 min answering per project.
- *Plans:* 116, 117, 118, 120, 122, 123 all edit `configure`; 123 adds a project-type question —
  put it in the same bundled call.

**L6 — Implement's per-task gate: build plan 110 first.**
- *Now:* Stage B `approve` on every task, Stage A per decision item, sequential by rule. Measured
  75 stops and 76 h idle in one run.
- *Plan 110* collapses the gate onto `review_checkpoint` (D2, arm i) and restores a context-health
  halt (D8). It is the single largest stop reducer among the open plans and needs no new mechanism.
- *Caveat recorded in the plan itself:* checkpoints set while the field was inert were set
  carelessly (OQ-7); the counter is a poor proxy for context pressure (OQ-1). Both stand.

**L7 — Prose size and the verbatim-copy convention.**
- *Now:* the "copy stderr VERBATIM … then end the turn" recovery paragraph is repeated at nearly
  every helper site; research renders the report twice (`render` at Phase 3 as a preview and at
  Step 4.4 with the real path — the closing message only refers back to that output) and the
  orchestrator writes the bytes it received; 28/37 verbatim-copy
  instructions in research/breakdown.
- *Change:* (a) one shared recovery paragraph, cited by name from each site; (b) verbatim echo
  only for exit-2 / BLOCKED paths and user-facing renders, an acknowledging line for the rest;
  (c) `render --out <path>` so the report never transits the model.
- *Saving:* prose −30–40% per command (research ~50 k → ~30 k tokens at invocation); own-output
  tokens down by the echoed bytes; one fewer `Write` turn per save.
- *Risk:* the convention exists so gate messages are not paraphrased — keep it exactly there.

**L8 — Not levers.** Python runtime (≤ 5% of wall); per-turn model speed (equal to v1); agent
dispatch in pre-implement (only grill and spec-check dispatch there); `generate-docs` (not
measurable in these transcripts — its segments are 2–7 turns, so the real runs sit in
unrecognized sessions).

### 2.3 Plans 106–123: effect on cost

| Plan | Status (2026-09-27) | Cost effect | Note |
|---|---|---|---|
| 106 Intake provenance continuity | Phase 0 closed, in build | neutral | D2 ratified as an INFORMATIONAL notice, no user gate; D1 instruction-only; D3 nit |
| 107 Surface path proof | Phase 0 open | neutral to +1 call | D2/D3 add flags to existing setters; D4 advisory cross-check verb (+1 call); D6 browser rung REJECTED in the recommendation |
| 108 Scope rule downstream regime | Phase 0 closed, not built | neutral | wording in `CLAUDE.md` item 17 + docs sweep; "raise it" needs no artifact |
| 109 Re-entry chain continuity | Phase 0 open | neutral | helper-side third pending arm; one extra prompt only when a stale downstream exists |
| 110 Implement auto-approve | Phase 0 open | **strongly negative (good)** | see L6 |
| 111 WIP marker contract | Phase 0 open | neutral | wire/retire/document a dead marker API |
| 112, 113, 114, 115 | stubs | neutral, then + bytes | CBM/index correctness; where they succeed CBM returns data it now omits (see L2) |
| 116, 117, 118 | stubs | neutral | configure detection correctness |
| 119, 121 | stubs | neutral | validator scope; stderr `SyntaxWarning` noise — 121 removes bytes the commands echo verbatim |
| 120, 122 | stubs | neutral | configure render/prune order |
| 123 Project-type-gated design intake | stub | **negative (good)**, −1 stop ×3 commands on non-UI | see L4(b), L5 |

Nothing in 106–123 touches L1 (setter round-trips), L2 (CBM volume), L3 (the gates) or L7 (prose
size). Those four carry most of the measured cost.

### 2.4 Do not cut

The parts the benchmark credited, with where they live: the emission matrix (research Phase 3,
orchestrator-composed, written at Step 4.5b); the benchmark report's "Coupling decision point" —
the rubric's `scope` question with its `set-scope --evidence` gate; Phase 0.5 intake echo-back
(closes the plan-18 over-solve failure); the Phase 2.4c helper-API surface enumeration
(→ `declare-caller-total`); Rule 5 in `src/commands/plan/main.md` ("An alternative rejected as
IMPOSSIBLE …"), not in the architect agent file; the six inference rules (plan 81); subject
resolution in spec-check (plan 82); the typed handoffs between stages. Every lever above is
written to leave these intact.

### 2.5 Order, and what to measure

1. Ratify and build plan 110 (L6). Largest stop reduction, mechanism already designed.
2. Design the batch write verb (L1) before 106 D3 / 107 D2 / 109 D4 add more per-call flags.
3. CBM budget (L2) together with 113/114/115.
4. Configure bundling (L5) together with 116–118, 120, 122, 123.
5. Grill policy knob (L3); spec-check unchanged until the plan-81 rerun says otherwise.
6. Prose diet and `render --out` (L7); delete the cost gate (L4a).

If L1, L2, L5, L7 and 110 land, the static counts predict for research: tool calls 92 → ~55,
turns ≈ −40%, context bytes ≈ −50%; for implement: stops 75 → the number of `Review checkpoint:
Yes` tasks; for the chain: −1 h under a non-Strict policy. These are predictions from counts.
The measurement that would confirm them is the ablation in Part 1 §5, run through
`profile_helper` after its marker anchor (F9) is fixed so v1 and model-invoked v2 segments both
resolve — otherwise the before/after tables cannot be compared.
