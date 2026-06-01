---
name: audit
description: Adversarial whole-codebase quality audit across the full spectrum — mislogic, system design, language/framework best practices, duplication, and constitution adherence; writes a dated report.
argument-hint: "[--full | --uncommitted | --top N | path]"
disable-model-invocation: true
---

# /audit — Adversarial Codebase Audit

`/audit` is a standalone, on-demand whole-codebase audit for periodic "second opinion" quality reviews. It invokes the review-agent ensemble (`code-reviewer`, `architect`, `qa-engineer`, `security-reviewer`) in ADVERSARIAL MODE to hunt the full quality spectrum — mislogic (lying code, control-flow bugs, cross-file contradictions), system design (layering drift, SOLID-at-scale, god components — software design, not visual), language/framework best practices (type-safety suppression, untyped boundaries, reactivity/lifecycle misuse, static perf-idiom smells), duplication (copy-paste and diverged variant copies), and constitution-principle adherence — validates every finding against the actual source to discard hallucinations, force-ranks the survivors, and writes a dated report to `audits/YYYY-MM-DD-audit.md`. Each agent declares a `Category` on every finding (one of `mislogic`, `system_design`, `best_practice`, `duplication`, `security`, `blind_spot`); the report buckets findings by that declared category. Read-only — it never modifies source, never auto-commits the report. State + render shape are owned by `.devforge/lib/audit_helper`; the orchestrator composes values via verb subcommands. **NOT part of any workflow chain — invoke manually after several specs ship, or on a periodic cadence.**

Usage: `/audit` (broad, default) · `/audit --full` (explicit broad) · `/audit --top N` (hotspot — top N risk-scored files) · `/audit --uncommitted` (working-tree changes) · `/audit path/to/file.ts` or `/audit src/auth/` (narrow).

## Maintainer note

This file lives at `src/commands/audit/main.md` in the AIDevTeamForge template repo and is the SSOT for the `/audit` command. Do NOT inject project-specifics — this spec is substituted + emitted into target projects by the build. Helper paths use the installed `.devforge/lib/...` location because that's where they resolve at runtime in the target project. Reference-file paths are written author-relative (`references/<file>.md`); the emitter rewrites them to `.claude/commands/audit/references/<file>.md` at install time.

## Outputs of this phase

- `audits/.state.json` — audit run state (phase + mode + scope + outpath). Owned + shaped by the helper; initialized at Preflight, advanced via `check-status-and-flip`. Lives at the workspace root's `audits/` directory.
- `audits/.tmp-<agent>.md` — per-agent findings, written by each adversarial agent in Phase 3 and consumed + deleted in Phase 4. Gitignored via `audits/.gitignore`.
- `audits/YYYY-MM-DD-audit.md` — the rendered audit report. Produced by the helper's `render-report` verb in Phase 5; collision suffix `-2`, `-3`, … on same-day re-runs. **Not committed, not staged** — the user decides whether to keep audit history in git.

### Intermediate JSON files (orchestrator-written, helper-consumed)

The helper cannot call CBM or dispatch agents (a subprocess has no MCP tools), so the orchestrator captures each verb's stdout to an intermediate JSON file that the next verb reads (most verbs take a `--<name> <path>` flag, not stdin). All live under `audits/` with a leading dot and are scratch state for one run — the orchestrator deletes them at the end (Phase 6). The first-run `audits/.gitignore` the helper writes ignores `.tmp-*.md` only, so these `.*.json` scratch files are NOT auto-ignored; the Phase 6 `rm` deletes them so they never reach a commit. Several verbs print a DICT (e.g. `{findings, consensus_map}`) but the next verb's `--findings` requires a BARE ARRAY — those steps include a one-line `python3 -c` extraction (shown inline at each phase). The per-agent scratch files (`audits/.parsed-<agent>.json`, `audits/.findings-<agent>.json`, `audits/.validated-<agent>.json`) follow the same one-run lifecycle.

- `audits/.mode.json` — the `resolve-mode` stdout (mode + scope_arg + uncommitted). Written in Phase 1.1, read by `resolve-scope --mode-result`.
- `audits/.callers.json` — `{file: caller_count}` or `{file: [caller_qns]}` per-file inbound-edge payload from CBM. Written by the orchestrator in Phase 2.1 (hotspot only), read by `compute-hotspots --callers`.
- `audits/.hotspot.json` — the ranked `HotspotResult` from `compute-hotspots` stdout. Written in Phase 2.1 (hotspot only), read by `resolve-scope --hotspot` and `render-hotspot-summary --hotspot`.
- `audits/.scope.json` — the `resolve-scope` stdout (`scope_files`, `file_count`, `pipeline`, `scope_oversize`). Written in Phase 2.2, read by `render-scope-block --scope` and `render-agent-brief --scope`.
- `audits/.recurring.json` — `[{file, fingerprint}]` past-review findings the orchestrator extracts from recent `specs/*/review.md`. Written in Phase 4.3 (broad + hotspot + directory/uncommitted; NOT single-file), read by `map-recurring-issues --recurring`.
- `audits/.parsed-<agent>.json` — `consume-tmp` stdout (a DICT: `status` + `findings` array). Written + read per agent in Phase 4.1.
- `audits/.findings-<agent>.json` — the bare `findings` array extracted from `.parsed-<agent>.json`. Written in Phase 4.1, read by `validate-findings --findings`.
- `audits/.validated-<agent>.json` — `validate-findings` stdout per agent (`passed` + `discarded` + `discard_counts`). Written + read in Phase 4.1.
- `audits/.validated.json` — the four agents' validated `passed` findings concatenated into ONE bare array. Written in Phase 4.1, read by `compute-consensus --findings`.
- `audits/.consensus.json` — `compute-consensus` stdout (a DICT: `findings` merged working list + `consensus_map`). Written in Phase 4.2.
- `audits/.consensus-findings.json` — the bare `findings` array extracted from `.consensus.json`. Written in Phase 4.2, read by `map-recurring-issues --findings` (and `force-rank-top10` on the single-file skip).
- `audits/.recurring-mapped.json` — `map-recurring-issues` stdout (a DICT: `findings` recurring-tagged + `recurring_status`). Written in Phase 4.3.
- `audits/.working.json` — the bare recurring-tagged `findings` array extracted from `.recurring-mapped.json`. Written in Phase 4.3, read by `force-rank-top10 --findings`.
- `audits/.ranked.json` — `force-rank-top10` stdout (a DICT: `top` = ordered `[{finding, score}]`). Written in Phase 4.4, read by the orchestrator when building the report dict's `top10`.
- `audits/.report.json` — the assembled `render_report` input dict. Written in Phase 4.5, read by `render-report --report` (Phase 5) and `render-inline-summary --report` (Phase 6).

## Reference files

Read these in full at the phase where each is needed. The adversarial preamble + mislogic checklist + best-practices checklist are load-bearing prompt text — inject them VERBATIM into every agent invocation; do not paraphrase, summarize, or templatize them.

- `references/adversarial-preamble.md` — the ADVERSARIAL AUDIT MODE preamble (Phase 3, every agent).
- `references/mislogic-checklist.md` — the Mislogic Hunt Checklist (Phase 3, every agent).
- `references/best-practices-checklist.md` — the system-design + language/framework best-practices + duplication + constitution-principle adherence hunt checklist (Phase 3, every agent). Injected verbatim alongside the mislogic checklist; each section names the `Category` its findings carry.
- `references/report-format.md` — the report skeleton `render-report` produces (orientation for Phase 5; the helper owns the actual render).
- `references/hotspot-scoring.md` — the risk-score formula, weights, defaults, and knobs for `--top N` mode (Phase 2, hotspot only).

## Helper interaction model

Every mechanical step is a normal Bash tool call to `.devforge/lib/audit_helper <verb> ...`. Each verb prints JSON (or a rendered block) to stdout. Most verbs that consume a prior verb's output take a `--<name> <path>` flag (not stdin), so capture stdout to the named `audits/.*.json` scratch file with `>` and pass that path into the next call — the per-phase fences below show the exact redirects. On any non-zero exit, copy the helper's stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), then follow the recovery note for that phase. The helper owns file structure, validation, and atomic writes; the orchestrator owns agent dispatch, the verbatim prompt text, user-facing prose, and phase pacing.

## Preflight — CBM refresh + state load

```bash
.devforge/lib/generate_docs_helper preflight
```

`/audit` is standalone and not part of the docs pipeline; this call is invoked here only to keep the CBM index fresh, which hotspot scoring (Phase 2.1) depends on. Refreshes the CBM index stamp so Phase 2 hotspot scoring and per-agent reference resolution see current code. Skip the call when `.devforge/.preflight-stamp` is fresher than 60 seconds — the stamp is already current. Check freshness with:

```bash
[ -f .devforge/.preflight-stamp ] && \
  [ "$(( $(date +%s) - $(stat -f %m .devforge/.preflight-stamp 2>/dev/null || stat -c %Y .devforge/.preflight-stamp) ))" -lt 60 ]
```

Exit 0 → stamp fresh; skip the helper call. Non-zero → run `.devforge/lib/generate_docs_helper preflight`. CBM is REQUIRED only for hotspot mode (Phase 2 gates on it per `references/hotspot-scoring.md`); narrow + broad modes degrade gracefully when CBM is absent.

Then initialize run state:

```bash
.devforge/lib/audit_helper check-status-and-flip --workspace-root . --to preflight
```

`check-status-and-flip` advances `audits/.state.json` to the named phase so an interrupted run can report where it stopped. Call it once at the start of each major phase with `--to <phase>` (`preflight`, `phase1`, `phase2`, `phase3`, `phase4`, `phase5`), and once at the very end of Phase 6 with `--to phase6 --status complete`. The per-phase calls are shown at each phase heading below; keep them lightweight (one call per boundary, no parsing of the output beyond the non-zero-exit check). `--to` accepts any label, so these phase names are a convention, not a helper-enforced enum.

## PHASE 1 — Load Context & Guard

```bash
.devforge/lib/audit_helper check-status-and-flip --workspace-root . --to phase1
```

Cheapest guards first; mode determination before any mode-conditional I/O.

### 1.1 — Resolve mode from `$ARGUMENTS`

```bash
.devforge/lib/audit_helper resolve-mode -- "$ARGUMENTS" > audits/.mode.json
```

Pass the raw argument string as a single positional after the `--` end-of-options separator. The `--` is REQUIRED: without it, argparse treats a leading `--full` / `--top` / `--uncommitted` as an unknown top-level flag and exits 2 before the subcommand runs. With `--`, the whole `$ARGUMENTS` string (including any leading dashes) is taken as the positional the verb parses. Stdout JSON carries the resolved `mode` (`narrow` / `hotspot` / `broad`), `scope_arg` (the path or the `--top N` value, or empty), and `uncommitted` (bool). Capture it to `audits/.mode.json` — `resolve-scope` (Phase 2.2) reads this exact file via `--mode-result`. (Create `audits/` first if it does not yet exist — `mkdir -p audits`.) Empty `$ARGUMENTS` and `--full` both resolve to `broad`; `--top N` resolves to `hotspot`; a path or `--uncommitted` resolves to `narrow`. On unparseable input (e.g. more than one positional path) the verb sets a non-empty `error` field, writes the same message to stderr, and exits 2 — copy stderr VERBATIM and end the turn; the user re-invokes with a single valid argument shape.

### 1.2 — Agent-existence check (fail-fast)

```bash
.devforge/lib/audit_helper check-agents
```

Detects which of the four audit-capable agents exist in `.claude/agents/`: `code-reviewer`, `architect`, `qa-engineer`, `security-reviewer`. The result is always JSON on **stdout** — `present` + `missing` lists plus an `all_missing` boolean; nothing is written to stderr. The verb exits **3** when `all_missing` is true (zero agents installed): copy the stdout JSON VERBATIM as a fenced block and end the turn — the user must run `/setup-wizard` to install at least one. When 1–3 exist (exit 0), proceed and carry the `missing` list forward for the report's "Agents skipped (not installed)" section.

### 1.3 — Preflight context + constitution guard

```bash
.devforge/lib/audit_helper preflight-context
```

Reads `constitution.md`, `CLAUDE.md` (Source Root, project type, framework, language), and `.claude/memory/MEMORY.md` (pitfalls, past incidents, lessons), and emits a structured context block on stdout for downstream phases. This verb is best-effort and ALWAYS exits 0 — the constitution guard is a JSON-field check, NOT an exit code: if the stdout JSON has `"constitution_populated": false` (the file is absent or still contains a populate-marker), STOP — tell the user VERBATIM "⛔ constitution.md has not been populated yet. Run `/constitute` before using `/audit`." and end the turn.

The context block carries the Source Root. `audits/` always lives at the **workspace root** (the directory containing `CLAUDE.md`), NEVER under Source Root, even in wrapper mode.

## PHASE 2 — Determine Scope

```bash
.devforge/lib/audit_helper check-status-and-flip --workspace-root . --to phase2
```

### 2.1 — Hotspot scoring (hotspot mode only)

For `--top N` mode, score every candidate file and take the top N. Read `references/hotspot-scoring.md` in full first — it defines the risk formula, default weights (`w_c=0.5, w_k=0.4, w_s=0.1`), the `--weights` knob, and the CBM-required gate.

**Step A — build the caller payload.** Caller counts come from CBM and must be supplied to the helper as a file — a subprocess helper cannot call MCP, so the orchestrator (which has the MCP tools) produces them. First enumerate the candidate source files (the same set the helper scores — tracked source files), then for each file resolve its inbound-edge count via CBM (`trace_path` inbound / `search_graph`, aggregated per file, per `references/hotspot-scoring.md`). Write the result to `audits/.callers.json` as a `{file: caller_count}` object — each value is EITHER a strict integer (the inbound-edge count) OR a list of caller qualified-names (the helper dedupes the list and uses its length). The two forms may be mixed across files; this mirrors the helper's `load_callers` contract. Files absent from the payload count as 0 at the merge step.

**Step B — score.** Capture the ranked result to `audits/.hotspot.json`:

```bash
.devforge/lib/audit_helper compute-hotspots --top "$N" --callers audits/.callers.json [--weights c=0.5,k=0.4,s=0.1] > audits/.hotspot.json
```

The verb prints the ranked `HotspotResult` (top list + next-10 + per-file metrics) as JSON to stdout; the `>` redirect captures it into `audits/.hotspot.json`. The helper computes git churn (90-day commit count) and LOC itself, normalizes each metric min-max, and applies the weighted sum.

**CBM-required stop.** If `compute-hotspots` exits 2, the CBM caller payload is missing or unreadable — STOP, copy the helper's stderr VERBATIM, and tell the user to build the codebase-memory index first. Hotspot mode REQUIRES CBM (Decision 8); there is no grep fallback and scoring does not proceed without it. (Narrow + broad modes never reach this step and degrade gracefully when CBM is absent.)

**Step C — render the table.** On success, show the human-readable Top-N + Next-10 table:

```bash
.devforge/lib/audit_helper render-hotspot-summary --hotspot audits/.hotspot.json
```

This reads `audits/.hotspot.json` and produces the top-N table plus the "Next 10 Candidates" tail (positions N+1..N+10); display it to the user. The same next-10 list also reaches the report via `render-report` (it embeds `next_candidates` in hotspot mode — Phase 4.5 copies it from `audits/.hotspot.json` into the report dict), so this is the inline preview, not the only place it appears. Skip 2.1 entirely for narrow + broad modes.

### 2.2 — Resolve the file set

```bash
.devforge/lib/audit_helper resolve-scope --mode-result audits/.mode.json > audits/.scope.json
```

`resolve-scope` reads the `audits/.mode.json` written in Phase 1.1 and turns the mode into an ordered file list; the `>` redirect captures its stdout to `audits/.scope.json` (read by `render-scope-block` and `render-agent-brief` below). For hotspot mode, also pass the ranked result so the helper extracts the top-N file list from it:

```bash
.devforge/lib/audit_helper resolve-scope --mode-result audits/.mode.json --hotspot audits/.hotspot.json > audits/.scope.json
```

Directory narrow scope walks the subtree via `git ls-files <dir>` (tracked, gitignore-respecting, polyglot-safe; filesystem fallback for non-git roots). Stdout JSON includes the resolved `scope_files` list, `file_count`, the `pipeline` depth (`simplified` for single-file; `full` for directory + uncommitted + hotspot + broad — Decision 10), and a `scope_oversize` flag (true when `file_count` exceeds `--scope-limit`, default 200 — Decision 11). Carry `scope_files`, `file_count`, and `pipeline` forward — Phase 4 reads `pipeline` to gate recurring-issues mapping, and Phase 4.5 copies `scope_files` into the report dict. On a non-empty `error` field, copy stderr VERBATIM and end the turn.

### 2.3 — Big-directory guard

If `resolve-scope` reports `scope_oversize: true`, gate before agent dispatch via AskUserQuestion (Decision 11). Question text is single-line; substitute `{N}` and `{path}` from the helper output:

> Auditing {N} files in {path} approaches broad-mode scope without --full's recurring-issues breadth. How do you want to proceed?

Options (2–4; AskUserQuestion auto-injects "Other"):

- `Risk-targeted sample` — re-run as `/audit --top 25` (recommended for periodic checks).
- `Whole codebase` — re-run as `/audit --full` (broad, with recurring-issues).
- `Proceed anyway` — continue with the current narrow scope.

On `Risk-targeted sample` or `Whole codebase`: tell the user the exact command to re-invoke and end the turn. On `Proceed anyway`: continue. When `scope_oversize` is false, proceed silently — no prompt.

### 2.4 — Render the scope block

```bash
.devforge/lib/audit_helper render-scope-block --scope audits/.scope.json --source-root <source-root>
```

Reads `audits/.scope.json` from 2.2 and produces the human-readable scope summary used in the report header (Phase 5). Substitute `<source-root>` with the Source Root from Phase 1.3 (the helper renders it into the block; `render-agent-brief` in Phase 3 takes the same `--source-root` so each agent reads from the correct location).

## PHASE 3 — Launch Adversarial Agents

```bash
.devforge/lib/audit_helper check-status-and-flip --workspace-root . --to phase3
```

Read `references/adversarial-preamble.md`, `references/mislogic-checklist.md`, and `references/best-practices-checklist.md` in full now. Their content is load-bearing and must reach each agent VERBATIM.

### 3.1 — Build each agent brief

First compute the **scope-aware finding cap** from the `file_count` in `audits/.scope.json` (Phase 2.2): `cap = min(60, max(30, file_count * 2))`. This raises the per-agent budget on dense scopes so exhaustive enumeration (the contract tells each agent to report every grounded instance of a recurring pattern, not one representative) is not choked by the flat 30-finding floor; it stays at 30 for small scopes and is bounded at 60 so a huge scope cannot blow up one agent's context. For example, a 29-file directory → `cap = 58`; a 5-file scope → `cap = 30`.

For each agent present (from Phase 1.2), passing the computed cap:

```bash
.devforge/lib/audit_helper render-agent-brief --agent <agent> --scope audits/.scope.json --source-root <source-root> --finding-cap <cap>
```

`render-agent-brief` reads `audits/.scope.json` and the reference files under `--references-dir` (default `.claude/commands/audit/references` — leave it unset, that is the installed location). `--finding-cap` (default 30) is substituted into the output contract + closing reminder wherever the cap is named. It assembles the structured brief in this order: the adversarial preamble, the mislogic checklist, the best-practices checklist (all three read verbatim from the reference files), the agent-specific focus block, the scope block (plus any `--extra-context-file` content appended to it), the output contract, and the closing mode reminder. The closing reminder is the LAST instruction in the brief so the most-recent instruction wins over the agent's baked-in polite tone.

**Constitution excerpts via `--extra-context-file` — standard for `/audit`.** The best-practices checklist's "Constitution-principle adherence" hunt only works when the constitution rules are present in the agent's brief — an agent cannot check the code against principles it cannot see. So the orchestrator SHOULD assemble a context file containing the project's constitution rules and pass it via `--extra-context-file <path>` to every agent, so each can hunt constitution-principle violations and tag them `[CONSTITUTION-VIOLATION]`. `preflight-context` (Phase 1.3) only reports whether the constitution is populated (the `constitution_populated` flag), NOT its text — so the orchestrator reads `constitution.md` directly (it lives at the workspace root, the CWD; Phase 1.3 confirms it is populated) and writes the relevant rules to a scratch file `audits/.tmp-context.md` (the `.tmp-*.md` name keeps it gitignored on first run and swept by `cleanup-tmps` in Phase 5), then passes that path. MEMORY.md pitfalls and the recurring-issues list are still-optional additions to the same context file. When no constitution rules reach the brief, agents report none from the constitution-adherence section (per the checklist), and the rest of the full-spectrum hunt is unaffected.

Pass the rendered brief as the Task tool PROMPT. Dispatching with `subagent_type: <agent>` ALREADY loads that agent's persona (`.claude/agents/<agent>.md`) as the subagent's system context — so do NOT prepend or re-inline the persona file into the brief. The persona comes from `subagent_type`; the brief carries only the audit-specific instructions on top of it. (This deviates from the stale draft, which manually prepended the persona; that predates Task subagents, which load it automatically.) The brief instructs the agent to write its findings to `audits/.tmp-<agent>.md` in the fixed parseable format the output contract specifies (so Phase 4 can regex-parse them), and to write a temp file with `# Status: failed` + a `# Reason:` line on partial failure, or `# Status: complete` + `# Finding count: 0` when it finds nothing.

### 3.2 — Batched parallel dispatch

To avoid the context-exhaustion failure mode (CHANGELOG 1.27.0 for `/verify`), dispatch in two batches, not all four at once. Each batch is multiple Task calls issued in a single turn (true parallel); wait for both to complete before the next batch.

- **Batch A** (parallel): `code-reviewer` + `architect` → both write `audits/.tmp-<agent>.md`.
- **Batch B** (parallel): `qa-engineer` + `security-reviewer` → both write `audits/.tmp-<agent>.md`.

Only dispatch agents that exist; skip the missing ones (already noted for the report). For very large scopes, run one scope partition through Batch A → Batch B before the next — do not fan out every partition in parallel.

## PHASE 4 — Consolidate, Verify, & Rank

```bash
.devforge/lib/audit_helper check-status-and-flip --workspace-root . --to phase4
```

Stream agent outputs through the helper one at a time — do NOT load all findings from all agents into context at once. Every finding is validated against the actual source before it is accepted; adversarial mode invites hallucination and grounding is the antidote.

### 4.1 — Consume + validate per agent, then combine

For each agent in `code-reviewer`, `architect`, `qa-engineer`, `security-reviewer` that wrote a temp file, parse it, extract the `findings` array, then validate that array:

```bash
.devforge/lib/audit_helper consume-tmp --tmp audits/.tmp-<agent>.md --agent <agent> > audits/.parsed-<agent>.json
# Extract the .findings array from the parsed dict into a bare JSON array:
python3 -c "import json,sys; print(json.dumps(json.load(open('audits/.parsed-<agent>.json'))['findings']))" > audits/.findings-<agent>.json
.devforge/lib/audit_helper validate-findings --findings audits/.findings-<agent>.json --repo-root . --source-root <source-root> > audits/.validated-<agent>.json
```

`consume-tmp` reads the agent temp file (`--tmp`) and regex-parses it into a result dict with `status` (`complete` / `clean` / `failed` / `missing`) and a `findings` array. `validate-findings` requires a BARE JSON array of finding dicts (it rejects a dict with exit 2), so extract `.findings` from the parsed dict first — the `python3 -c` line above does that. When `status` is `failed` or `missing`, record `{name: <agent>, reason: <reason>}` for the report dict's `agents_failed` and skip the agent (its `findings` array is empty, so it contributes nothing). `validate-findings` runs the anti-hallucination guard — file exists, line in range, evidence non-empty, pattern present, evidence quote grounded — and emits, per agent, a `passed` array (the findings that survived) plus a `discard_counts` tally (`file_missing`, `line_oob`, `evidence_empty`, `pattern_missing`, `quote_mismatch`). (Pass `--source-root` only when Source Root is a subdirectory; for `SOURCE_ROOT="."` omit it.)

After all four agents are validated, concatenate the `passed` array out of every `audits/.validated-<agent>.json` dict into one combined bare array and write it to `audits/.validated.json` (e.g. `python3 -c "import json,glob; out=[]; [out.extend(json.load(open(p)).get('passed',[])) for p in sorted(glob.glob('audits/.validated-*.json'))]; print(json.dumps(out))" > audits/.validated.json`). This combined array is what the next three steps operate on — cross-agent consensus only works when every agent's survivors are in one list. Also sum each agent's `discard_counts` (each `.validated-<agent>.json`'s `discard_counts`) by failure class into one aggregate dict (the five keys above); Phase 4.5 copies the aggregate into the report dict.

### 4.2 — Cross-agent consensus

```bash
.devforge/lib/audit_helper compute-consensus --findings audits/.validated.json > audits/.consensus.json
```

Reads the combined `audits/.validated.json` BARE ARRAY from 4.1 (it is already the concatenated `passed` arrays — no extraction needed). Exact-match grouping only (no LLM "is this similar" judgment) — findings sharing `(file, line, normalized-pattern)` across different agents merge into one consensus finding (tagged `[CROSS-AGENT]`, severity bumped one level). The helper owns the hash key and the severity bump; do not semantically dedupe in the orchestrator. Stdout (captured to `audits/.consensus.json`) is a DICT carrying `findings` (the merged working list) and `consensus_map` (`hash_key -> [agent names]`). The report dict's `consensus` key is derived from `consensus_map` — see Phase 4.5.

Extract the merged `findings` array into a bare array for the next step (`map-recurring-issues` / `force-rank-top10` both require a bare array, not this dict):

```bash
python3 -c "import json; print(json.dumps(json.load(open('audits/.consensus.json'))['findings']))" > audits/.consensus-findings.json
```

### 4.3 — Recurring-issues mapping (broad + hotspot + directory/uncommitted; skip single-file)

**Gate (Decision 10).** Recurring-issues mapping runs in broad, hotspot, and narrow-DIRECTORY/uncommitted modes; it is skipped ONLY for narrow SINGLE-FILE. The signal is the `pipeline` field from `resolve-scope` (Phase 2.2): `simplified` (single file) → SKIP this whole step (the file is its own context); `full` (directory + uncommitted + hotspot + broad) → run it.

**Step A — build the recurring payload.** Glob `specs/*/review.md` modified within the last 90 days, take the 5 most recent, and extract their Critical findings ONLY (cap 25 total across all reviews). Write them to `audits/.recurring.json` as a `[{file, fingerprint}]` list. If no reviews qualify, write `[]` and note "No recent reviews to cross-reference." in the eventual summary. Track which review files you consulted — that list becomes the report dict's `recurring_reviews_consulted`.

**Step B — map.** The `--findings` input is the working list — the bare array `audits/.consensus-findings.json` extracted at the end of 4.2, NOT raw `.validated.json` (recurring tags must layer on top of the merged list):

```bash
.devforge/lib/audit_helper map-recurring-issues --findings audits/.consensus-findings.json --recurring audits/.recurring.json > audits/.recurring-mapped.json
```

It maps each past finding against the working list — RESOLVED / RECURRING / RECURRING-SPREAD — by exact match, tags matched findings, and bumps their severity. This is the audit's differentiator over `/review`: it sees drift across features. Stdout (captured to `audits/.recurring-mapped.json`) is a DICT carrying `findings` (the working list, now recurring-tagged) and `recurring_status` (a `[{past, status}]` list). Derive the report dict's `recurring_resolved` / `recurring_unresolved` by splitting `recurring_status` on `status` (`RESOLVED` → resolved; `RECURRING` / `RECURRING-SPREAD` → unresolved). Algorithmic merging only — exact-match keys in the helper, never LLM semantic judgment. Extract the recurring-tagged `findings` array into a bare array for 4.4:

```bash
python3 -c "import json; print(json.dumps(json.load(open('audits/.recurring-mapped.json'))['findings']))" > audits/.working.json
```

When this step is SKIPPED (single-file `simplified` pipeline), use `audits/.consensus-findings.json` from 4.2 as the working list for 4.4 instead, and set the report dict's `recurring_resolved`, `recurring_unresolved`, and `recurring_reviews_consulted` to `[]`.

### 4.4 — Force-rank the Top N

The `--findings` input is the bare-array working list from the previous step — `audits/.working.json` when 4.3 ran, else `audits/.consensus-findings.json` (the single-file skip case). Add `--narrow` ONLY for the single-file `simplified` pipeline (Top 5 instead of Top 10):

```bash
.devforge/lib/audit_helper force-rank-top10 --findings audits/.working.json [--narrow] > audits/.ranked.json
```

Scores survivors by severity × confidence × cross-agent × recurring weights and returns the ordered top slice. Deterministic given the working list. Stdout (captured to `audits/.ranked.json`) is a DICT carrying `top` — an ordered `[{finding, score}]` list (length 10, or 5 with `--narrow`). The report dict's `findings` and `top10` are BOTH derived from the SAME bare-array working list you just ranked (`audits/.working.json`, or `audits/.consensus-findings.json` on the single-file skip) plus this ranking — see Phase 4.5.

### 4.5 — Assemble the report dict

Assemble the `render_report` input dict and write it to `audits/.report.json`. This is the single bundle `render-report` and `render-inline-summary` both consume.

**Finding-id assignment first.** The helper auto-assigns `finding_id` (`F-001`, `F-002`, …) in document order only at render time, so to build the `top10` and `consensus` keys (both keyed by finding_id) the orchestrator must assign the SAME ids up front. Take the FULL bare-array working list — `audits/.working.json` when 4.3 ran, else `audits/.consensus-findings.json` — and assign `finding_id` = `F-001`, `F-002`, … in that exact order. This id-assigned list is the report dict's `findings`.

Then build the rest, each value sourced from an earlier step:

| Key | Source |
|---|---|
| `mode` | Phase 1.1 `audits/.mode.json` `mode` |
| `audit_date` | today's date `YYYY-MM-DD` (also passed via `--date` in Phase 5) |
| `scope_description` | Phase 2.4 `render-scope-block` stdout |
| `scope_files` | Phase 2.2 `audits/.scope.json` `scope_files` |
| `agents_run` | Phase 1.2 `check-agents` `present` |
| `agents_skipped` | Phase 1.2 `check-agents` `missing` |
| `agents_failed` | Phase 4.1 — agents whose `consume-tmp` `status` was `failed` or `missing`, as `[{name, reason}]` |
| `findings` | the id-assigned full working list (above) |
| `top10` | the `finding_id`s of `audits/.ranked.json`'s `top` entries, in order — match each `top[i].finding` to its assigned id by `(file, line, pattern, agent)` |
| `consensus` | `audits/.consensus.json` `consensus_map` re-keyed from hash → finding_id: for each hashed group, the matching finding's assigned `finding_id` maps to that group's agent list |
| `recurring_resolved` | Phase 4.3 — `recurring_status` entries with `status == "RESOLVED"` (skipped → `[]`) |
| `recurring_unresolved` | Phase 4.3 — `recurring_status` entries with `status` in `RECURRING` / `RECURRING-SPREAD` (skipped → `[]`) |
| `recurring_reviews_consulted` | Phase 4.3 Step A consulted review paths (skipped → `[]`) |
| `discard_counts` | Phase 4.1 aggregate across all four agents |
| `source_root` | Phase 1.3 `preflight-context` |
| `framework` | Phase 1.3 `preflight-context` |
| `language` | Phase 1.3 `preflight-context` |
| `next_candidates` | Phase 2.1 `audits/.hotspot.json` `next_candidates` (hotspot only; omit otherwise) |

The key names above are the exact ones `render_report` reads — do not rename or add keys it does not consume. (`render-inline-summary` reads the same dict plus an optional `out_path`; set `out_path` to the path `render-report` prints, before calling Phase 6.)

## PHASE 5 — Write Report

```bash
.devforge/lib/audit_helper check-status-and-flip --workspace-root . --to phase5
```

```bash
.devforge/lib/audit_helper render-report --report audits/.report.json --audits-dir audits --date <YYYY-MM-DD>
```

Reads the assembled `audits/.report.json` from Phase 4.5, renders the full audit markdown (skeleton documented in `references/report-format.md`), and writes it to `audits/YYYY-MM-DD-audit.md` at the workspace root, appending `-2`, `-3`, … on a same-day collision. The helper creates `audits/` and a first-run `audits/.gitignore` (`.tmp-*.md`) as needed. Stdout reports the exact written path.

```bash
.devforge/lib/audit_helper cleanup-tmps
```

`cleanup-tmps` deletes `audits/.tmp-*.md` only (it globs that pattern; it never touches the report or `.gitignore`). The intermediate JSON scratch files are NOT covered by the `.tmp-*.md` gitignore pattern — but Phase 6's `render-inline-summary` still needs `audits/.report.json`, so the scratch-JSON deletion happens at the END of Phase 6, not here.

**Do NOT commit. Do NOT stage.** Let the user decide whether to keep the audit in git history. (The run is marked `complete` only at the very end of Phase 6, once the report is written AND the summary is shown — see below.)

## PHASE 6 — Present Inline Summary

```bash
.devforge/lib/audit_helper render-inline-summary --report audits/.report.json
```

`render-inline-summary` reads the same report dict as `render-report` (set its `out_path` to the path `render-report` printed in Phase 5 so the block can cite the file). It prints the count-first inline block — total findings by severity, cross-agent consensus count, recurring-unresolved count, agents skipped, findings discarded by validation, the Top 5 priorities, and the report path. This follows the audit-format discipline (count first; the most important findings named). Copy the helper's stdout VERBATIM into your final user-facing message as a fenced code block, then tell the user the report is not committed — review, then commit if they want audit history in git, or delete.

Finally, delete the intermediate JSON scratch files (gitignored only via the explicit `rm`, not the `.tmp-*.md` pattern):

```bash
rm -f audits/.mode.json audits/.callers.json audits/.hotspot.json audits/.scope.json \
      audits/.parsed-*.json audits/.findings-*.json audits/.validated-*.json audits/.validated.json \
      audits/.consensus.json audits/.consensus-findings.json audits/.recurring.json \
      audits/.recurring-mapped.json audits/.working.json audits/.ranked.json audits/.report.json
```

Then mark the run complete so an interrupted re-run can distinguish a finished audit from a stopped one:

```bash
.devforge/lib/audit_helper check-status-and-flip --workspace-root . --to phase6 --status complete
```

## Important rules

1. **Read-only** — no source modifications, no fixes, no auto-commit of the report.
2. **Standalone** — `/audit` is never invoked by another command, never part of any chain, never auto-triggered.
3. **Grounded adversarial bias** — false positives are acceptable ONLY when grounded in a verbatim quote from real code; `validate-findings` discards ungrounded ones.
4. **Constitution violations are always Critical** — never downgraded, regardless of confidence.
5. **Critique code, not people** — findings describe what is wrong with the code, never who is wrong.
6. **Algorithmic merging only** — consensus + recurring tags are exact-match hash keys in the helper, never LLM semantic judgment.
7. **Dated reports, not overwritten** — same-day re-runs append a numeric suffix; history is preserved.
8. **Not committed** — temp files are gitignored on first run; the user owns the keep/delete decision.
9. **Context-aware batching** — two-batch dispatch + stream consolidation; never fan out all agents on all files at once, never load all findings into context at once.
10. **Skip missing agents gracefully** — note them in the report; fail only if all four are missing.
11. **Wrapper-mode aware** — pass Source Root to every agent for source files; `audits/` always lives at the workspace root.
