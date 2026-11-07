# 127 — CBM vs Files Token Measurement Plan

**Created**: 2026-10-03
**Status**: **Phase 0 OPEN — nothing below is ratified, no close record exists, and no build phase may start. NOTHING IS MEASURED.** This is a measurement plan: it edits nothing under `src/`, whatever its result (D10). ⚠ **The evidence class, to be repeated in every summary of this plan:** ONE observational, confounded measurement exists (the 2026-09-27 cost diagnosis); NO controlled comparison exists; this plan would produce the first; NOTHING is measured yet. ⚠ **Sequencing.** The maintainer works the open plans in NUMERIC ORDER. On 2026-10-03, plans 109, 110, 111 and 126 read *"Phase 0 OPEN"* and plans 112–124 read *"Stub"* in their Status lines, so under that order this plan's runs sit behind them unless the maintainer directs otherwise — the precedent for such a direction is plan 125, *"built ahead of plan 108 by ratified D5"* (`PLAN-STATUS-ARCHIVE.md:99`). ⚠ **Numbered 127 because 126 was the highest plan number at the repo root on 2026-10-03 and no other `127-*` file existed when this plan was created (2026-10-03). Other sessions work in this checkout and may take 127 first; a resuming session re-checks the number before trusting it.** ⚠ **Every `file:line` here was read on 2026-10-03 and will drift — grep the quoted text, never the digits.**

The maintainer asked on 2026-10-03 whether this framework can claim that CBM (codebase-memory-mcp) saves tokens compared to reading files. **The honest answer today: no such claim is supported.** The only measurement in this repo, `RESEARCH-2026-09-27-V2-COST-DIAGNOSIS.md` (hereafter *the diagnosis*), is observational and confounded, and it points the other way — in the median v2 `/devforge:research` run, 45 CBM calls returned 72% of the run's tool-result bytes (E1). **This plan designs a CONTROLLED A/B in which the discovery TOOL — the CBM graph or file tools — is the only variable, pre-registers the scoring and the decision rule (D9) before any scored run, and records the result.** ⚠ **What the result changes belongs to plan 124's lever 2, which already owns it; this plan only supplies the evidence that lever lacks (D10).**

---

## Origin & evidence

⚠ **Evidence class, stated first and repeated in every summary of this plan: ONE observational, confounded measurement exists (the 2026-09-27 cost diagnosis); NO controlled comparison exists; this plan would produce the first; NOTHING is measured yet.** This plan names no client, install, repo, branch, ticket, component or consumer path, and no phase of it may introduce one. The diagnosis's own labels — "client installs A/B/C/D", "the benchmark install" — are the only names it uses for the populations it cites.

### The maintainer's question — 2026-10-03

As relayed to this draft by the orchestrator: *"Can we claim that CBM (codebase-memory-mcp) saves tokens compared to reading files?"* — and, on how to find out, *"two identical repos with identical tasks, v1 vs v2 for measurements."*

- **It is a question and a design sketch, never a ratification.** It names no outcome for any decision below.
- **D1 keeps "two identical repos with identical tasks" exactly and reframes one word:** the arm variable is the DISCOVERY TOOL within one forge generation, not the forge generation. The reframe is the orchestrator's proposal, and Phase 0 ratifies or declines it like every other item.

### Verified structure (2026-10-03)

⚠ **Line digits drift — grep the quoted text, never the digits.** The `E` labels below are this plan's. The diagnosis numbers its own findings `F1`–`F10`, so this plan cites them as "diagnosis F9" and never uses a bare `F` label.

**E1 — The only measurement, and which way it points.** The diagnosis's Part 2 §2.1 tool-mix table, medians per run (grep `| research v2 | 92 |`, `RESEARCH-2026-09-27-V2-COST-DIAGNOSIS.md:301`–`:302`; the medians, `:296`–`:297`): **research v2** = 92 tool calls, 45 CBM MCP calls, 12 direct reads, 274 KB of tool-result bytes of which 196 KB CBM (4.3 KB per call); **research v1** = 52 calls, 0 CBM, 40 direct reads, 121 KB. Its fact 2 (`:313`–`:314`): *"**CBM costs bytes.** 45 MCP calls return 72% of research's context bytes. v1 read code directly (40 `Bash` reads, 95 KB); v2 replaced that with graph queries that return twice the bytes."* Its F10 addendum finds the same shape on one real-work v2 install (`:213`–`:214`): *"119 tool calls, 53 CBM MCP calls returning 86 KB of its 169 KB"*.

**E2 — The split by verb.** The diagnosis's lever L2 (grep `**L2 — Cap the CBM chain in research.**`, `:346`) measures per run, on four research runs (`:349`–`:358`):

| Verb | Benchmark install (older CBM): calls · KB/call · KB | Client install D (newer CBM, compact output): calls · KB/call · KB |
|---|---|---|
| `search_code` | 26 · 4.9 · 129 | 24 · 1.5 · 37 |
| `get_code_snippet` | 15 · 3.3 · 51 | 12 · 3.1 · 37 |
| `trace_path` | 5 · 2.5 · 12 | 11 · 0.3 · 3 |
| `search_graph` | 3 · 2.2 · 6 | 5 · 0.6 · 3 |
| all CBM | ≈ 50 · — · ≈ 200 | ≈ 53 · — · ≈ 86 |

Three of its sentences carry the case this plan tests. *"CBM did not replace those reads with fewer, sharper queries; the mandated sweeps added calls on top, so a graph adopted to save tokens became the largest single source of them."* (`:382`–`:384`). On the raw-grep ban: *"`grep -n` yields the same exact `file:line` the grounding rule needs at ~1 KB a call, so the ban is a bet on CBM, not a technical necessity."* (`:393`–`:394`). And the graph part: *"`trace_path`, where the benchmark's caller-enumeration advantage came from — is 5–11 calls and 3–12 KB per run: the cheap part."* (`:371`–`:373`). The `search_code` calls *"went out with `limit` 30–60 (the tool's default is 10)"* (`:369`–`:370`), and *"the recorded runs already passed `limit` and `mode` to it; the spec sets none of them"* (`:377`–`:378`).

**E3 — The diagnosis's method, and why this plan re-creates its code.** Its §1 (grep `**Sources.** Claude Code session transcripts`, `:22`): the sources are `~/.claude/projects/<encoded-cwd>/*.jsonl` plus their `<session>/subagents/*.jsonl` children; token sums deduplicate assistant messages by `message.id` (`:39`); in SUBAGENT transcripts the first event of a message carries a placeholder `usage` and a later event carries the real count, so agent output is taken as the max per message id, while main-thread transcripts repeat the same `usage` on every event of a message (`:40`–`:45`); "framework time" is wall minus human gaps (`:46`); segments with fewer than 3 assistant turns are dropped (`:47`–`:48`). Its measurement code was *"Two scratch scripts (not in the repo)"* (`:35`). **This plan cannot re-run them, so D8 re-creates the measurement code and keeps it.**

**E4 — The diagnosis's confounds.**
- **Model.** Plan 124 records that on the benchmark *"the v2 run used a different model from all six v1 runs"* (`124-PIPELINE-COST-REDUCTION-PLAN.md:14`; diagnosis F8, `:177`–`:178`), and that *"the model mix differs between the two transcript populations"* (`124-…:8`).
- **CBM version.** The all-CBM totals in E2 — ≈ 200 KB against ≈ 86 KB per run, on ≈ 50 against ≈ 53 calls — differ by ≈ 2.3×. ⚠ **That ratio is this plan's arithmetic, not a figure the diagnosis states,** and the two populations ran on different codebases. The diagnosis attributes the drop to the newer CBM: *"The newer CBM already helps without a forge change: the same 24 `search_code` calls returned 37 KB instead of 129."* (`:373`–`:374`).
- **Installs.** v1 ran on client installs A, B and C; v2 on the benchmark install and, from 2026-09-25, on client install D — v2 `2.0.12` in wrapper mode, 3 sessions (§1's population table, `:25`–`:29`).
- **Machine-level steering** (E10) — present on 2026-10-03; whether it was present during the diagnosis's window is not verified.

**E5 — One run per fresh session.** Diagnosis F9 (grep `### F9 — Side finding`, `:183`): the profiler's `<command-name>` segmentation never fires, and *"v1 transcripts (no helpers) profile as one `(preamble)` per session"* (`:189`–`:190`). **Consequence for this plan:** D6 runs one research per fresh process, so no segmentation is needed.

**E6 — The lever that lacks this evidence.** Plan 124's lever 2 (grep `**CBM call budget in`, `124-…:22`) prescribes per-sweep budgets, conditional sweeps, `search_code` pinned to `mode=compact`, `limit` 10 and `max_output_tokens`, and leaves *"whether that raw-read ban stays decided separately"*. The diagnosis's L2(e) is that separate decision's case (`:392`–`:394`). **This plan is the evidence that separate decision lacks.** Plan 124's Status line (`124-…:4`) queues it after every plan numbered 106–123.

⚠ **E7, E8 and D1 describe the tree on 2026-10-03, and two plans that build before this one under numeric order can change it.** Plan 123 (`123-PROJECT-TYPE-GATED-DESIGN-INTAKE-PLAN.md`, a Stub) targets the design-intake ask — E8 item 3. Plan 124's item 2 pins `search_code`'s `limit`, `mode` and `max_output_tokens` and makes sweeps conditional, and its item 3 deletes the Phase 2.1 cost gate — E8 item 10 and operator-script row 10 (`124-PIPELINE-COST-REDUCTION-PLAN.md:22`–`:23`). **Either landing first falsifies "as shipped", "pre-applied in neither arm", "the shipped spec sets no limit" and E7's chain. If plan 123 or 124 lands before Phase 1, Phase 1 re-derives E8 and arm A's spec from the INSTALLED commit, and D1 is re-ratified** (Phase 1's Verify).

**E7 — Where the belief "CBM saves tokens" is encoded: `/devforge:research`.** None of these is edited by this plan; each is a surface the result bears on.
- **`src/commands/research/main.md` `### Phase 2.3 — CBM discovery chain (MANDATORY order)`** (`:401`). Its chain is `search_graph` → `search_code` (on 0 hits) → `trace_path` → `get_code_snippet` (`:405`–`:408`).
- **Four ban sentences in that file:**
  - `:403` — *"Raw `Read` / `Grep` / `Glob` / `grep` / `find` / `cat` over source-file extensions are forbidden and will be blocked by runtime hooks."*
  - `:408` — *"This is the only sanctioned source-read path; do not use raw `Read`."*
  - `:257`, in Phase 1's `### Pre-rubric docs scan (orchestrator-only)` — *"Use CBM for the package + concern lookups; do NOT use raw `Read`/`Grep`/`Glob`:"*
  - `:1307`, in Phase 3's `### Emission matrix` step 3 — *"Raw `Read` / `Grep` / `Glob` / `grep` / `cat` over source files stay forbidden (Phase 2.3)."*
- **The grounding rule** (`:412`): every `file_path:line` passed to `record-finding` is copied from a `search_graph` or `search_code` result row.
- **The Phase 2 sweep map, by heading:** Phase 2.1 Cost gate (`:384`), 2.2 Read docs layer first (`:390`), 2.3 (`:401`), 2.3b Framing challenge (`:414`), 2.4 Parallel-pattern sweep (`:446`), 2.4b Canonical-pattern search (`:470`), 2.4c Helper-API surface enumeration (`:506`), 2.4d Click-handler-to-write-boundary trace (`:664`), 2.4e Feature-surface sweep (`:733`), 2.5 Hypothesis enumeration (`:791`), 2.5b Literal archaeology (`:841`), 2.6 Wire findings into helper (`:940`).
- **Phase 0.2 — CBM index refresh** (`:62`) runs `.devforge/lib/generate_docs_helper preflight` unless `.devforge/.preflight-stamp` is fresher than 60 seconds (`:68`); that helper runs `codebase-memory-mcp cli index_repository` (`src/devforge/lib/_generate_docs/_preflight.py:356`).
- **Phase 2.1** (`:386`) estimates 15–120 CBM calls by scope and asks proceed / cancel (`:388`).
- **Helper code carries CBM vocabulary too, and no arm can change it without a `src/` edit.** Phase 2.4c Step 3 records a dead sibling with `--verified-via <trace_path|search_code>` (`:616`), says *"always pass `--verified-via search_code`"*, and adds *"The helper accepts only those two literal values."* (`:619`) — enforced by `choices=("trace_path", "search_code")` (`src/devforge/lib/_research/_cli.py:939`). `declare-caller-total`'s docstring defines its total as the row count of `trace_path(<helper-qn>, mode=calls, direction=inbound)` (`src/devforge/lib/_research/_cmds_dataflow.py:227`, `:235`–`:236`), and `research_helper`'s own messages name `trace_path`: the `declare-caller-total` rejection (`_cmds_dataflow.py:251`) and three verify messages (`src/devforge/lib/_research/_cmds_render_verify.py:477`, `:485`, `:664`).
- **Orchestrator-inline.** *"No subagent dispatch — every phase runs in the main thread."* (`:9`); Phase 2.1: *"no fresh subagent boot"* (`:386`). **A run's whole cost therefore sits in ONE main-thread transcript** — a reason D2 picks this command.

**E8 — Every question `/devforge:research` can ask.** D4's operator script must cover each.
1. **Phase 0.3** — the topic comes from `$ARGUMENTS`; the fallback `"What's the topic? (bug or enhancement, one sentence)"` (`:100`) fires only on empty arguments, which this protocol never passes.
2. **Phase 0.5** — `"Is this interpretation right?"` with `confirm` / `correct`, via AskUserQuestion (`:155`); a reply that picks neither is asked once more (`:159`).
3. **Phase 1, design reference** — a free-text prompt asked before the first dimension, opening *"Is there a design reference for this feature's UI"* (`:228`).
4. **Phase 1, the six dimensions, one per turn** (`:269`–`:270`): `scope` closed-choice `one place` / `feature-wide` / `cross-cutting` via AskUserQuestion; `symptom`, `affected_area`, `repro_or_current`, `desired`, `unchanged_behavior` as free-text prose prompts. The rubric is MANDATORY and never skipped on pre-filled input (`:209`); the stop discipline ends the turn after every prompt (`:378`).
5. **Phase 1, narrow-framing follow-up** — a `one place` answer with no locality citation can draw one follow-up asking for it (`:296`).
6. **Phase 1, conflict** — `"Which to keep — the new answer or the prior one?"` (`:306`).
7. **Phase 1, drift note** — `"Heads up — your <new dimension> answer suggests <observed drift>. Adjust <affected dimension> or continue?"` (`:321`).
8. **Phase 1, mode** — `"Treat this as a bug or an enhancement?"`, on a mode-flip (`:323`) or a mixed-signal symptom (`:368`).
9. **Phase 1, coverage echo** — after `symptom-coverage`, the user continues clarifying or accepts gaps (`:338`–`:342`).
10. **Phase 2.1** — `"Investigation will scan roughly <N> CBM calls. Proceed?"` with `proceed` / `cancel` (`:388`).
11. **Phase 2.4d** — three fallback prompts when the sweep misses the handler, the write boundary, or the intermediate chain (`:678`, `:686`, `:696`). Phase 2.4d runs only in bug mode on a presentation-layer symptom (`:664`).
12. **Phase 4, Step 4.1** — TWO questions in ONE AskUserQuestion call (`:1335`): `"Save this research as feature '<proposed-slug>'?"`, whose tool-appended free-text row is the rename path (`:1337`), and `"Which ticket is this feature tracked under?"` with `No ticket` / `I'll type the ticket` (`:1339`).
13. **Phase 4, Step 4.2** — a missing or rejected ticket re-asks Step 4.1's question 2 (`:1385`).

**E9 — The shipped hooks.** `src/settings.template.json` wires five:
- PreToolUse `Read|Grep|Glob` → `cbm-code-discovery-gate` (`:28`–`:32`); PreToolUse `Bash` → `bash-ban-raw-tools` (`:37`–`:41`); PostToolUse `Bash|mcp__codebase-memory-mcp__.*` → `cbm-mcp-marker` (`:48`–`:52`); SessionStart `startup|resume|clear|compact` → `cbm-session-reminder` (`:59`–`:63`) and `cbm-sync-session-start` (`:68`–`:72`).
- `install.sh` copies the template to `<install>/.claude/settings.json` (grep `cp "$TEMPLATE_DIR/src/settings.template.json"`, `install.sh:442`), the scripts to `<install>/.claude/hooks/` (`:444`–`:445`), and `src/mcp.json` to `<install>/.mcp.json` (`:440`), which registers `codebase-memory-mcp` (`src/mcp.json:10`).
- **`cbm-code-discovery-gate`** keys `GATE=/tmp/cbm-code-discovery-gate-$PPID` (`src/hooks/cbm-code-discovery-gate:7`): when the file exists it exits 0; otherwise it creates the file, prints a `BLOCKED:` message to stderr and exits 2. Its header reads *"Once per Claude Code session (PPID-keyed) blocks the call"* (`:3`), and its message ends *"If you still need this tool, retry — this gate fires once per session."* (`:13`). ⚠ **So the "ban" is a once-per-session nudge by design, not a block.** It also deletes gate files older than one day (`:8`).
- **`bash-ban-raw-tools`** keys `GATE=/tmp/bash-ban-raw-tools-$PPID` (`src/hooks/bash-ban-raw-tools:8`) and fires the same way, once, on a command matching `\b(grep|find|cat)\b` together with an extension from `py|js|ts|tsx|jsx|vue|go|rb|java|rs|c|h|cpp|hpp|cs|swift|kt|php|scala` (`:15`–`:16`). `rg`, `sed`, `head` and `awk` never match.
- **`cbm-mcp-marker`** appends one `<UTC timestamp> <tool_name>` line per Bash or CBM MCP call to `${CLAUDE_PROJECT_DIR:-.}/.devforge/cbm-usage.log` (`src/hooks/cbm-mcp-marker:8`–`:10`). **In arm B, that log filtered to `mcp__codebase-memory-mcp__` names is the leak detector.**
- **`cbm-session-reminder`** injects a block opening `CRITICAL - Code Discovery Protocol:` into every session start (`src/hooks/cbm-session-reminder:6`).
- **`cbm-sync-session-start`** runs `.devforge/lib/cbm_sync_helper check` (`src/hooks/cbm-sync-session-start:41`). On `missing` or `drift` it injects an instruction to call `index_repository` or `detect_changes`; on `current` it is silent. The stamp it compares against `HEAD` is `.devforge/cbm-last-indexed-sha`.
- **The installed `CLAUDE.md` documents the hooks.** `src/CLAUDE.md`'s `## CBM-first Protocol Enforcement` (`:185`) has a `### Disabling individual hooks` (`:197`) reading *"To disable any hook, remove its entry from the corresponding event array in `.claude/settings.json`."* (`:199`) — **D1's delta (i) is that documented switch.** Its Artifact Storage bullet (`:301`) sends structural queries to the graph.

**E10 — CBM and token steering on this machine, outside any install.** Read on 2026-10-03:
- **User-level hooks** in `~/.claude/settings.json`: PreToolUse `Bash` → `~/.claude/hooks/rtk-rewrite.sh`; PreToolUse `Grep|Glob|Read|Search` → `~/.claude/hooks/cbm-code-discovery-gate`; SessionStart `startup`, `resume`, `clear` and `compact` → `~/.claude/hooks/cbm-session-reminder`. The same file sets `"model": "fable"`.
- **The user-level copies share the shipped copies' identity.** The user-level gate keys the SAME file name — `GATE=/tmp/cbm-code-discovery-gate-$PPID` (`~/.claude/hooks/cbm-code-discovery-gate:5`) — and the user-level reminder opens with the same `CRITICAL - Code Discovery Protocol:` line.
- **rtk.** `~/.claude/CLAUDE.md` imports `RTK.md` (`@RTK.md`), which describes rtk as a *"Token-optimized CLI proxy (60-90% savings on dev operations)"*. ⚠ **rtk is documented as compressing dev-operation output; which command families its rewrite covers — and so how much of arm B's Bash output it would touch — was not verified.**
- **A user-level skill,** `~/.claude/skills/codebase-memory/SKILL.md`, whose description opens *"Use the codebase knowledge graph for structural code queries."*
- **A user-level MCP registration:** `~/.claude.json`'s top-level `mcpServers` carries a `codebase-memory-mcp` entry. The CBM server's own instructions, as shown to a session in this repository on 2026-10-03, open *"Graph first: search_graph for symbols, trace_path for relationships"*.
- **Other user-level settings that can move output length.** The same `~/.claude/settings.json` sets `"defaultMode": "auto"` (permission mode), `"language": "uk"` (response language), `"alwaysThinkingEnabled": true` and `"effortLevel": "xhigh"`, and its `modelSettings` block carries a per-model override, `"claude-opus-5-5": { "effortLevel": "xhigh" }` (`~/.claude/settings.json:69`–`:71`) — written here as it appears in that user-level key. Only the override keyed to the model the pinned alias resolves to applies to a run (C11): with a pin on that model's alias the per-model override is in force, and with a pin on a different alias the top-level `effortLevel` is — either way, the value in force is recorded in the pre-registration block. The same file also sets `"autoUpdatesChannel": "latest"` (`:74`), so Claude Code updates itself (D7, C10). D7's window leaves the output-moving settings on; the pre-registration block records them.
- ⚠ **Contamination of the existing evidence.** Hook entries merge across settings levels (C1), so every session in which these user-level entries were present ran them beside the project's own. `~/.claude/settings.json` is not under version control, and **whether these entries were present during the diagnosis's window (2026-08-28 – 2026-09-28) is NOT verified here.** If they were, every transcript the diagnosis measured carried rtk-compressed Bash output and the user-level CBM nudges. D7 controls this going forward; nothing can repair it backward.

**E11 — What exists to measure with.**
- **The profiler.** `.devforge/lib/profile_helper` has the verbs `run` (`--transcript`, `--dir`, or the auto-located latest transcript) and `aggregate` (grep `_SUBCOMMAND_REGISTRY`, `src/devforge/lib/_profile/_cli.py:159`). It gives the per-segment LLM / Bash / Task / Human / AgentBusy split (diagnosis `:32`–`:33`), and `run` writes `.devforge/profile/` unless `--no-store` (`_cli.py:10`–`:11`). **It reports neither bytes per tool family nor tokens** — hence D8.
- **The profiler's test builders** (`tests/lib/_profile/_fixtures.py`) are hand-authored line builders, and their module docstring calls that *"the documented exception"* to the repo's round-trip-via-the-real-producer testing discipline (`:9`–`:10`), because no producer of a transcript exists in a test sandbox. They write a `version` field on every transcript line they build (`:39`) and no `usage` field. D8 weighs them.
- **The maintainer-script precedent.** `scripts/lib/memory_lane.py` + `scripts/verify-memory-lane.py` + `tests/lib/test_memory_lane.py` (`CLAUDE.md`'s `## Where to find what` row "Memory-lane coverage gate"). Plan 126's D7 proposes the first maintainer script that spends tokens, and records the COUNTER *"Maintenance and cost of a harness nobody runs."*
- **The model-alias convention.** `scripts/lib/model_version_tripwire.py:5`–`:7` (the quote wraps across those lines; grep `makes the framework's model choice VERSION-FREE`): *"`src/` stores only Claude Code aliases (`opus`, `sonnet`, `haiku`, `fable`) or a consumer-owned pin, never a priced, dated, version-bound model identifier."* The tripwire scans `src/` only (`:177`), so a plan or a script under `scripts/` is outside its scan; this plan follows the convention anyway, as plan 126's OQ-2 does.

**E12 — The two generations.**
- **v2** = `develop-2.0-init` at the commit Phase 1 records at install time. `src/manifest.json:2` reads `"version": "2.0.12"` on 2026-10-03, and `install.sh` stamps that manifest version into `.claude/template-version` (grep `template-version`, `install.sh:477`). ⚠ **The stamp is a version string, not a commit:** two installs from different commits can carry the same stamp, so Phase 1 records this repository's `git rev-parse HEAD` separately.
- **v1** = branch `main` at `9eeff96`, dated 2026-04-14 — verified by the orchestrator on 2026-10-03 with `git log -1 --format='%h %ad' --date=short main`. The diagnosis took v1's static weight from `git ls-tree main` (`:50`).

**E13 — Install-root facts the session protocol depends on.**
- **`.devforge/index.json` carries an ABSOLUTE path:** `src/devforge/lib/index_helper.py:852` writes `"project_root": str(project_root.resolve()),`. A file copied from one install root into another can name the first root (Phase 1, Trap 10).
- **Storage classes.** `research-state.json`, `research-report.json` (`src/devforge/storage-rules.md:112`–`:113`), `.preflight-stamp`, `cbm-last-indexed-sha` (`:114`) and `cbm-usage.log` (`:115`) are EPHEMERAL and gitignored (`src/files/devforge.gitignore:4`–`:11`). `.devforge/lib/`, `bin/`, `templates/` and `command-refs/` are the untracked CODE class (`devforge.gitignore:17`–`:20`), so `git clean -x` deletes them.
- **Scratch ≠ record.** *"Scratch ≠ record — do not conflate."* (`storage-rules.md:132`): the scored RECORD is `specs/<feature>/research-report.md`; `.devforge/research-report.json` is EPHEMERAL run state that shares its name (`:134`).
- **A confirmed save mutates the repository.** It allocates `specs/<YYYY>/<MM>/<leaf>/`, creates `spec/<ticket>` or `spec/<feature-slug>` when the run is on the repository's default branch, and `[WIP]`-commits the artifacts (`research/main.md:11`, `:26`, `:30`). On any other branch no checkout is emitted (`:1427`). A tier-1.5 probe script lives in `${TMPDIR:-/tmp}/forge-research` (`:1048`).
- **CBM outside MCP.** The CBM index is keyed by the absolute repo path (`_preflight.py:353`), and the binary has a `cli` mode (`:356`), so a Bash command can query CBM without any MCP call.
- ⚠ **Not verified:** whether, after `git reset --hard` removes a run's saved report, the CBM index still holds nodes for it. The Phase 2 dry run checks (Trap 11).

**E14 — The frozen benchmark install.** An older-version client install is frozen for benchmark runs. **It is NEVER touched by this plan:** no `install.sh` or `update.sh` run against it, no edit, no session in it, no message to its sessions. No identifier of it — and no client identifier of any kind — enters this plan.

### Claude Code facts from the consult (2026-10-03)

The orchestrator's `claude-code-guide` consult on 2026-10-03 returned the items marked *(consult)*. This draft's author re-fetched each URL the same day with WebFetch, which produced two corrections to the consult (C1's hook-merge sentence, C2's model-on-resume sentence) and the items C5–C8. The orchestrator then routed every WebFetch-only item through `claude-code-guide` on 2026-10-03, and each item carries its verdict below; C9–C12 come from that check and its later rounds. ⚠ **Settled — do not re-open:** a first `claude-code-guide` pass mis-read C1's hook merge, C5's shell and C8's SDK answers as undocumented or conflicting; a second, targeted pass the same day fetched the exact sections, quoted them verbatim, and confirmed the WebFetch reading on all three. **The facts no source documents and the runs depend on — the process behind `$PPID` in a hook script (C5), the transcript fields carrying the model and the Claude Code version (C2, C10), and how a compaction shows in a transcript (C12) — are observed in the Phase 2 dry run, never assumed.**

- **C1 — Settings precedence and hooks.**
  - *(consult)* Highest to lowest: managed, command line `--settings`, `.claude/settings.local.json`, `.claude/settings.json`, `~/.claude/settings.json`; *"A key set at a higher level overrides the same key set lower down."* — https://code.claude.com/docs/en/settings.md .
  - *(`claude-code-guide`, 2026-10-03)* `--settings` merges with the files: *"Values you set here override the same keys in your `settings.json` files for this session. Keys you omit keep their file-based values."* — https://code.claude.com/docs/en/cli-reference.md . hooks.md documents `disableAllHooks` as the switch that turns hooks off: *"To turn hooks off for one run whatever the project's settings say, pass `--settings '{"disableAllHooks": true}'`"* — https://code.claude.com/docs/en/hooks.md .
  - ⚠ **Hook entries MERGE across levels — VERIFIED through `claude-code-guide` on 2026-10-03 (targeted section fetch), correction 1 of 2 to the consult.** hooks.md, section "Hook locations": *"Hook entries merge across settings levels rather than replacing each other: user, project, and local settings add their own hooks without removing managed ones, and the `disableAllHooks` setting can't disable managed hooks from outside managed settings."* — https://code.claude.com/docs/en/hooks.md . **A project's `.claude/settings.json` therefore cannot drop a user-level hook** (D7).
  - ⚠ **`CLAUDE_CONFIG_DIR` — VERIFIED through `claude-code-guide` on 2026-10-03 for relocation.** *"When set, `CLAUDE_CONFIG_DIR` changes the root directory for: Settings files, Credentials, Projects directory, Plugins and other configuration data"* — https://code.claude.com/docs/en/env-vars.md . Whether a project's own `.claude/settings.json` hooks still load under a fresh config directory is NOT explicitly documented.
- **C2 — Model pin.**
  - *(consult)* `claude --model <alias|name>` at startup, or the `"model"` key in a settings file — https://code.claude.com/docs/en/model-config.md .
  - ⚠ **WebFetch-only; re-verified through `claude-code-guide` on 2026-10-03 — VERIFIED; the field name is NOT documented (correction 2 of 2 to the consult,** which found the model's presence in a transcript undocumented). The sessions page lists, among what a resumed session restores, *"Model: the session continues on the model it was using."* — https://code.claude.com/docs/en/sessions.md . A transcript therefore carries the model in some form; which entry field holds it is internal (C3), and Phase 2 records it.
- **C3 — Transcripts** *(consult)*. `~/.claude/projects/<project>/<session-id>.jsonl`, where `<project>` is the working directory with non-alphanumeric characters replaced by `-`; *"The entry format is internal to Claude Code and changes between versions, so scripts that parse these files directly can break on any release."* — https://code.claude.com/docs/en/sessions.md#where-transcripts-are-stored . Subagent transcript storage is not documented there; it is observed on this machine as `<session>/subagents/*.jsonl` (E3).
- **C4 — Hooks** *(consult)*. A PreToolUse exit 2 *"Blocks the tool call"*, and when the hook returns no JSON reason — the shipped hooks return none — the block reason reaching the model is the hook's stderr; `${CLAUDE_PROJECT_DIR}` is the documented project-root variable; SessionStart matchers are `startup`, `resume`, `clear`, `compact` and `fork` — https://code.claude.com/docs/en/hooks.md .
- **C5 — How a hook process is spawned.** ⚠ **VERIFIED through `claude-code-guide` on 2026-10-03 (targeted section fetch).** hooks.md, section "Exec form and shell form": *"Shell form runs when `args` is absent. The `command` string is passed to a shell: `sh -c` on macOS and Linux, Git Bash on Windows, or PowerShell when Git Bash isn't installed. Set the `shell` field to choose explicitly."* — https://code.claude.com/docs/en/hooks.md . The shipped entries carry no `args` (E9), so they run in shell form under `sh -c` on macOS and Linux. ⚠ **The process behind `$PPID` in the script stays UNDOCUMENTED** — every source agrees — and the shipped gates' once-per-session behavior depends on it; the dry run settles it by counting gate fires per gate (D8, Trap 1).
- **C6 — Auto memory.** ⚠ **WebFetch-only; re-verified through `claude-code-guide` on 2026-10-03 — VERIFIED.** Stored per project under `~/.claude/projects/<project>/memory/`, loaded into every session in that project (*"first 200 lines or 25KB"*); off via `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` — https://code.claude.com/docs/en/memory.md . **A note one run writes would load into the next run in the same install root** (D7, Trap 12).
- **C7 — The user-level `CLAUDE.md`.** ⚠ **WebFetch-only; re-verified through `claude-code-guide` on 2026-10-03 — VERIFIED.** `~/.claude/CLAUDE.md` loads in every project, and its `@path` imports are expanded at launch — https://code.claude.com/docs/en/memory.md .
- **C8 — Answering `AskUserQuestion` programmatically.** ⚠ **VERIFIED for the Agent SDK through `claude-code-guide` on 2026-10-03 (targeted section fetch); UNDOCUMENTED for headless runs.** agent-sdk/user-input, step "Return answers to Claude" under "Handle clarifying questions": *"Build the `answers` object as a record where each key is the `question` text and each value is the selected option's `label`"* — https://code.claude.com/docs/en/agent-sdk/user-input.md . The `canUseTool` callback returns that object. What a headless `claude -p` run does on `AskUserQuestion` is documented nowhere (https://code.claude.com/docs/en/headless.md). D6's rejection of a programmatic operator rests on other reasons.
- **C9 — An MCP server defined at two scopes** *(`claude-code-guide`, 2026-10-03)* — VERIFIED. *"When the same MCP server is defined in multiple places, Claude Code connects to it once using the definition from the highest-precedence source. The entire server entry from that source is used; fields are NOT merged across scopes."* A project's `.mcp.json` outranks the user's `~/.claude.json` — https://code.claude.com/docs/en/mcp.md . So in both arms the install's `.mcp.json` definition of `codebase-memory-mcp` is the one used (OQ-9).
- **C10 — The Claude Code version: auto-update, reading and pinning** *(`claude-code-guide`, 2026-10-03)* — VERIFIED.
  - Auto-update off: *"Set `DISABLE_AUTOUPDATER` to `"1"` in the `env` key of your `settings.json` file"* — https://code.claude.com/docs/en/setup.md#disable-auto-updates . The stronger `DISABLE_UPDATES` blocks every update path, manual `claude update` included. `autoUpdatesChannel` takes `latest` (the default) or `stable`.
  - Reading and pinning: `claude --version` prints, for example, `2.1.89 (Claude Code)`; a specific version installs with `curl -fsSL https://claude.ai/install.sh | bash -s <version>`; native installs keep versions under `~/.local/share/claude/versions/`; the `minimumVersion` setting is a floor, not a pin — https://code.claude.com/docs/en/setup.md#install-a-specific-version .
  - ⚠ **Whether the Claude Code version is written into a transcript is NOT documented** — C3's internal-format sentence is all the docs say. D8 reads it from a transcript only if present; **the operator's per-run `claude --version` record is the version of record** (D7).
- **C11 — Per-model settings overrides** *(`claude-code-guide`, 2026-10-03)* — VERIFIED. *"Claude Code writes each entry under the model's canonical name (e.g., …), but the override applies when the session runs on: That model's alias, Date-suffixed versions, `[1m]` variants, Recognized provider-specific IDs"*, and *"An `effortLevel` in `modelSettings` takes precedence over the top-level `effortLevel` in the same settings file"* — https://code.claude.com/docs/en/settings-reference.md . Consequence for E10's override: a pin on that model's alias runs with the per-model value; a pin on a different alias runs with the top-level `effortLevel`.
- **C12 — `/compact` and how a compaction shows in a transcript** *(`claude-code-guide`, 2026-10-03)*.
  - ⚠ **VERIFIED through `claude-code-guide` on 2026-10-03:** sessions.md lists *"`/compact [instructions]`: replace history with a summary, optionally focused on what you specify"*, and describes it as one summarization request over the full history, after which later requests carry the summary instead of the history — https://code.claude.com/docs/en/sessions.md .
  - ⚠ **UNDOCUMENTED:** no event kind, marker or entry type is documented for detecting a compaction in an on-disk transcript — C3's internal-format sentence is all the docs say. **D8's compaction definition, frozen at Phase 2, therefore comes from what the dry run or the conditional probe OBSERVES in a transcript;** that is the reason the probe exists.

---

## Decisions to ratify

Nothing below is ratified. Each item states the decision, a **RECOMMEND** with its reason, and the strongest counter-argument, **COUNTER, at full strength — recorded honestly rather than answered away.**

### D1 — What is compared (the reframe)

**The decision.** Which two configurations the two identical repos carry.

**The reframe.** The maintainer's sketch was *"two identical repos with identical tasks, v1 vs v2 for measurements."* **"Two identical repos with identical tasks" is kept exactly. "v1 vs v2" is reframed: the arm variable is the DISCOVERY TOOL within one forge generation (v2), NOT the forge generation.** v1 and v2 differ at once in spec size (research loads ≈ 50 k tokens of prose at invocation, diagnosis `:323`), in mandated sweeps (*"nine sweeps marked MANDATORY"*, `:347`), in helper round-trips (32 helper calls per research run, `:301`), in the model and in the installs (E4). The diagnosis already measured that generation delta — on 92 + 1 v1 sessions and 10 + 5 v2 sessions (`:27`–`:28`) — and could not isolate CBM inside it. **A v1 arm is offered as optional Phase 6 (arm C, OQ-3); it answers the generation question, not this one.**

**RECOMMEND:**
- **Arm A — v2 AS SHIPPED:** an install of one recorded `develop-2.0-init` commit, with the emitted research command and all five shipped hooks unchanged.
- **Arm B — the SAME commit and the SAME install procedure, with exactly two deltas:**
  - **(i)** the four CBM-steering hooks removed from the install's `.claude/settings.json` — `cbm-code-discovery-gate`, `bash-ban-raw-tools`, `cbm-session-reminder`, `cbm-sync-session-start` — with `cbm-mcp-marker` KEPT as the leak detector. This is the switch the installed `CLAUDE.md` documents (E9).
  - **(ii)** the emitted `.claude/commands/devforge/research.md` rewritten by the MECHANICAL mapping table below. **Sweep count and order are UNCHANGED; only the tool each step names changes.**

| CBM call (arm A) | File-tool substitute (arm B) |
|---|---|
| `search_graph(name_pattern\|qn_pattern)` | `Grep` for the definition pattern of the symbol (`function X`, `const X =`, `class X`, `export … X`) over source files, `-n` |
| `search_code(pattern)` | `Grep` with the same literal/regex, output mode content, `-n`, no head limit beyond the tool's default |
| `trace_path(X, mode=calls)` | `Grep` for `\bX\(` project-wide excluding the definition file, then `Read` of each hit's enclosing function (this IS caller enumeration by hand — the place CBM is expected to win) |
| `get_code_snippet(qualified_name)` | `Read` with offset/limit around the `file:line` a Grep row gave |
| `get_architecture` / `get_file_outline` / `query_graph` | `Glob` plus `Read` of file heads / `docs/` overview |
| *(row added by this draft)* `search_graph(label="File", name_pattern=<regex on file_path>)` — used by the pre-rubric docs scan (`:260`) and Phase 2.2 (`:392`) | `Glob` on the same path pattern, then `Read` of the matched file |
| *(row added by this draft)* `trace_path(X, mode=calls, direction=outbound)` — used by Phase 2.4d (`:691`) | `Read` of X's body, then `Grep` for the definition of each function it calls |
| *(row added in review)* `trace_path(X, mode=data_flow, …)` — named at `:407`; used with `direction=outbound` at `:626` and `:755` | `Grep` X's identifier forward — assignments and call arguments — then `Read` each site |
| *(row added in review)* `trace_path(X, mode=cross_service)` — named at `:407` | `Grep` across package boundaries for the symbol or route string, then `Read` each hit |
| *(row added in review)* `search_graph(label=Method\|Function\|Class, qn_pattern=…)` — `:518`, `:601` | `Grep` for the definition pattern of the symbol, scoped to the class or file the qualified name names, `-n` |

- **The `file:line` grounding rule keeps its meaning, with Grep rows as the source.**
- **Plan 124's item 2 (the diagnosis's L2 change (c)) is NOT pre-applied in either arm.** Neither arm caps `search_code` or `Grep` output beyond its tool's default, and neither pins `mode=compact` or `max_output_tokens`: those are proposed changes (E6), owned by plan 124 (D10). The shipped spec sets no limit on 2026-10-03, and the recorded runs passed `limit` 30–60 (E2). ⚠ **This bullet, the mapping table and the rest of D1 describe `research/main.md` on 2026-10-03; if plan 123 or 124 lands before Phase 1, D1 is re-ratified against the installed commit** (the ⚠ paragraph above E7).
- **An unmapped CBM call shape found while writing the arm-B file is a Phase 1 STOP:** a row is added and D1 is re-ratified before the freeze.
- **Every sentence that names a CBM tool as a step's path is mapped by the table, and nothing else in the file changes except as the next bullet states.** The four ban sentences (E7) become their inverse: file tools are the sanctioned path, and CBM tools are not called. Phase 2.1's question keeps its estimate rule and its options, and its wording names discovery calls instead of CBM calls. Phase 0.2 follows OQ-4.
- **Helper-enforced literals stay as they are.** The arm-B file keeps `--verified-via search_code` (`:616`–`:619`) unchanged, because the helper accepts only `trace_path` and `search_code` (E7) and changing that is a `src/` edit, which D10 forbids. In arm B that value then labels a Grep-derived confirmation with the only accepted non-graph value. Likewise `declare-caller-total`, whose total the helper defines as a `trace_path` row count (E7), receives a Grep-derived caller count in arm B. Every helper-verb invocation in the file stays byte-identical.
- **The arm-B file is produced by instruction-author → instruction-reviewer from the emitted arm-A file**, and its unified diff against arm A is recorded in `#### Phase 1 record`, so arm B is reproducible with `patch`.

**Why.** It holds everything but the discovery tool fixed — the commit, the spec's sweeps, the helpers, the model, the fixture and the tasks — so a difference between arms is the tool's.

**COUNTER, at full strength.**
- **The maintainer said v1 vs v2.** This plan answers a narrower question than the one sketched; arm C (Phase 6) is the sketched one, and it stays optional.
- **Arm B measures "the same sweeps with file tools", never "the best file strategy".** The sweeps were written for a graph. A grep discipline designed from scratch could do better or worse, and nothing here measures it (`## Honest bounds`).
- **Arm B is a counterfactual nobody ships.** Its spec is a mechanical rewrite, and it still carries the CBM steering OQ-9 lists.
- **The mapping is one author's judgment.** A different `trace_path` row would move T2's result. Freezing the rows at Phase 2 stops them being tuned to a result; it does not make them neutral.
- **The tools' own defaults are an asymmetry neither arm controls.** The `Grep` tool's default output shape and each CBM tool's default limits are tool-level choices (the diagnosis records `search_code`'s default `limit` as 10, `:370`). The comparison is of the tools as their defaults ship, plus whatever arguments the model passes — recorded per call (D8), never equalized.

### D2 — The measured command: `/devforge:research` only

**RECOMMEND `/devforge:research` alone.**
- **It carries the CBM volume.** In the diagnosis's §2.1 table research carries 45 CBM calls per run, while specify, plan, grill and configure each carry 0 (`:301`–`:307`).
- **One transcript holds its whole cost.** It dispatches no agent (E7).
- **Its output is scoreable.** The saved report and handoff name affected areas and findings with `file:line` (D4's answer key scores against them).

**COUNTER, at full strength.** Eleven other files under `src/commands/` name `search_graph`, `trace_path`, `search_code` or `mcp__codebase-memory-mcp` (grep, 2026-10-03) — among them `/devforge:implement`, `/devforge:generate-docs`, `/devforge:audit`, `/devforge:pr-review`, `/devforge:discover` and `/devforge:specify` — and plan 115 names *"every CBM-backed step (generate-docs, glossary, research, implement)"* (`115-WRAPPER-INNER-REPO-CBM-VISIBILITY-PLAN.md:8`). **None of them is measured:** that is a follow-up, not this plan. And research is where CBM's share is largest, so this result bounds one command, never the pipeline.

### D3 — The fixture

**RECOMMEND ONE public open-source repository, cloned TWICE at ONE pinned commit into two sibling directories, each an install root in STANDALONE mode.** Not wrapper mode: wrapper adds plan 115's CBM-visibility problem and a second repository.

**Selection criteria the maintainer applies (OQ-1 picks):**
- a language the CBM indexer supports AND `bash-ban-raw-tools` matches (E9) — TypeScript / Vue preferred: research's Phase 2.3 names Vue `<script setup>` and React hooks among the shapes `search_code` exists to catch (`research/main.md:406`), and `ts`, `tsx` and `vue` are in the gate's extension list;
- roughly 20–80 k lines;
- at least one shared helper reached from ≥ 2 entry points through different intermediate functions — the benchmark's shape, where `trace_path` earned its credit (E2);
- a runnable test suite;
- a permissive license;
- no client material;
- *(added by this draft)* no top-level `specs/` directory, so the research save's `specs/<YYYY>/<MM>/<leaf>/` lands in an empty tree and the reset (D6) never meets fixture content there.

**COUNTER, at full strength.** A public repository is not the maintainer's consumer codebases, so the result transfers only as far as the fixture resembles them. **One fixture binds the result to one codebase shape.**

### D4 — Tasks: THREE research topics, pre-registered

**RECOMMEND three tasks:**
- **T1 — bug-shaped, one place.**
- **T2 — enhancement-shaped, feature-wide, whose correct answer REQUIRES enumerating every caller of the fixture's shared helper** — the task where CBM is expected to win.
- **T3 — a hardcoded-literal change, cross-cutting,** which triggers Phase 2.5b literal archaeology (`:841`).

**For each task, the pre-registration block in `## Measurement record` carries:**
- **the topic text** passed as `$ARGUMENTS`;
- **the ANSWER KEY** — the set of `file:function` sites a correct research must name, authored by the maintainer by READING THE CODE before any run;
- **the OPERATOR SCRIPT** — the exact reply to every question in E8:

| Question (E8) | Scripted reply |
|---|---|
| 2 — Phase 0.5 interpretation | `confirm` |
| 3 — design reference | `none` |
| 4 — `scope` | T1 `one place`; T2 `feature-wide`; T3 `cross-cutting` |
| 4 — the five free-text dimensions | fixed text per task; **T1's `affected_area` text carries one fixed `file:line` of the symptom site**, authored with the answer key, because `--evidence` is REQUIRED as a real `file:line` when `scope` is `one place` (`:293`) |
| 5 — narrow-framing citation follow-up | `you decide`, recorded as a deviation — the scripted T1 citation is meant to make this prompt never fire |
| 6 — conflict | the option whose text is the script's answer for that dimension |
| 7 — drift note | `continue` |
| 8 — mode | T1 `bug`; T2 `enhancement`; T3 fixed per task |
| 9 — coverage echo | accept gaps |
| 10 — Phase 2.1 | `proceed` |
| 11 — Phase 2.4d fallbacks | `you decide`, recorded as a deviation |
| 12 — Step 4.1, question 1 | the task's fixed slug, typed into the free-text row (OQ-5) |
| 12 — Step 4.1, question 2 | `No ticket` |
| 13 — Step 4.2 ticket re-ask | STOP — the run is VOID (the ticket requirement was not turned off in Phase 1) |
| any question not in this table | `you decide`, recorded as a deviation |

**Same text and same answers in both arms.** **Every `you decide` reply is a recorded deviation:** a hand-back makes the model supply the content itself, and the discovery calls it spends to do so fall inside the measure and can differ by arm (`## Honest bounds`). All of it is written into the plan BEFORE the first scored run, in the shape of plan 126's D1 element 7 (pre-registration), and frozen at the end of Phase 2.

**Recall, the outcome measure.** An answer-key site counts as NAMED in a run when the saved `research-report.md` or `research-handoff.json` names both its file path and its function. Scoring is mechanical first — both strings in one finding, affected-area or caller entry — and then a read of every saved report confirms or reclassifies each site, with the reason recorded for every reclassification (plan 126 D1 element 6's shape). **Recall = named sites ÷ key sites.**

**COUNTER, at full strength.** Three tasks are three codebase shapes, not a distribution. **T2 is chosen to favour CBM and T3 to favour text search.** The per-task split is reported so the bias is visible, and D9 requires all three tasks to agree. The operator also authored the answer keys, so it is the script — not the operator's blindness — that keeps the key out of the answers.

### D5 — N and order

**RECOMMEND N = 3 per cell: 3 tasks × 2 arms × 3 = 18 scored runs, plus 1 dry run per arm on T1 (Phase 2) — 20 runs in all, plus at most one short probe session, only if neither dry run compacts (D8's compaction definition).** Runs go in task pairs, both arms back to back, with the task order rotated per repetition and the opening arm counterbalanced per task as far as N = 3 allows, so time of day and model drift fall on both arms:

| Pair | Rep | Task | Order |
|---|---|---|---|
| 1 | 1 | T1 | A, B |
| 2 | 1 | T2 | B, A |
| 3 | 1 | T3 | A, B |
| 4 | 2 | T2 | A, B |
| 5 | 2 | T3 | B, A |
| 6 | 2 | T1 | B, A |
| 7 | 3 | T3 | A, B |
| 8 | 3 | T1 | A, B |
| 9 | 3 | T2 | B, A |

Arm A opens a pair twice for T1 and T3 and once for T2; with three repetitions per task, one arm opens twice.

**VOID re-runs.** A run that is VOID (a run-level tripwire, D9's Run VOID row) keeps its row, and its re-run is appended after pair 9, the re-runs in pair order. **The cost, named:** an appended re-run falls later in the series and outside the counterbalanced order, so its cell loses part of the balance this table buys. More than 2 VOID runs in one cell (task × arm) stop the series for the maintainer's review (`## Tripwires`).

**COUNTER, at full strength.**
- **N = 3 gives counts, not rates.**
- **N = 5 roughly doubles the cost:** 30 scored runs.
- **The cost is large.** The diagnosis measured 30–68 main-thread LLM minutes per v2 research run on the benchmark (`:83`) and 23 on client install D (`:205`), with a median of 12 stops for the human per run (`:105`). **18 scored runs are ≈ 7–20 hours of main-thread model time — this plan's arithmetic, 18 × 23–68 LLM minutes — EXCLUDING the human's answering time,** with an operator present for every stop, billed to the maintainer. OQ-7 records the real number after the dry run.

### D6 — Session protocol: one run is one fresh process

**RECOMMEND, for every run, in the install root:**

**Before the run.**
1. Delete `/tmp/cbm-code-discovery-gate-*` and `/tmp/bash-ban-raw-tools-*`, so arm A's gates fire identically every run (Trap 1).
2. Delete `.devforge/.preflight-stamp`, so Phase 0.2 runs in both arms and its cost is reported on its own row.
3. Truncate `.devforge/cbm-usage.log`.
4. Delete `${TMPDIR:-/tmp}/forge-research`.
5. Confirm `git rev-parse HEAD` is the baseline commit, `git status --porcelain` is empty, `.devforge/lib/cbm_sync_helper check` prints `current`, the D7 window is in force, and no auto-memory file exists for this root (C6).

**The run.** Start `claude --model <alias>` fresh in the install root, with `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` in its environment (D7) — never `--continue`, never `--resume`. Type `/devforge:research "<topic>"`. Answer from the operator script only. Let Phase 4 save. Exit.

**After the run.**
1. Record the session id (the transcript's file stem) and the transcript path. Copy the transcript, any `<session>/subagents/` folder (none is expected — research is inline) and `.devforge/cbm-usage.log` into the measurement folder (OQ-8).
2. Score the saved `specs/<…>/research-report.md` and `research-handoff.json` against the answer key (D4).
3. **Reset the install root to its baseline:** `git checkout <baseline-branch>`; delete any `spec/*` branch the run created; `git reset --hard <baseline-commit>`; `git clean -fd -- specs/`; remove the EPHEMERAL `.devforge/research-state.json`, `.devforge/research-report.json`, `.devforge/session-state.md` and `.devforge/.preflight-stamp`. Keep `.devforge/cbm-last-indexed-sha`. **Never `git clean -x`**, which deletes the untracked CODE class `.devforge/lib` (E13), **and never `rm -rf specs/`.**
4. Confirm `git status --porcelain` is empty and `HEAD` is the baseline commit.

**Blind operator.** Every content question is answered from the script, never from judgment.

**COUNTER (operator), at full strength — a human is in the loop.** **A programmatic operator is documented for the Agent SDK:** an `AskUserQuestion` call reaches the `canUseTool` callback, which returns an `answers` object (C8). It is NOT recommended, for three reasons that do not depend on C8: research's five free-text dimensions are plain end-of-turn prose prompts, not `AskUserQuestion` calls (`:270`), so a harness must recognise which prompt it is facing before it can pick the scripted reply — the judgment the human operator spends; whether an SDK session loads an install's project settings, hooks and slash commands the way the interactive CLI does is not verified here; and consumers run the interactive CLI. **An SDK harness is recorded as the rejected alternative**, re-openable if the operator's time becomes the binding cost. Headless `claude -p` is rejected with it — what it does on `AskUserQuestion` is undocumented (C8).

### D6b — Compaction handling

**The decision.** What a run whose context compacts counts as.

**Why it matters.** A compacting run carries a summary in place of its history from then on. In arm A the shipped reminder is injected again — `compact` is in the shipped SessionStart matcher (E9) — and so is the sync block, but only on a missing or drifted stamp (`src/hooks/cbm-sync-session-start:44`–`:49` exits silently on `current`, and Trap 13 keeps the stamp current). Arm B gets neither.

**RECOMMEND: a compaction is RECORDED, never void** — counted per run (D8) and reported per arm — because a research run that compacts is what a consumer gets.

**COUNTER, at full strength.** A series free of that asymmetry would VOID every compacting run, at the cost of re-runs that may compact again.

### D7 — Contamination control

**The decision.** How the machine-level steering in E10 is kept out of both arms.

**RECOMMEND option (a), verified by the Phase 2 dry run.** ⚠ **(a) is NECESSARY, not merely preferred:** hook entries merge across settings levels (C1), so nothing an install's project settings say can drop a user-level hook — only stripping the user file does.
- **(a) A run window, opened per phase.** Back up `~/.claude/settings.json` and `~/.claude/CLAUDE.md`; remove the `hooks` block from the first and the `@RTK.md` import from the second; move `~/.claude/skills/codebase-memory/` aside; run every run of a phase inside that window; at the phase's close, restore those three and confirm each restored file equals its backup byte for byte — **except the `DISABLE_AUTOUPDATER` key under `env` in `~/.claude/settings.json`, which the next bullet keeps set across phases.**
- **The Claude Code version is held fixed for the series — by an auto-update block that outlives the windows.** Auto-update is ON on this machine — `~/.claude/settings.json` sets `"autoUpdatesChannel": "latest"` (E10) — so a client update can land between runs spread over days, and Phase 3's build sits between the Phase 2 freeze and Phase 4. **`DISABLE_AUTOUPDATER` is set to `"1"` under `env` in the user settings (C10) before the first Phase 2 session and stays set through the last Phase 4 run;** only the hooks, the `@RTK.md` import and the skill are restored at each phase's close, and the key is removed after Phase 4's last run, when `~/.claude/settings.json` must equal its backup byte for byte. The `claude --version` output is recorded at the freeze in the pre-registration block, the operator records it in the run-log row of every run, and Phase 4's Verify checks it before run 1. **COUNTER:** the block keeps the maintainer's whole machine off auto-update for the days or weeks between Phase 2 and Phase 4. **The alternative:** remove the key with the rest at each phase's close, and at Phase 4's start re-record `claude --version` and re-freeze under a new `**Freeze record**` line — at the cost of scored runs on a CLI version the dry runs and the Phase 3 fixtures never saw. ⚠ On 2026-10-03 the machine ran `2.1.288 (Claude Code)` (the orchestrator's `claude --version`) — **the draft-time version, NOT the pin;** the pin is whatever the freeze records. *(Added in review.)*
- **And, in both arms, `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`** in the environment of every run (C6), so no run can leave a note the next run in the same root loads. *(Added by this draft.)*
- **rtk is OFF in both arms.** Consumer installs do not carry it, and it is documented as compressing dev-operation output (E10).

**Rejected or unverified alternatives:**
- **(b) `CLAUDE_CONFIG_DIR`** pointing at a fresh config directory. The docs relocate settings files, credentials, the projects directory and plugins under it (C1); whether a project's own `.claude/settings.json` hooks still load under a fresh directory is not explicitly documented, and whether starting without the current credentials forces a new sign-in is not documented either. The dry run would have to prove the install's hooks fire.
- **(c) `--settings '{"disableAllHooks": true}'`** — REJECTED. hooks.md names `disableAllHooks` as the switch that turns hooks off for one run (C1); its scope wording is the doc's, and on that wording it turns off arm A's shipped hooks too — and arm A is "as shipped".

**The dry-run checks** (Phase 2's Verify):
- arm A's transcript carries exactly one SessionStart-`startup` injection of the `CRITICAL - Code Discovery Protocol:` block — the shipped reminder alone, since the user-level copy opens with the same line (E10) — plus one per compaction (D6b); arm B's carries none;
- arm B has zero tool results containing `BLOCKED: For code discovery` (`cbm-code-discovery-gate`), zero containing `BLOCKED: Raw grep/find/cat` (`bash-ban-raw-tools`), and no text containing `The CBM (codebase-memory-mcp) index` (the sync hook's injection, `src/hooks/cbm-sync-session-start:52`, `:62`) — the removed hooks did not fire;
- no Bash call in either transcript carries an `rtk` token in its input or its result;
- no invocation of the user-level `codebase-memory` skill in either transcript;
- arm B's transcript has zero `mcp__codebase-memory-mcp__` tool uses, zero Bash commands containing `codebase-memory-mcp`, and its `cbm-usage.log` has zero `mcp__codebase-memory-mcp__` lines;
- no auto-memory file exists for either root after the run.

**COUNTER, at full strength.**
- **The window touches every Claude Code session on this machine.** While it is open, the maintainer's other sessions lose rtk, the user-level CBM nudges and the user-level `CLAUDE.md` import; and, separately from the window, they stay off auto-update from the first Phase 2 session through the last Phase 4 run; no other session should run during a window, and nothing enforces that.
- **What stays uncontrolled is the same in both arms:** the Claude Code system prompt, the machine's other MCP servers, and the user-level settings the window leaves on — permission mode (`"defaultMode": "auto"`), response language (`"language": "uk"`), `"alwaysThinkingEnabled": true`, `"effortLevel": "xhigh"` and the per-model effort override in `modelSettings` (E10). Each can move the Output measure; their values are recorded in the pre-registration block, identical across arms. **They are noise between the arms, not bias — but a consumer's values differ,** so they bound how far the Output figures transfer (`## Honest bounds`).

### D8 — The measurement module, kept in the repo

**RECOMMEND** `scripts/lib/transcript_metrics.py` (parser and metrics), `scripts/measure-transcripts.py` (entry: a folder of transcripts → one CSV or markdown table) and `tests/lib/test_transcript_metrics.py` — the memory-lane shape (E11) — **every function tested in the same turn it is written** (`CLAUDE.md`, "Test-immediately-after-write for python helpers"), built by python-engineer → python-reviewer.

**Metrics per transcript:**
- **tool calls by family** — CBM per verb; `Read` / `Grep` / `Glob`; Bash split into raw-read (`grep|cat|sed|find|head|awk`), `*_helper` and other; `AskUserQuestion`; other;
- **tool-result bytes per family** — the diagnosis's "bytes their results return into context" (`:296`), with the Phase 0.2 `generate_docs_helper preflight` result as its own row;
- **the arguments of every CBM call** — `limit`, `mode`, `max_output_tokens` (Trap 4);
- **gate fires, per gate** (defined below);
- **reminder injections** and **sync injections** — SessionStart injections of the `CRITICAL - Code Discovery Protocol:` block and of the sync hook's block, each counted per run (defined below);
- **compaction events per run** (count; D6b);
- **assistant output tokens**, deduplicated by `message.id`, max per id (E3);
- **cache-read tokens** at the median turn and at the peak;
- **assistant turn count;**
- **wall minutes and framework minutes** — human gaps subtracted, the diagnosis's §1 rule (E3);
- **the model**, from the field the Phase 2 dry run finds it in (C2), and **the Claude Code version** only if a transcript field carries it (C10; E11) — the operator's per-run `claude --version` record in the run log is the version of record (D7);
- **unknown event kinds are COUNTED and skipped, never fatal.** The module's docstring quotes C3's *"The entry format is internal to Claude Code and changes between versions"*.

**Where each metric is recorded.** Wall and framework minutes go in the run log; the per-family and per-verb figures in the split table; the `AskUserQuestion` count, the per-call CBM arguments, the unknown-event count and the model and version fields go in the report file's appendix (Phase 5), with no column in `## Measurement record`. All other D8 metrics are Results-table columns (Phase 5).

**Definitions, fixed at the freeze** (D9 uses them; the pre-registration block carries them, and editing one after the freeze voids the measurement):
- **Tool-result bytes** — the UTF-8 byte length of a tool result's text content. Error results are included. Non-text content counts as 0 bytes, and the number of such results is reported.
- **Families** — the list under *tool calls by family* above.
- **The `Grep` family** — the `Grep` tool plus Bash raw-read commands (`grep|cat|sed|find|head|awk`).
- **Gate fire** — a tool result whose text CONTAINS one gate's distinguishing string: `BLOCKED: For code discovery` for `cbm-code-discovery-gate` (`src/hooks/cbm-code-discovery-gate:13`), `BLOCKED: Raw grep/find/cat` for `bash-ban-raw-tools` (`src/hooks/bash-ban-raw-tools:18`); each gate its own count. **NEVER a bare `BLOCKED:`:** research's own preflight prints *"BLOCKED: /devforge:research requires the full 4-command setup chain."* (`src/devforge/lib/_research/_cmds_basic.py:154`; documented at `research/main.md:49`), and a bare count would conflate them. Contains-matches, not prefix matches, because how a hook block is framed in a transcript is recorded in Phase 2, not assumed.
- **Reminder injection** — a SessionStart injection whose text contains `CRITICAL - Code Discovery Protocol:`; **sync injection** — one whose text contains `The CBM (codebase-memory-mcp) index`.
- **Output deduplication** — assistant messages deduplicated by `message.id`, the max `output_tokens` per id taken (E3).
- **Compaction** — an event of the kind that marks a compaction in a transcript. No such kind is documented (C12), so it is named in this definition before the freeze from what a transcript is OBSERVED to carry: a dry-run transcript that compacted, or — when neither dry run compacts — ONE probe session in install A in which the operator types `/compact` (C12), logged with Kind = probe and counted in D5 and OQ-7. If the observed transcript carries no event that marks the compaction, that is recorded, and Phase 2 STOPS until the definition is re-designed before the freeze.

**A frozen definition Phase 3 cannot implement.** Phase 2 applies every definition by hand to a dry-run transcript before the freeze (Phase 2's Verify), so that each is known to produce a number. If Phase 3 still finds a frozen definition unimplementable, that is a **Measurement VOID declared before any scored run**: the definition is rewritten, and the block is re-frozen under a NEW entry in `**Freeze record**` — a new SHA, with the old one kept there and marked superseded. **A definition is never re-defined silently.**

**Test fixtures are REDACTED EXCERPTS of the Phase 2 dry-run transcripts** — production shapes, per `CLAUDE.md`'s rule that tests use *"input shapes matching what the function will receive in production"*, never hand-invented JSON. The redaction strips the home path and every token naming the maintainer or the machine, checked by a grep before commit; the fixture repository is public, so no client identifier can enter. **Therefore Phase 3 comes AFTER Phase 2.**

**COUNTER, at full strength.**
- **Plan 126 D7's: "Maintenance and cost of a harness nobody runs."** The diagnosis kept its scripts scratch, and the parser this plan keeps is bound to one CLI version by the docs' own statement (C3). The answer recorded: the diagnosis's two scratch scripts are not in the repo (E3), so nobody can re-run its measurement, and this plan is paying for that.
- **Committed transcript excerpts are a first.** No `.jsonl` file exists under `tests/` on 2026-10-03, every excerpt carries redaction risk, and every excerpt binds a test to one CLI version's format. **The alternative, NOT recommended:** hand-authored builders, the shape `tests/lib/_profile/_fixtures.py` documents as *"the documented exception"* (E11). Those builders carry no `usage` field, which every token metric here reads.

### D9 — The pre-registered decision rule

**The decision.** When this plan may say that CBM saves tokens. **This is the point of the plan.**

**The three measures, per run:**
- **Bytes** — tool-result bytes (defined in D8) summed over every family, with the Phase 0.2 preflight result excluded and reported on its own row.
- **Output** — assistant output tokens, deduplicated by `message.id`, max per id.
- **Recall** — answer-key recall (D4).

**RECOMMEND: the claim *"CBM saves tokens versus reading files in `/devforge:research`"* is SUPPORTED only if, on the median over N for EACH task, arm A has LOWER bytes AND LOWER output than arm B, AND arm A's recall is not lower on any task.** "Lower" is strict; a tie is not lower. Any other pattern is NOT SUPPORTED, and the per-family and per-verb split says where.

**Secondary, NOT decision-bearing: the per-verb split.** File tools substitute for every CBM verb in arm B, so arm B cannot be split by verb mechanically. The MIXED reading therefore compares arm A's per-verb figures with arm B's per-family totals: if `trace_path`'s value shows on T2 while `search_code` costs more than arm B's `Grep` family everywhere, the finding is "graph yes, text search no" — evidence for the diagnosis's L2(e), lifting the raw-grep ban (the decision plan 124's item 2 leaves open, E6), and for narrowing the shipped hook set.

**The outcome table — every row evaluated independently, stated BEFORE any run:**

| Outcome | Fires when | Recorded as | Where |
|---|---|---|---|
| **SUPPORTED** | Over the 18 non-VOID scored runs, neither NOT SUPPORTED row fires | *"In `/devforge:research` on <fixture> at <commit>, with <alias>, Claude Code <version> and CBM <version>, N = 3 per task: arm A (CBM as shipped) returned fewer tool-result bytes and fewer output tokens than arm B (the same sweeps with file tools) on the median of every task, at no lower answer-key recall. Counts, not rates."* | `## Measurement record`; the report file; one `CHANGELOG.md` `## [Unreleased]` line; a dated bullet in `124-PIPELINE-COST-REDUCTION-PLAN.md` under its lever 2 |
| **NOT SUPPORTED (bytes / output)** | On some task, arm A's median bytes or median output is not lower than arm B's | *"…arm A did NOT return fewer <bytes / output tokens> than arm B on <tasks>"* | as SUPPORTED, plus a new `FINDINGS.md` entry |
| **NOT SUPPORTED (recall)** | On some task, arm A's median recall is lower than arm B's | *"…arm A named fewer answer-key sites than arm B on <tasks>"* | as SUPPORTED, plus a new `FINDINGS.md` entry |
| **MIXED (graph yes, text no)** — secondary | T2's median recall is higher in arm A, AND on every task arm A's median `search_code` bytes exceed arm B's median `Grep`-family bytes (both as defined in D8) | *"the caller-enumeration task favoured the graph, while text search through the graph cost more than Grep on every task"* | the report file; the plan-124 bullet names it as evidence for the diagnosis's L2(e) |
| **Run VOID** | A run-level tripwire fired for one run | the run's row, kept, with the tripwire named | `## Measurement record` only; the run is re-run in the slot D5 names (appended after pair 9, in pair order) |
| **Measurement VOID** | A freeze-level tripwire fired: an edit to the pre-registration block after the freeze | *"The measurement is void: <item> was edited after the freeze."* | `## Measurement record`; no other row of this table is evaluated, and no ledger records a result. A Measurement VOID declared before any scored run is followed by a re-freeze (D8) |

⚠ **Phase 4 changes nothing after seeing a result.** Any edit to the pre-registration block after the Phase 2 freeze — in particular to this rule, N, the schedule, an operator script, an answer key, the mapping table or a D8 definition — voids the measurement: the Measurement VOID row (`## Tripwires`).

**COUNTER, at full strength.**
- **Cache-read tokens are not decision-bearing**, although they are by far the largest token COUNT of a research run (17.6–37.0 M cache-read against 91–144 k output per v2 run, diagnosis `:137`). The diagnosis makes no dollar conversion (*"Model mix differs, so no dollar conversion is made"*, `:159`) and calls cache-read *"the cheapest token class"* (`:161`). They grow with bytes and turns together, so a bytes-and-output rule tracks them without isolating the tool's share; they are reported, not ruled on.
- **A three-task conjunction is strict.** One task of three can make the claim NOT SUPPORTED, and with N = 3 a single noisy run can move one median.

### D10 — What the result changes

**RECOMMEND: NOTHING under `src/` is edited by this plan, whatever the result** — the posture plan 126's outcome table takes for item 17 (*"item 17 is NOT edited by this plan (D5)"*). A SUPPORTED result lets the claim enter docs later, WITH its number and its bounds. A NOT SUPPORTED result is evidence for the diagnosis's L2(e) — the raw-read ban decision plan 124's item 2 leaves open — and for the hook set, filed as a `FINDINGS.md` entry. Either way the record is `## Measurement record` and the report file.

**COUNTER, at full strength.** A plan that measures and changes nothing reads as indecision. **The answer recorded:** the change belongs to plan 124, which already owns the lever, and ratifying a `src/` change on a measurement nobody has seen yet is the error this plan exists to stop.

### OQ-1 — The fixture repository

The maintainer picks, against D3's criteria. **The plan records the URL and the pinned commit when picked**, in the pre-registration block.

### OQ-2 — The model alias

**RECOMMEND one alias, `fable`, pinned with `--model` for all sessions, the conditional probe included** — the maintainer's current default (`~/.claude/settings.json` sets `"model": "fable"` on 2026-10-03) — and record the model the transcripts report (C2). **Alternative:** two aliases, which doubles the runs and binds the result to two models.

### OQ-3 — Arm C (v1)

Arm C is v1 from `main` at `9eeff96` (E12) on the same fixture, run in Phase 6. **RECOMMEND defer:** run it only if A-vs-B leaves "v2 costs more for reasons other than CBM" unexplained. **COUNTER:** it is the question the maintainer sketched, and deferring it can mean never answering it.

### OQ-4 — Phase 0.2 in arm B

**RECOMMEND keep it,** for symmetry; its bytes are reported on their own row in both arms. **Alternative:** remove it from arm B — Phase 0.2 dropped from the arm-B file, or `generate_docs_helper preflight --skip-index` (`_preflight.py:476`) — which makes arm B purer at the price of a third difference between the arms.

### OQ-5 — The Phase 4 save prompt

**RECOMMEND save YES with a fixed slug per task** — `cbm measure t1`, `cbm measure t2`, `cbm measure t3`, typed into question 1's free-text row, which Step 4.1 normalizes to `cbm-measure-t1` etc. (`:1349`) — so the report and the handoff land on disk for scoring, then reset (D6). **Alternative:** `Don't save`, and score the console echo — fragile, because nothing writes it to disk.

### OQ-6 — The CBM version

The diagnosis's two populations differ ≈ 2.3× in CBM bytes per run — a ratio this plan derived, which the diagnosis attributes to the newer CBM's output (E4). **RECOMMEND pin the installed `codebase-memory-mcp` to one version for all arm-A runs — the newer, compact-output one — and record the version and how it was read.** **COUNTER:** the result then binds that version, and the older version's ≈ 2.3× byte cost would make arm A look worse.

### OQ-7 — The cost

**Recorded after the dry run as a NUMBER:** minutes per run and, if the runs report it, dollars per run — plus the compaction probe's, if D8's definition needed one. ⚠ **Phase 4 starts only after the maintainer has seen that number.**

### OQ-8 — Where the installs live

**RECOMMEND outside this repository, never committed.** The plan records what rebuilding them needs: the fixture URL and commit, the forge commit, the install steps, the setup chain's scripted answers, the arm-B diff, the operator scripts and the answer keys. The measurement folder (transcripts, logs) also lives outside the repository; only tables and redacted test excerpts (D8) enter it.

### OQ-9 — The CBM steering arm B still carries *(added by this draft)*

Arm B keeps each of these, and each points the model at CBM:
- the installed `CLAUDE.md`'s `## CBM-first Protocol Enforcement` section, which describes the four removed hooks as wired, and its Artifact Storage bullet sending structural queries to the graph (E9);
- the CBM MCP server's tool definitions and its own instructions (*"Graph first: …"*). Claude Code connects to a server defined in several places once, from the highest-precedence definition, and a project's `.mcp.json` outranks `~/.claude.json` (C9) — so in both arms the install's `.mcp.json` definition is the one used, and the server's instructions load in both arms;
- **helper-emitted text and a helper-enforced enum:** `research_helper`'s messages and docstrings name `trace_path` as the way callers are counted, and `--verified-via` accepts only `trace_path` and `search_code` (E7). Changing either is a `src/` edit, which D10 forbids.

**RECOMMEND keep all of it in arm B — no third delta.** It is identical in both arms, so it pulls arm B toward CBM — toward leaks, which void runs (`## Tripwires`), and toward under-using its file tools — never toward a lower arm-B cost. Removing the server from arm B would take removing both the install's `.mcp.json` entry and, for arm-B runs only, the machine-level `~/.claude.json` entry, which would otherwise become the definition used (C9).

**COUNTER, at full strength.** Arm B's model reads a `CLAUDE.md` saying hooks are wired that are not, beside a server saying "Graph first" and a helper whose messages name `trace_path` — a configuration no consumer runs. A high leak rate costs re-runs, and each re-run tests the same confused configuration. **The alternative:** a third delta rewriting arm B's `CLAUDE.md` section, plus the server disabled for arm B — a cleaner "no CBM" arm, at the price of a different fixed context per turn between the arms. The helper text stays whichever arm is picked.

### Phase 0 close record

**PENDING — no close record exists.** Nothing above is ratified, and no build phase may start.

**What the close record must contain, BY NAME and never against a range** — an item with no line cannot fail: each of D1, D2, D3, D4, D5, D6, D6b, D7, D8, D9, D10 and OQ-1 through OQ-9 with its outcome; whether per-item deliberation was supplied; whether the close is an explicit pick or a delegation (plan 98's D1 distinction); and what the outcomes put in scope (Phase 0's `#### Verify`).

---

## Measurement record

**EMPTY — nothing is measured.** Each block below is filled by the phase it names; until then it holds its headers only.

**Pre-registration block** — written in Phases 1–2 and FROZEN at the end of Phase 2: the frozen text is the block as committed at the freeze commit, whose SHA is recorded outside the block, in `**Freeze record**` below. After the freeze, any edit to the block voids the measurement (`## Tripwires`).

| Item | Value |
|---|---|
| Fixture (OQ-1): public URL and pinned commit | — |
| Forge commit installed, and `.claude/template-version` | — |
| `codebase-memory-mcp` version, and how it was read (OQ-6) | — |
| Model alias (OQ-2), and the model the transcripts record | — |
| Claude Code version at the freeze — the `claude --version` output — with `DISABLE_AUTOUPDATER` set from the first Phase 2 session through the last Phase 4 run (D7, C10) | — |
| User-level settings left on (D7): effort level, the per-model effort override in `modelSettings` for the model the alias resolves to, thinking setting, response language, permission mode — values identical across arms | — |
| Setup chain's scripted answers (Phase 1) | — |
| T1 / T2 / T3 topic text (`$ARGUMENTS`) | — |
| T1 / T2 / T3 answer keys | — |
| T1 / T2 / T3 operator scripts | — |
| Arm-B mapping table (D1), as ratified | — |
| Arm-B diff | see `#### Phase 1 record` |
| N and the run schedule (D5), as ratified | — |
| D8 definitions: tool-result bytes, families, the `Grep` family, gate fire (with the two distinguishing strings), reminder and sync injection, output deduplication, compaction | — |
| Decision rule and outcome table (D9), as ratified | — |

**Freeze record** — outside the pre-registration block, because a commit cannot contain its own SHA (the rule `126-DOWNSTREAM-SURFACE-EVIDENCE-AND-RECORD-PLAN.md` follows; grep `cannot contain its own SHA` there). One line per freeze, in the form `<SHA> — <date> — current | superseded by <SHA>`; a re-freeze before any scored run (D8) adds a line and marks the earlier one superseded.

- —

**Run log** — one row per run, dry runs and VOID runs included (Phases 2 and 4).

| # | Kind (dry / scored / probe) | Pair | Arm | Task | Rep | Date | Session id | `claude --version` | Script deviations | Tripwire | Wall min | Framework min | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| — | — | — | — | — | — | — | — | — | — | — | — | — | — |

**Results — medians over N, per task and arm** (Phase 5).

| Task | Arm | Bytes (Phase 0.2 excluded) | Output tokens | Recall | Cache-read, median turn / peak | Assistant turns | Tool calls | Gate fires: discovery / raw-tools | Reminder injections | Sync injections | Compactions | Phase 0.2 bytes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| — | — | — | — | — | — | — | — | — | — | — | — | — |

**Split by family and verb** (Phase 5).

| Task | Arm | Family or verb | Calls (median) | Bytes (median) |
|---|---|---|---|---|
| — | — | — | — | — |

**D9 outcome** (Phase 5) — each row of D9's table, by row.

| Outcome row | Fired? | Recorded sentence |
|---|---|---|
| — | — | — |

**Cost** (OQ-7) — minutes per run and, if the runs report it, dollars per run: —

---

## Phases

**Phase 0 is the `## Decisions to ratify` section above; nothing below starts before its `### Phase 0 close record` reads anything other than PENDING.**

**Build order: Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5; Phase 6 is optional and last.** Phase 3 follows Phase 2 because its test fixtures are excerpts of the dry-run transcripts (D8). Phase 4 follows Phase 3 so the module is proven on the dry runs before 18 runs are spent.

Every phase that commits does so by explicit path — **never `git add -A`** — because other sessions work in this checkout.

### Phase 0 — Ratification gate

D1–D10, D6b and OQ-1–OQ-9 go to the maintainer. **NO build phase may start before a close record exists.**

#### Verify

- The `### Phase 0 close record` names **each** of D1, D2, D3, D4, D5, D6, D6b, D7, D8, D9, D10, OQ-1, OQ-2, OQ-3, OQ-4, OQ-5, OQ-6, OQ-7, OQ-8 and OQ-9 with an explicit disposition.
- **D1's outcome names both arms and states the mapping table as ratified or amended row by row.**
- **D9's outcome ratifies the rule and the outcome table as a whole, or amends them row by row** — never "D9 ratified" over an amended table.
- It states whether per-item deliberation was supplied, and whether the close was an explicit pick or a delegation.
- **Every counter-argument above is still present, unshortened.**
- The record says what the outcomes put in scope: **D1, D3, D4, OQ-1, OQ-4, OQ-6, OQ-8 and OQ-9 decide Phase 1**; **D5, D6, D6b, D7, OQ-2, OQ-5 and OQ-7 decide Phases 2 and 4**; **D8 decides Phase 3**; **D9 and D10 decide Phase 5**; **OQ-3 decides Phase 6**; **D2 decides the command every phase measures.**

### Phase 1 — Fixture and two installs

**Route: the maintainer builds the installs outside this repository; instruction-author → instruction-reviewer produces the arm-B `research.md`, looping until the review is clean.** Every Claude Code fact this phase uses is in `### Claude Code facts from the consult (2026-10-03)` with its `claude-code-guide` verdict. The facts no source documents — the process behind `$PPID` in a hook script (C5), the transcript fields for model and version (C2, C10), and how a compaction shows in a transcript (C12) — are observed in Phase 2, not assumed here.

#### Deliverables

- **The fixture**, cloned twice at the pinned commit into two sibling directories outside this repository.
- **Both installs:** this repository's `install.sh`, run from a recorded `develop-2.0-init` commit, into each clone in standalone mode.
- **The setup chain, ONCE, in install A** — `/devforge:init-forge` → `/devforge:generate-docs` → `/devforge:configure` → `/devforge:constitute` — answered from a script recorded in the pre-registration block, with the ticket requirement OFF so `No ticket` allocates (E8 item 13), and with `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` in the environment of every setup session, so the chain cannot leave install A an auto-memory note that install B lacks (C6).
- **The copy to install B:** every path the setup chain created or modified in install A outside the CODE class (`.devforge/lib`, `bin`, `templates`, `command-refs`), read off `git status --porcelain --ignored` in A after the chain, copied into B. **Then every occurrence of install A's absolute path inside B is rewritten to B's own path** (E13), and the record lists each rewritten file.
- **Arm B's two deltas (D1):** the four hooks removed from B's `.claude/settings.json`; B's `.claude/commands/devforge/research.md` replaced by the reviewed arm-B file.
- **A baseline commit in each root, on a branch named `cbm-measure-baseline`, which is NOT the fixture's default branch** — so Phase 4's Step 4.3 emits no checkout (E13).
- **CBM at baseline in each root:** the index built, and `.devforge/lib/cbm_sync_helper write` run after the baseline commit, so `cbm-sync-session-start` stays silent (Trap 13).
- **The task material** — T1–T3's topic text, answer keys and operator scripts (D4) — written into the pre-registration block.
- **This plan** — `#### Phase 1 record` below, with the arm-B unified diff.

#### Verify

- `diff -r` of the two roots, excluding `.git`, the CODE class and the EPHEMERAL files (E13), lists exactly arm B's two deltas plus the lines carrying each root's own absolute path, every one of them listed in the record.
- A recursive grep of each root, `.git` excluded, for the OTHER root's absolute path returns nothing.
- `.claude/template-version` is equal in both roots, and the forge commit is recorded separately (E12).
- The installed CBM version and the Claude Code version are recorded, each with how it was read.
- `git branch --show-current` prints `cbm-measure-baseline` in both roots, and `.devforge/lib/cbm_sync_helper check` prints `current` in both.
- No auto-memory file exists for either root (C6).
- The arm-B diff touches only Phase 2.3's chain, the four ban sentences, the mapped steps and Phase 2.1's wording (D1); it leaves every helper-verb invocation and every helper-enforced literal — `--verified-via search_code` among them — byte-identical, even where the surrounding text names a CBM tool (E7); and instruction-reviewer returns SHIP-READY.
- **Drift from plans 123 and 124 is checked against the INSTALLED commit** (the ⚠ paragraph above E7). Install A's `.claude/commands/devforge/research.md` is grepped for `mode=compact`, `limit`, `max_output_tokens` and the `### Phase 2.1 — Cost gate` heading, and its design-reference prompt (E8 item 3) is re-read; what each grep found is recorded. Any difference from E7, E8 or D1 re-derives E8 and arm A's spec from the installed file, and D1 is re-ratified before the arm-B file is written.
- No path of the frozen benchmark install appears in any command this phase ran.

#### Phase 1 record

**NOT RUN.**

### Phase 2 — Dry run

**Route: the maintainer is the operator; the orchestrator reads the transcripts.** One run per arm on T1, **NOT scored**, under D6 and D7 — plus the one conditional compaction probe (D6b, D8), only if neither dry run compacts.

#### Verify

- **Where SessionStart hook output appears in a transcript is recorded.** If it does not appear at all, Phase 2 STOPS, and D7's reminder and sync-text checks are re-designed before the freeze.
- **How a hook block appears in a transcript is recorded** — the event kind that carries it and the framing of its text. The gate-fire definition (D8) is a contains-match on each gate's distinguishing string; if the dry runs show the string reaching the transcript altered (truncated, escaped or wrapped so it no longer contains the literal), the definition is rewritten to match what does appear, BEFORE the freeze.
- **D7's checks, each recorded:** one SessionStart-`startup` reminder injection in arm A (plus one per compaction) and none in arm B; in arm B, zero results containing `BLOCKED: For code discovery`, zero containing `BLOCKED: Raw grep/find/cat` and no text containing `The CBM (codebase-memory-mcp) index`; no `rtk` token; no `codebase-memory` skill use; zero CBM tool uses, zero `codebase-memory-mcp` Bash commands and zero `mcp__codebase-memory-mcp__` log lines in arm B; no auto-memory file for either root.
- **D8's compaction definition names its event kind** — from a dry run that compacted, or else from the one probe session the definition allows; if neither carries a compaction-marking event, Phase 2 STOPS (D8).
- **Each D8 definition was applied by hand to one dry-run transcript and produced a number,** and each number is recorded.
- **The operator script covers every question asked.** An uncovered question becomes a script line now, before the freeze.
- **The transcript's assistant events carry `message.id` and `usage`;** the record names the field that carries the model and the field that carries the Claude Code version, or records that none does.
- **No `<session>/subagents/` folder appears** (research is inline).
- **Arm A's gate behavior is recorded:** gate fires per gate (D8) — at most one per gate per run if the once-per-session design holds, and zero when no matching call was made. More than one fire of one gate in one run means `$PPID` is not stable across calls (C5, Trap 1).
- **The reset returns a clean root:** `git status --porcelain` is empty and `HEAD` is the baseline commit.
- **No carry-over in the CBM index:** after the reset and a Phase 0.2 refresh, a query of arm A's index through `codebase-memory-mcp cli` for the dry run's saved slug returns no hit, and the exact command is recorded (Trap 11).
- **The cost per run is recorded** (OQ-7).
- **The D7 window is closed after the dry runs:** `~/.claude/CLAUDE.md` equals its backup, `~/.claude/settings.json` equals its backup except the `DISABLE_AUTOUPDATER` key, which stays set (D7), and the skill directory is back in place.
- **The pre-registration FREEZE is declared at the end of this phase:** the plan is committed with the block complete, and that commit's SHA is then recorded in `**Freeze record**`, outside the block. After it, the whole pre-registration block is immutable — in particular the operator scripts, the mapping table, the answer keys, N, the schedule, the D8 definitions and D9 — and any edit to it voids the measurement (a VOID before any scored run is followed by a re-freeze — D8).

#### Phase 2 record

**NOT RUN.**

### Phase 3 — Measurement module and tests (D8)

**Route: python-engineer → python-reviewer, looping until the review is clean. Every function gets a test written AND run in the same turn.** Commit by explicit path.

#### Deliverables

- `scripts/lib/transcript_metrics.py`, `scripts/measure-transcripts.py`, `tests/lib/test_transcript_metrics.py`, and the redacted excerpts of the two dry-run transcripts the tests read.
- **This plan** — `#### Phase 3 record` below.

#### Verify

- **On the two dry-run transcripts, the module's call counts equal a manual count of `tool_use` events by name;** the manual count is stated in the record.
- **Every frozen D8 definition is implemented as written,** and on the dry-run transcript Phase 2 used it gives the number Phase 2 recorded. A definition that cannot be implemented is a Measurement VOID before any scored run, followed by a re-freeze (D8) — never a silent re-definition.
- An unknown event kind in a test input is counted and skipped, and the run does not fail.
- **A grep of the committed excerpts for the home path, the maintainer's name, the machine's name and any client identifier returns nothing.**
- `python3 -m pytest tests/lib -q -p no:cacheprovider` is green.
- `git show --stat` lists only the module files, the excerpts and this plan.
- python-reviewer returns SHIP-READY, or every finding is fixed.

#### Phase 3 record

**NOT RUN.**

### Phase 4 — The 18 scored runs (D5, D6)

**Route: the maintainer is the operator; the orchestrator runs the module and fills the run log.** ⚠ **Cost is billed to the maintainer's account; this phase starts on the maintainer's go, after OQ-7's number is recorded.**

#### Verify

- **18 non-VOID rows of Kind = scored exist in the run log,** in the D5 schedule's order. Every VOID run's row is kept; its re-run is appended after pair 9, the re-runs in the same pair order. **More than 2 VOID runs in one cell (task × arm) STOP the series for the maintainer's review** (`## Tripwires`).
- **The pre-registration block is byte-identical to the block as committed at the latest, non-superseded freeze commit, whose SHA is recorded outside the block** (`**Freeze record**`) — its D8-definitions row included — and the definitions the module applied match that row.
- **`claude --version` equals the freeze's before run 1** (D7, C10), and the operator's record of it is in the run log.
- **The D7 window is closed after the last run:** the `DISABLE_AUTOUPDATER` key is removed, each restored user-level file equals its backup byte for byte, and the skill directory is back in place.

#### Phase 4 record

**NOT RUN.**

### Phase 5 — Report and ledgers

**Route: instruction-author → instruction-reviewer, looping until the review is clean.** ⚠ **Re-read `git status`, read each ledger LIVE, re-derive every edit from what is there, and commit by explicit path — other sessions edit these files.**

#### Deliverables

- **A report file at the repo root,** `RESEARCH-2026-MM-DD-CBM-VS-FILES.md` — the diagnosis is the precedent — carrying the per-arm and per-task medians, the per-family and per-verb split, D9 applied row by row, the honest bounds, and the appendix D8 names: the `AskUserQuestion` count, the per-call CBM arguments, the unknown-event count, and the model and version fields.
- **`## Measurement record`** filled as it describes.
- **`CHANGELOG.md`** — one line under `## [Unreleased]`, under the sub-heading read live, stating the evidence class first and the bounds last.
- **`FINDINGS.md`** — a new numbered entry if a NOT SUPPORTED row fired, numbered after the last entry present at build time.
- **`124-PIPELINE-COST-REDUCTION-PLAN.md`** — one dated bullet under its lever 2, naming the D9 row that fired and pointing at the report. Nothing else in that file changes.
- **`PLAN-STATUS-ARCHIVE.md`** — this plan's `## Index` line and its `## Entries` entry, both or neither. **The ledger lands HERE, at Phase 5, not at the plan's creation** — plan 125 did the same at its Phase 3.
- *(Added by this draft.)* **`CLAUDE.md`'s `## Where to find what`** — one row for the measurement module, as plan 126's Phase 6 adds one for its harness.

#### Verify

- No sentence in any ledger or in the report claims a rate, a consumer result, or a result beyond `/devforge:research`.
- Every summary written repeats the evidence class.
- The report and every edited ledger name no client, install, repo, branch, ticket or component.
- `git diff 124-PIPELINE-COST-REDUCTION-PLAN.md` shows one added bullet and nothing else.
- instruction-reviewer returns SHIP-READY, or every finding is fixed.

#### Phase 5 record

**NOT RUN.**

### Phase 6 — OPTIONAL: arm C (v1)

**Runs only on a ratified OQ-3 that says so.** v1 from `main` at `9eeff96` on the same fixture, the same three tasks, and an operator script adapted to v1's prompts, under its own pre-registration block written before its first run. **It answers the generation question, not the CBM question,** and it carries every confound the diagnosis named except the fixture and the model.

#### Phase 6 record

**NOT RUN.**

---

## Honest bounds

⚠ **These are the plan's ceiling. Any summary that drops one overstates the plan.**

- **One fixture, one model, one Claude Code version, one CBM version** — the result binds all four. The version is held by `DISABLE_AUTOUPDATER`, kept set from the first Phase 2 session through the last Phase 4 run, checked before Phase 4's first run, and checked per run by a STOP tripwire (D7, Tripwires); a straddle the maintainer accepts instead of restarting becomes its own bound here.
- **N = 3 gives counts, never rates.**
- **Arm B measures "the same sweeps with file tools", never "the best file strategy"** (D1).
- **Arm B still carries CBM steering:** the installed `CLAUDE.md`'s CBM section and the CBM server's tools and instructions (OQ-9).
- **Answer-key recall is the ONLY outcome measure.** The quality of the spec that follows research is not measured.
- **The operator authored the answer keys.** The script, not blindness, keeps the key out of the answers.
- **The transcript format is internal and version-bound** (C3); the parser is validated on one CLI version only.
- **Phase 0.2 and the setup chain's CBM use are outside the measured comparison** — Phase 0.2 is reported on its own row, and the setup chain is not measured at all.
- **Arm B's helper state carries graph vocabulary over file-tool evidence.** In arm B, `declare-caller-total` holds a Grep-derived caller count the helper defines as a `trace_path` row count, `--verified-via search_code` labels a Grep-derived confirmation, and helper messages can still name `trace_path` (D1, OQ-9). None of it can change without a `src/` edit.
- **The result says nothing about `/devforge:implement`, `/devforge:generate-docs` or any other CBM-backed step** (D2).
- **The existing evidence was itself possibly contaminated** by the user-level hooks and rtk on this machine (E10). This plan controls that going forward and cannot repair it backward.
- **Arm A's "ban" is a nudge.** The two shipped gates fire once per session by design (E9), so arm A measures the shipped behavior, not a hard ban — and `bash-ban-raw-tools` never matches `rg`, `sed`, `head` or `awk`.
- **Both arms run on a machine whose user-level hooks are off but whose other user-level settings stay on** (D7): auto memory off; the user-level hooks, the rtk import and the CBM skill removed; effort level, thinking, response language and permission mode left as the maintainer has them and recorded at the freeze. **A consumer's settings differ, so the Output figures transfer only as far as those settings match.**
- **A compaction re-injects the shipped reminder in arm A only — and the sync block only on a missing or drifted stamp** (D6b). Compactions are recorded and reported per arm, never voided.
- **Every hand-back can make cost arm-dependent.** A `you decide` reply makes the model supply the content itself, and the discovery calls it spends doing so fall inside the measure. Phase 2.4d's three fallback prompts fire on a CBM miss (E8 item 11), so how often they fire is itself arm-dependent; the narrow-framing follow-up (E8 item 5) is meant never to fire, because T1's script carries the citation (D4). The operator answers every hand-back identically, and the run log records each one as a deviation.

---

## Tripwires

**Two kinds of VOID** (D9): a **run VOID** voids one run — its row is kept, and its re-run is appended after pair 9, in pair order (D5); a **measurement VOID** voids the whole measurement.

- **A CBM `tool_use` in an arm-B transcript, a `mcp__codebase-memory-mcp__` line in arm B's `cbm-usage.log`, or an arm-B Bash command containing `codebase-memory-mcp` → run VOID.**
- **In an arm-B run, a tool result containing `BLOCKED: For code discovery` or `BLOCKED: Raw grep/find/cat`, or a SessionStart injection containing `The CBM (codebase-memory-mcp) index` → run VOID** — a removed hook fired (D7).
- **In an arm-B run, a SessionStart injection containing `CRITICAL - Code Discovery Protocol:` → run VOID** — the removed `cbm-session-reminder`, or the user-level copy, fired (D7, D8's reminder injection).
- **A raw `Read` / `Grep` / Bash-grep over source in arm A → RECORDED, never void.** Arm A is as shipped; the diagnosis saw 12 direct reads per run (E1).
- **A `research_helper` message naming `trace_path` in an arm-B run → RECORDED, never void** (E7, OQ-9) — unless the model then calls CBM, which the first tripwire voids.
- **A compaction event in a scored run → RECORDED, never void,** and reported per arm (D6b, which carries the COUNTER).
- **Any edit to the pre-registration block after the Phase 2 freeze — in particular an operator script, the mapping table, an answer key, N, the schedule, a D8 definition or D9 → measurement VOID** (a VOID before any scored run is followed by a re-freeze — D8).
- **A user-level hook, an `rtk` rewrite, a `codebase-memory` skill use, or an auto-memory file observed for any run → run VOID.**
- **A session resumed or continued instead of started fresh → run VOID.**
- **In arm A, a CBM result naming a path a previous run saved under `specs/` → run VOID** (Trap 11).
- **Step 4.2 re-asks for a ticket → run VOID,** and Phase 1's ticket setting is re-opened before any further run.
- **More than 2 VOID runs in one cell (task × arm) → STOP the series** for the maintainer's review.
- **The model a transcript records differs from the first run's → STOP;** the series no longer runs on one model.
- **The Claude Code version the operator records for a run differs from the freeze's → STOP;** the maintainer decides between re-pinning and restarting the series, and recording the straddle as a bound (D7, C10).
- **An install root whose files name the other root's absolute path → STOP before any run** (Trap 10).
- **Any `install.sh`, `update.sh`, edit, session or message against the frozen benchmark install → forbidden; STOP.**
- **Any edit under `src/` by this plan → forbidden; STOP.**
- **An edit to a plan file other than this one, beyond the one dated bullet in plan 124 under its lever 2 → STOP.**
- **A client identifier in any tracked file this plan writes → STOP and remove it.**
- **A commit staging a file this plan does not name → STOP and unstage.**

---

## Non-goals

- **No `src/` edit** — no change to the shipped hooks, to `/devforge:research`'s Phase 2.3, or to any command (D10).
- **No claim about outcome quality beyond answer-key recall.**
- **No question about how CBM is served or shared, and no team-scale question** — both belong to a separate 2026-10-03 conversation. OQ-9 concerns only what arm B's sessions load.
- **No headless or SDK harness** (D6).
- **No v1 arm by default** (OQ-3).
- **No consumer install, ever** — the fixture is a public repository, and the frozen benchmark install is never touched (E14).
- **No measurement of any command other than `/devforge:research`** (D2).

---

## Context for next session

⚠ **Evidence class: ONE observational, confounded measurement exists (the 2026-09-27 cost diagnosis); NO controlled comparison exists; this plan would produce the first; NOTHING is measured yet.** ⚠ All line digits drift — **grep the quoted text, never the digits.**

**The one sentence that governs everything here: nobody may say CBM saves tokens until the same `/devforge:research` sweeps, on the same fixture and tasks, cost fewer tokens through the graph than through file tools at no lower recall — on every task, by a rule written before the first run.**

⚠ **Phase 0 is the gate, and nothing below it may start.** On 2026-10-03 no decision is ratified.

**Out-of-scope observation made while drafting — owned by no phase here, NOT fixed, and NOT filed in `FINDINGS.md`:** `src/CLAUDE.md:187` opens its `## CBM-first Protocol Enforcement` section with *"Four hook scripts ship at `.claude/hooks/`"*, while its own table and `src/hooks/` list five. It is not filed because it is a one-word count drift that the next editor of that file fixes; whether to file it anyway is the orchestrator's call.

### Traps

**Trap 1 — the PPID-keyed `/tmp` gate files.** Both shipped gates key a file on `$PPID` (E9). Reap them before every run (D6), or arm A's gates may not fire on a later run of the day. The reap is machine-wide: another session's gate fires once more after it. ⚠ **A shell-form hook runs under `sh -c` on macOS and Linux (C5), and the process behind `$PPID` is undocumented; if it is a per-call process, the gate blocks every matching call** — Phase 2 counts gate fires per gate (D8) to find out which holds.

**Trap 2 — the "ban" is a nudge.** Each shipped gate blocks once and then passes (E9). Reading `:403`'s *"will be blocked by runtime hooks"* as a hard ban misreads arm A.

**Trap 3 — two CBM versions.** ≈ 200 KB against ≈ 86 KB of CBM bytes per run in the diagnosis's two populations (E4) — a ratio of ≈ 2.3× this plan derived, on different codebases. Pin one version (OQ-6), and never compare this plan's arm A with the diagnosis's figures.

**Trap 4 — `limit` and `mode=compact`.** The shipped spec sets neither, yet the recorded runs passed them (E2). Record the arguments of every CBM call (D8).

**Trap 5 — rtk.** It rewrites Bash commands and is documented as compressing dev-operation output (E10). It must be off in both arms, and a run that shows it is VOID.

**Trap 6 — the user level looks like the shipped level.** The user-level gate keys the same `/tmp` file name, the user-level reminder opens with the same line, and a user-level skill and MCP registration steer toward CBM (E10). Only D7's window and its dry-run checks tell them apart.

**Trap 7 — the reset.** **Never `git clean -x`** in an install root — it deletes the untracked CODE class `.devforge/lib` (E13). **Never `rm -rf specs/`** — a fixture can track its own; `git reset --hard` plus `git clean -fd -- specs/` is the reset (D6).

**Trap 8 — scratch versus record.** `.devforge/research-report.json` (EPHEMERAL scratch) and `specs/<feature>/research-report.md` (the RECORD) share a name. **Score the record** (`storage-rules.md:134`).

**Trap 9 — subagent placeholder usage.** In subagent transcripts the first event of a message carries a placeholder `usage` (E3). Irrelevant for research, which is inline; relevant the moment arm C or another command is measured.

**Trap 10 — absolute paths in copied files.** `.devforge/index.json` stores its root as an absolute path (E13). A file copied from install A into B can point B at A; Phase 1 rewrites and greps for it.

**Trap 11 — CBM index carry-over.** A run's saved report is a file the CBM index can pick up, and nothing verified here says the index forgets it after `git reset --hard` (E13). Phase 2 checks; a run that meets a previous run's report through CBM is VOID.

**Trap 12 — auto-memory carry-over.** Auto memory is per repository and loads into every session (C6). Without `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`, run N can leave run N+1 a note.

**Trap 13 — the sync hook's drift message.** `cbm-sync-session-start` injects an instruction to re-index when `.devforge/cbm-last-indexed-sha` differs from `HEAD` (E9). The stamp is written at the baseline commit in Phase 1 and kept through every reset; otherwise arm A pays a re-index that arm B never sees.

**Trap 14 — the default branch.** On the repository's default branch, a research save creates and switches to a `spec/*` branch (E13). The baseline branch is not the default, so no branch is created; the reset still deletes any that appears.

**Trap 15 — the version stamp is not a commit.** `.claude/template-version` holds the manifest version (E12). Record the forge commit itself.

**Trap 16 — client identifiers.** Treat every file at this repo root as public once committed. The fixture is public; the frozen benchmark install and every consumer stay unnamed (E14).

**Trap 17 — line digits.** Every `file:line` here was read on 2026-10-03. Re-anchor by the quoted text.

### File anchors

**EDIT targets — a phase of this plan writes each of these:**

- **This plan** — every phase's record and `## Measurement record`.
- **`scripts/lib/transcript_metrics.py`**, **`scripts/measure-transcripts.py`**, **`tests/lib/test_transcript_metrics.py`** and the redacted excerpts (Phase 3).
- **`RESEARCH-2026-MM-DD-CBM-VS-FILES.md`** — new, at the repo root (Phase 5).
- **`CHANGELOG.md`**, **`FINDINGS.md`**, **`PLAN-STATUS-ARCHIVE.md`**, **`CLAUDE.md`**'s `## Where to find what`, and ONE dated bullet in **`124-PIPELINE-COST-REDUCTION-PLAN.md`** under lever 2 (Phase 5).

**READ-ONLY anchors — no phase of this plan writes any of these:**

- `RESEARCH-2026-09-27-V2-COST-DIAGNOSIS.md` — `| research v2 | 92 |`, `**CBM costs bytes.**`, `**L2 — Cap the CBM chain in research.**`, `**Sources.** Claude Code session transcripts`, `Two scratch scripts (not in the repo)`, `### F9 — Side finding`, `the ban is a bet on CBM`, `cheap part`, `Cache-read is the cheapest token class`, `no dollar conversion is made` (E1–E5, D9).
- `123-PROJECT-TYPE-GATED-DESIGN-INTAKE-PLAN.md` — its title, `Project-Type-Gated Design Intake Plan` (the drift warning above E7). **Read-only.**
- `124-PIPELINE-COST-REDUCTION-PLAN.md` — `used a different model`, `**CBM call budget in`, `whether that raw-read ban stays decided separately`, `` Delete the `/devforge:research` Phase 2.1 cost gate `` (E4, E6, the drift warning above E7); edited only by Phase 5's one bullet.
- `src/commands/research/main.md` — `### Phase 2.3 — CBM discovery chain (MANDATORY order)`, `are forbidden and will be blocked by runtime hooks`, `This is the only sanctioned source-read path`, `do NOT use raw`, `stay forbidden (Phase 2.3)`, `no fresh subagent boot`, `--verified-via <trace_path|search_code>`, `The helper accepts only those two literal values`, `` Vue `<script setup>` ``, `` Pick a `mode` from ``, `mode=data_flow, direction=outbound`, `search_graph(label="Method"`, `` `--evidence` is REQUIRED ``, `Is this interpretation right?`, `Investigation will scan roughly`, `TWO questions in ONE call` (E7, E8, D1, D3, D4).
- `src/devforge/lib/_research/_cli.py` — `choices=("trace_path", "search_code")`; `_research/_cmds_dataflow.py` — `declares the trace_path row count`, `per the trace_path row count`; `_research/_cmds_render_verify.py` — `where N = the trace_path(mode=calls, direction=inbound) row`, `re-run trace_path and re-declare via`, `write-boundary call via trace_path mode=calls`; `_research/_cmds_basic.py` — `BLOCKED: /devforge:research requires the full 4-command setup chain.` (E7, D8).
- `src/settings.template.json`; `src/hooks/cbm-code-discovery-gate` (`BLOCKED: For code discovery`), `src/hooks/bash-ban-raw-tools` (`BLOCKED: Raw grep/find/cat`), `src/hooks/cbm-mcp-marker`, `src/hooks/cbm-session-reminder` (`CRITICAL - Code Discovery Protocol:`), `src/hooks/cbm-sync-session-start` (`current|not-a-git-repo|""`, `The CBM (codebase-memory-mcp) index`); `src/mcp.json` (E9, D6b, D8).
- `install.sh` — `cp "$TEMPLATE_DIR/src/settings.template.json"`, `template-version` (E9, E12).
- `src/CLAUDE.md` — `## CBM-first Protocol Enforcement`, `To disable any hook, remove its entry`, `Four hook scripts ship` (E9).
- `src/devforge/storage-rules.md` — `Scratch ≠ record — do not conflate.`; `src/files/devforge.gitignore` (E13).
- `src/devforge/lib/index_helper.py` — `"project_root": str(project_root.resolve()),`; `src/devforge/lib/_generate_docs/_preflight.py` — `"cli", "index_repository"`, `--skip-index` (E13, OQ-4).
- `src/devforge/lib/_profile/_cli.py` — `_SUBCOMMAND_REGISTRY`; `tests/lib/_profile/_fixtures.py` — `the documented exception` (E11, D8).
- `scripts/lib/memory_lane.py`, `scripts/verify-memory-lane.py`, `tests/lib/test_memory_lane.py`; `scripts/lib/model_version_tripwire.py` — `makes the framework's model choice VERSION-FREE` (E11).
- `126-DOWNSTREAM-SURFACE-EVIDENCE-AND-RECORD-PLAN.md` — the precedent for pre-registration (D1 element 7), the outcome table (D2) and the kept-harness COUNTER (D7). **Read-only.**
- `115-WRAPPER-INNER-REPO-CBM-VISIBILITY-PLAN.md` — `every CBM-backed step` (D2). **Read-only.**
- `PLAN-STATUS-ARCHIVE.md` — `built ahead of plan 108` (the sequencing precedent); edited only by Phase 5.
- `~/.claude/settings.json`, `~/.claude/CLAUDE.md`, `~/.claude/skills/codebase-memory/` — machine-level, outside this repository (E10); edited only inside D7's windows and restored at each close, except `~/.claude/settings.json`'s `DISABLE_AUTOUPDATER` key, set from the first Phase 2 session through the last Phase 4 run (D7). `~/.claude.json` — machine-level, read only; no phase edits it (OQ-9).

---

## When resuming work

1. **Read this plan in full** before touching anything — it encodes context that is not in the conversation.
2. **Check `### Phase 0 close record` first.** While it reads PENDING, nothing is ratified and **no build phase may start.**
3. **Re-check the plan number** — another session may have taken 127. Find a sibling plan by its TITLE, never by assuming a number.
4. **Re-verify the anchors by grepping the quoted text** in `### File anchors`, never the digits.
5. **Route every NEW Claude Code fact through `claude-code-guide`.** C1–C12 carry the 2026-10-03 verdicts, all settled; C1's hook merge, C5's shell and C8's SDK answers were settled by a targeted section fetch — do not re-open them. The undocumented facts the runs depend on — `$PPID` (C5), the model and version fields (C2, C10) and the compaction event kind (C12) — are observed in Phase 2.
6. **Route every edit through the house flow:** python-engineer → python-reviewer for every Python edit, with a test per function run in the same turn; instruction-author → instruction-reviewer for every markdown edit; each loop runs until its review is clean.
7. **Commit by explicit path, never `git add -A`.** Re-read `git status` first, and read every shared ledger live.
8. **Keep the evidence class and the no-client-identifier rule attached** to every summary of this plan — and, once Phase 4 runs, add: one fixture, one model, N = 3, counts not rates.
9. **Never touch the frozen benchmark install** — no `install.sh`, no `update.sh`, no edit, no session (E14).
