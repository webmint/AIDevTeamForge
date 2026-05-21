# /specify redesign plan

Status: planning. Promoted from WATCHLIST (SPECIFY-PLAN.md) on user signal — SDD-drift concern + framework-parity push.
Active branch: `develop-2.0-init` (or successor — confirm at session start).

## Baseline

**Sole baseline = v3 spec at `/Users/mykolakudlyk/Projects/doosan/cse-strata-ws-forge/.claude/commands/specify.md`** (371 lines). v3 header documents v1→v2→v3 evolution explicitly. v2 added mandatory `research/` + `specs/` reads, Phase 1.5 findings enumeration, decision-point coverage across 7 categories, spec-type classification, 7-subsection AC, numerical-verification rule. v3 added mode-dependent execution path (auto vs interactive), `AskUserQuestion` tool preference, Phase 1.5-finding coverage rule. v3 is the empirically-tuned version.

**Devforge `src/_pending/commands/specify.md` is ignored.** Earlier plan rev wrongly used it as baseline. Discarded.

**Parity-test history** (Obsidian `parityTest/4-way comparison results - spec 007.md`): v1 ran 4-way parity test 2026-04-29 against cse-strata-ws-forge + copies B/C/D. Mean composite deviation = ~15% on v1. Mitigations proposed: (1) mandate clarifying-question surfacing, (2) mandate input frame, (3) self-consistency check on counts. Predicted post-mitigation = 6-8%. v2 implemented all three mitigations + adds Phase 1.5; v3 adds mode-dependent path. User reports ≤5% variance on subsequent runs — v3 empirical result, not v1.

## Why redesign

Two converging pressures:

1. **Framework parity** — `/init-forge`, `/generate-docs`, `/configure`, `/constitute` all use helper-owns-shape + schema + setters + per-answer persistence (per `feedback_helper_owns_shape_principle`). v3 `/specify` is orchestrator-direct with inline instructions; the discipline lives in prose rules (Rules 8-10), not enforced by code. Framework standard = code-level enforcement.
2. **Upstream commands** — `/discover` (DISCOVER-PLAN.md) saves to `discover/<date>-topic.md`; `/research` redesign (REDESIGN-RESEARCH-PLAN.md) saves to `research/<date>-topic.md`. Neither emits a structured handoff block — they save plain md files and tell the user "Run `/specify "<prompt>"`; reference: <path>". v3 already enumerates `research/`; v3.1 adds `discover/` enumeration. /specify reads these files as Phase 1 input sources and produces Phase 1.5 findings from their content uniformly. Path-based tagging only — no content parsing for structured fields.

Goal: convert v3 prose discipline into helper-enforced code discipline + add `discover/` to Phase 1 input list + path-based source tagging for spec-type pre-seeding. Net behavior preserves v3 mechanics; enforcement shifts from prose to validators.

## Variance preservation — hard constraint

v3 empirical: variance ≤5% across 4 measured axes (structural drift / AC count / output length / decision-drift) on 4 instances × 8 runs = 32 runs of canonical input case. Achieved through iterative tuning on v1→v2→v3.

Helper-owns-shape pattern is variance-reducing on axes 1-3 (structure determinism → ~0%, coverage rules bound count, closed enums bound length). Axis 4 (decision-drift) is where v3 prose discipline did its work — must preserve.

The following **10 rules** are non-negotiable:

1. **Decision-point categories = same 7 verbatim** from v3 Phase 2: `scope_boundaries`, `existing_behavior`, `data_flow_state`, `edge_cases`, `ui_ux_details`, `breaking_changes`, `tooling_configuration`. Same order. Same definitions. No new categories invented.
2. **Phase 1 read list = 6 v3 verbatim + 1 v3.1 addition** (7 total): (1) `constitution.md` + populate-guard, (2) `.claude/memory/MEMORY.md`, (3) `CLAUDE.md`, (4) `docs/` tree (architecture + packages/apps + topic-relevant md), (5) `research/` enumerated (every relevant file, recent first), (6) `discover/` enumerated (v3.1 addition — divergence documented in Appendix A "SDD-adopt prose blocks"), (7) `specs/` enumerated (prior related specs). v3 sources unchanged in order or definition; `discover/` slots as #6 and shifts `specs/` to #7.
3. **Phase 1.5 mandatory** — REQUIRED INTERMEDIATE OUTPUT to conversation (not file), structured findings per source, ≥3 bullets if file read and relevant, "No items relevant" if read but irrelevant, omit if not read. Helper validates count + structure before Phase 2 unlocks.
4. **AC categorization = same 7 subsections verbatim** from v3 Phase 4 Section 5: `tooling_artifact_presence` (5.1), `behavior_preservation` (5.2), `behavior_change` (5.3), `ci_pipeline` (5.4), `hooks_gates` (5.5), `documentation` (5.6), `hygiene` (5.7). Each subsection: ≥1 AC OR explicit `N/A — [reason]`. Helper validates.
5. **Coverage rule = enforced** — every Phase 1.5 finding must land as AC (§5) OR Constraint (§7) OR Out-of-Scope (§6) OR Risk (§9). Unlanded finding = hard error from helper `verify-coverage` subcommand.
6. **Numerical verification = enforced** — Rule 8 in v3. Every count/size/version/line-number in spec verified by direct Bash enumeration before write. Inconsistent numbers across sections = hard error. Helper `verify-numerical-consistency` runs grep over rendered spec + cross-checks counts.
7. **Decision-point exhaustiveness = enforced** — Rule 10 in v3. Every decision point with ≥2 valid implementations gets a clarifying question OR explicit `[default applied]` (auto mode) OR `out-of-scope`/`open-question` entry. Helper `verify-decision-coverage` validates.
8. **Mode-dependent execution path — C-strict detection rules**. Helper detects auto mode iff ANY of these three signals fire:
    - `os.environ.get("DEVFORGE_AUTO_MODE") == "1"`
    - `--auto` flag passed on /specify invocation
    - Substring match (case-insensitive) for `"auto mode is active"` OR `"auto mode still active"` in the latest `<system-reminder>` block of the conversation (orchestrator parses, passes bool to helper)

    User natural-language prose ignored — no LLM judgment in mode detection. User who wants auto must opt in via flag or env var. Pause-when-uncertain (Variance rule #8 v3 verbatim) preserved: helper defaults to interactive when no signal fires.

    Interactive path: AskUserQuestion preferred (single-line questions only per `feedback_askuserquestion_single_line_only`), markdown fallback (numbered list with (a)(b)(c) alternatives + named default), bundling for ≥4 related questions. Helper owns mode detection + Phase 2 enforcement (rejects `default_applied` setter in interactive); orchestrator owns presentation logic (AskUserQuestion vs fallback). v3 prose preserved verbatim where it describes presentation + bundling discipline.
9. **LLM-facing prose preserved verbatim** from v3 wherever it controls LLM behavior — Phase 1.5 enumeration framing, Phase 2 decision-point definition + stop rule + AskUserQuestion+fallback discipline, Phase 4 AC subsection examples, Phase 5 approval-summary 4-bullet block, Rules 1-10 verbatim. Diff with v3 baseline; any prose deviation requires explicit re-tune justification logged in plan. **Exception**: SDD-adopt prose blocks (EARS framing, constitution-recheck framing, test_anchor framing, resolve-open-question framing) are v3.1 additions — documented as divergence in Appendix A.
10. **AC statement = EARS notation** (Kiro / IEEE 29148-2018 SDD convention). Every `AcceptanceCriterion.statement` field matches one of 5 EARS variants:

    | Variant | Pattern | Use when |
    |---|---|---|
    | Ubiquitous | `The <system> shall <response>.` | always-true requirement |
    | Event-driven | `WHEN <trigger> the <system> shall <response>.` | event response |
    | State-driven | `WHILE <state> the <system> shall <response>.` | state-dependent behavior |
    | Optional | `WHERE <feature> the <system> shall <response>.` | feature-flag / conditional |
    | Unwanted | `IF <trigger>, THEN the <system> shall <response>.` | unwanted-behavior prevention |

    Helper `verify-ac-shape` validates pattern via regex per variant; rejects malformed `statement`. **Subsection-specific constraints**:
    - **§5.1 (tooling_artifact_presence)** and **§5.7 (hygiene)**: `ears_variant` MUST be `ubiquitous` (closed enum on these two subsections — other variants don't fit always-true presence/absence requirements). Both `statement` (EARS Ubiquitous, e.g., "The repository shall contain no occurrences of `lerna`.") AND `verification_command` (executable check, e.g., `grep -r "lerna" returns 0 matches`) are REQUIRED. Helper rejects on partial.
    - **§5.2–§5.6**: any of 5 EARS variants allowed; `verification_command` optional.

These 10 rules pinned into spec body verbatim. Any deviation = variance test failure.

## Empirical variance gate — DEFERRED

Variance verification (re-run v3 4-instance × 8-run protocol on rewrite, measure 4 axes, confirm ≤5%) is **deferred to future work**, not gated on this redesign's merge.

Rationale:
- /specify primary input path = generated by /research or /discover (per design intent + DISCOVER-PLAN + REDESIGN-RESEARCH-PLAN handoff blocks). Real upstream output needed for clean variance measurement. Upstream ship date = not soon.
- Building to Step 8 (functional empirical test on testForge20) does not require real upstream output — synthetic handoff fixtures matching plan schemas suffice for pipeline validation.
- Variance gate becomes a follow-up task triggered when upstream ships AND a canonical input case is selectable.

Variance preservation rules (10 rules above) remain in force as design discipline regardless. Rules govern code + spec writing; gate confirms they hit numerical target. Rules survive without the gate; gate cannot survive without the rules.

Follow-up plan when run: re-introduce gate as separate plan (SPECIFY-VARIANCE-GATE-PLAN.md) once /discover OR /research-redesign ships.

## Scope locked

1. Convert v3 spec to helper-owns-shape + per-setter persistence.
2. New `specify_helper.py` at `src/devforge/lib/specify_helper.py`. Schema = `SpecDoc` (v3 9-section template) + `FindingsLog` (Phase 1.5) + `DecisionPointLog` (Phase 2) + `SpecTypeClassification` (Phase 3).
3. Adapter = path-based source tagging on Phase 1 reads. Files in `discover/` → `source_origin="discover"` → pre-seeds spec_type=`greenfield_feature` in Phase 3. Files in `research/` → `source_origin="research"` → no pre-seed. No content parsing for structured handoff fields.
4. AC categorized by 7 subsections; each AC has verification command.
5. Orchestrator-direct dialogue (no new subagent — see Agent ownership).
6. Output preserved: `specs/NNN-feature-name/spec.md` + branch `spec/NNN-short-desc`.

## Naming locked

`/specify` — unchanged. Command file lives at `src/commands/specify/main.md` after Step 6.

## Prerequisites (hard gate)

`/specify` refuses to run unless all setup-chain commands have completed. Helper `preflight` subcommand checks four artefacts at startup; exits non-zero with explicit instruction if any missing:

| Required artefact | Produced by | Hard-gate check |
|---|---|---|
| `.devforge/init.yaml` | `/init-forge` | File exists + non-empty |
| `docs/architecture.md` | `/generate-docs` | File exists + non-empty |
| `.devforge/configure.yaml` | `/configure` | File exists + non-empty |
| `constitution.md` | `/constitute` | File exists + non-empty + does not contain `_Run /constitute to populate_` literal (v3 guard preserved) |

Artefact filenames mirror `discover_helper.PREFLIGHT_PREREQS` and `research_helper.PREFLIGHT_PREREQS` exactly — single source of truth for "what the 4-command setup chain writes". `.devforge/project-config.json` exists too (rendered by `/configure render-config` from `configure.yaml` + `init.yaml` + 3 derived keys) but is a downstream artefact, not the configure gate.

On missing artefact, helper emits:

```
BLOCKED: /specify requires the full 4-command setup chain.
Missing: <artefact>
Run: /init-forge → /generate-docs → /configure → /constitute, then retry /specify.
```

Exit code 2. No graceful skip, no fallback path. Mirrors `/discover` + `/research` hard gate.

## Phases (target order, mirrors v3)

```
PHASE 0:   Branch setup + session-state reset       ← helper preflight subsumes v3 Phase 0 + Pre-Step
PHASE 1:   Input reads (6 sources)                  ← v3 Phase 1 verbatim; helper enforces read completeness
PHASE 1.5: Findings enumeration                     ← REQUIRED INTERMEDIATE OUTPUT; helper validates structure
PHASE 2:   Decision-point coverage (7 categories)   ← mode-dependent (auto/interactive); helper validates exhaustiveness
PHASE 3:   Codebase analysis                        ← spec-type classify + per-type mandatory reads + CBM
PHASE 4:   Write spec (render via helper)           ← helper renders 9-section markdown with 7-subsection AC; coverage rule enforced
PHASE 5:   Approval + branch + /plan handoff        ← hard-gate approval; deterministic summary; handoff block
```

## Existing-code awareness layer (docs + CBM/MCP + research/specs/)

`/specify` consults **three layers** when reasoning about existing code:

### Layer 1: docs/ narrative context

Read in Phase 1 + Phase 3:
- `docs/architecture.md` — project-tier architecture
- `docs/<package>/architecture.md` — package-tier architecture per affected package
- `docs/<package>/<concern>/index.md` — concern md for relevant area
- `docs/glossary.md` — term grounding
- `docs/<source-root>/packages/**/*.md` + `docs/<source-root>/apps/**/*.md` — topic-relevant scan (v3 explicit)
- All other topic-relevant `.md` files (v3 explicit)

### Layer 2: research/ + discover/ + specs/ enumerated reads

`research/` enumeration (v3 verbatim mechanic; criterion tightened to filename-only per Variance rule #5):
- `ls research/` → enumerate filenames.
- Read every file whose filename has substring overlap with task-topic tokens (≥1 token overlap on whitespace-split filename slug). No content match in adapter.
- Record paths read.
- Most-recent files (by date prefix) prioritized when multiple match.
- /research output lands here per REDESIGN-RESEARCH-PLAN Phase 3 save.

`discover/` enumeration (v3.1 addition; NOT in v3 — divergence documented in Appendix A):
- `ls discover/` → enumerate filenames.
- Same filename-substring criterion as research/.
- /discover output lands here per DISCOVER-PLAN Phase 3 save.

`specs/` enumeration (v3 verbatim):
- `ls specs/` → enumerate prior spec directories.
- Read `spec.md` of any prior spec on related topic.
- Captures: decisions made, out-of-scope items established, AC patterns.

**No structured-handoff parsing**. /research and /discover save plain md files; /specify reads them like any other md. Source signal comes from PATH only — file in `discover/` ↔ /discover origin; file in `research/` ↔ /research origin. Path drives Phase 3 spec-type pre-seeding (see Phase 3 Step 1 below); content drives Phase 1.5 findings (see Phase 1.5).

### Layer 3: CBM/MCP structural queries

Called in Phase 3 codebase analysis:
- `agentic_context "<feature scope>"` — synthesized bundle (when LLM mode enabled).
- `search_graph(name_pattern=..., label=..., qn_pattern=...)` — named symbols (File-label queries use `name_pattern` per `feedback_cbm_search_graph_pattern_keys`).
- `search_code(pattern=...)` — text fallback for inline framework expressions (mandatory chain per `feedback_cbm_discovery_chain_search_graph_then_code`).
- `trace_path(function_name, mode=calls|data_flow|cross_service)` — impact analysis on affected surfaces.
- `get_code_snippet(qualified_name)` — read source (NOT raw Read/cat).

**v3 Phase 3 prefers Glob/Grep tools over Bash grep/find** for audit trail. Helper records tool selection in `.devforge/specify-tool-log.json` for debugging variance issues.

### Runtime enforcement (hooks already shipped)

Same 4 hooks at `src/hooks/` (per `project_track1_f11_hooks_shipped`):

- `cbm-session-reminder` (SessionStart)
- `cbm-code-discovery-gate` (PreToolUse Read|Grep|Glob)
- `bash-ban-raw-tools` (PreToolUse Bash)
- `cbm-mcp-marker` (PostToolUse Bash|mcp__codebase-memory-mcp__.*)

Spec body MUST instruct orchestrator to use CBM tools by name in Phase 3.

### Preflight gate

Phase 0 calls `./.devforge/lib/specify_helper preflight`. Skip if `.devforge/.preflight-stamp` is fresher than 60s. Ensures CBM index is current + hard-gate artefacts exist. Reuses stamp from `/generate-docs` preflight.

## Phase 0: Preflight + branch + session-state reset

Goal: collapse v3 Phase 0 (branch setup) + Pre-Step (session-state reset) into one helper-driven preflight.

**Helper subcommand `preflight`**:

1. Checks hard-gate artefacts per Prerequisites table; exit 2 + verbatim message on missing.
2. Checks git state via `git rev-parse --is-inside-work-tree`; exit 2 + v3 verbatim message on non-repo.
3. Detects current branch (`git branch --show-current`) + default branch via v3 method order: (i) `git symbolic-ref refs/remotes/origin/HEAD`, (ii) check `main` ref, (iii) check `master` ref, (iv) ask user.
4. Resets `.claude/session-state.md` to v3 verbatim placeholder content.
5. Returns structured JSON: `{preflight_pass, current_branch, default_branch, branch_decision, hard_gate_missing}`.

**Branch decision logic (v3 verbatim)**:
- Already on `spec/*` → skip.
- On default → generate 2-3 word kebab-case slug from `$ARGUMENTS`; defer branch creation to Phase 4 (matches spec NNN).
- On other branch → ask user via v3 verbatim prompt (3 options).

**Persistence**: Phase 0 outputs persisted to `.devforge/specify-state.json` so Phase 1+ resumes on kill.

## Phase 1: Input reads

Goal: read all 7 input sources (6 v3 verbatim + `discover/` v3.1 addition). **All bullets are required if the file/directory exists. Do not skip discretionarily** (v3 verbatim).

**Helper subcommand `record-input-read`** called per source:

1. `constitution.md` — read + check populate-guard (`_Run /constitute to populate_`). If guard present → exit 2 with v3 verbatim block message.
2. `.claude/memory/MEMORY.md` — read.
3. `CLAUDE.md` — read.
4. `docs/` tree — read per Layer 1 list.
5. `research/` — enumerate via `ls research/`. Read every file whose **filename** has substring overlap with task-topic tokens (helper-side string match; ≥1 token overlap on whitespace-split filename slug). No content match in adapter — Variance rule #5 (no LLM re-interpretation in adapter). LLM may widen scope in Phase 3 discretionary exploration; those reads do not count as Phase 1 reads. Record paths.
6. `discover/` (v3.1 addition) — enumerate via `ls discover/`. Same filename-substring criterion as research/. No content match in adapter. Record paths.
7. `specs/` — enumerate via `ls specs/`. Read `spec.md` of any prior spec directory whose name has substring overlap with task-topic tokens. Record paths.

**Path-based source tagging** (no content parsing):

When recording an input read, helper auto-tags by path:
- File path starts with `discover/` → `source_origin: "discover"`
- File path starts with `research/` → `source_origin: "research"`
- File path starts with `specs/` → `source_origin: "prior_spec"`
- Other → `source_origin: "context"` (constitution, MEMORY, CLAUDE, docs)

`source_origin` drives Phase 3 spec-type pre-seeding (only `discover` triggers a seed; see Phase 3 Step 1). Otherwise, all reads feed Phase 1.5 findings uniformly.

**No structured-handoff parsing.** /research and /discover save plain md files with their own internal shape (per REDESIGN-RESEARCH-PLAN + DISCOVER-PLAN Phase 2 report shapes). /specify reads them as-is and produces findings; does NOT attempt to extract structured fields. Variance rule #5 preserved (no LLM re-interpretation in adapter — content goes straight into Phase 1.5 enumeration where standard ≥3-bullet rule applies).

Phase 1.5 findings from `discover/` files include any Key-facts bullets present (functional_scope, users, success_criteria, recommended option, open uncertainties, etc.) as ordinary findings — they pass through the ≥3-bullet rule like any other content. The literal `/specify "<distilled topic>"` line at the top of a /discover Next-step block is the user's manual handoff text in the source doc — NOT an instruction to recurse. Helper treats it as plain prose; orchestrator does not re-invoke /specify on it.

**Persistence**: each `record-input-read` writes to `.devforge/specify-state.json` (path + source_origin + read_timestamp). Kill-resume safe.

## Phase 1.5: Findings enumeration (REQUIRED INTERMEDIATE OUTPUT)

Goal: convert implicit recall into explicit enumeration. v3 calls this "the bridge between reading and writing; without it, content silently drops." Dominant variance source on v1.

**Helper subcommand `record-finding`** called per finding:

Schema:
```python
class Finding(BaseModel):
    finding_id: str           # e.g., "F-constitution-1"
    source_path: str          # e.g., "constitution.md", "research/2026-04-15-xyz.md"
    source_section: str       # subheading or section label
    content: str              # the finding text
    landed_in: Literal["AC", "Constraint", "OOS", "Risk", "unlanded"] = "unlanded"
    landed_ref: str = ""      # e.g., "AC-3", "§7.1"
```

**Validation rules** (helper `verify-findings`):
- Each input source read in Phase 1 produces a Findings section.
- Required ≥3 bullets if source was read AND has task-relevant content.
- `No items relevant to this spec.` permitted when source read but irrelevant (≥3-bullet rule waived).
- Source not read → section omitted entirely.

**Output format** (rendered by helper `render-findings` for user echo, v3 verbatim format):

```
## Findings from Inputs

### From constitution.md
1. [content]
2. [content]
3. [content]

### From .claude/memory/MEMORY.md
1. ...

### From research/<filename> (if read)
1. ...

### From discover/<filename> (if read)
1. ...

### From CLAUDE.md
1. ...

### From docs/<filename> (if read)
1. ...

### From specs/<prior-spec>/spec.md (if read)
1. ...
```

**Verbatim echo directive** (per `feedback_verbatim_echo_directive`): orchestrator copies helper output VERBATIM into next user-facing message as fenced code block. No paraphrase.

**Gate**: `findings-finalize` returns non-zero unless every read source has either ≥3 findings OR "No items relevant" marker. Phase 2 cannot start until exit 0.

**Persistence**: every `record-finding` call writes to `.devforge/specify-state.json`.

## Phase 2: Decision-point coverage (7 categories)

Goal: surface every decision point with ≥2 valid implementations. Helper enforces exhaustiveness across 7 categories.

**v3 "Decision Point" definition (verbatim)**: any choice whose outcome would change at least one entry in the eventual spec's Acceptance Criteria, Affected Areas, Out-of-Scope, Technical Constraints, or Risks.

**7 categories (v3 verbatim, Variance rule #1)**:

1. `scope_boundaries` — does this affect related area X, related area Y, or only specific area Z?
2. `existing_behavior` — for each existing behavior in affected area, must it be preserved, modified, or replaced?
3. `data_flow_state` — for each new piece of state or data, where does it come from?
4. `edge_cases` — empty input, error condition, concurrent operations, etc.
5. `ui_ux_details` — loading state, error message, confirmation, accessibility, mobile.
6. `breaking_changes` — every behavior change might affect downstream consumers; for each, is the break acceptable or must compatibility be preserved?
7. `tooling_configuration` — migration / config-change / infrastructure specs: every config change has options (proactive vs reactive, opt-in vs opt-out, default vs explicit).

**Helper subcommand `record-decision-point`**:

Schema:
```python
class DecisionPoint(BaseModel):
    dp_id: str                 # e.g., "DP-scope-1"
    category: Literal["scope_boundaries", "existing_behavior", "data_flow_state",
                      "edge_cases", "ui_ux_details", "breaking_changes",
                      "tooling_configuration"]
    description: str
    valid_implementations: list[str]  # ≥2 entries (else no DP)
    status: Literal["pending", "answered", "default_applied", "deferred_OOS",
                    "deferred_open_question", "no_DP_in_category"]
    user_answer: str = ""
    default_applied: str = ""
    deferral_reason: str = ""
```

**Per-category requirement (Variance rule #7)**:
- For each of 7 categories: identify whether request creates decision points.
- If yes → ≥1 DecisionPoint with `status != no_DP_in_category`.
- If no → record one DecisionPoint with `status = no_DP_in_category` + reason ("Category X: no decision point — already determined by [Y]") — lands in §8 Open Questions of spec.

**Per-category coverage state enum** (mirrors /discover + /research Clear/Partial/Missing taxonomy; aligned with GitHub Spec Kit clarify taxonomy per <https://github.com/github/spec-kit/blob/main/templates/commands/checklist.md>):

| Category state | Meaning |
|---|---|
| `Clear` | ≥1 DecisionPoint with `status ∈ {answered, default_applied, deferred_OOS, deferred_open_question}` (rule applied: deferred entries count as Clear because user/auto made an explicit landing decision) |
| `Partial` | ≥1 DecisionPoint with `status == pending` (asked but unresolved) AND no Clear DP in this category yet |
| `Missing` | No DecisionPoints recorded for this category |
| `NoDPInCategory` | Single `no_DP_in_category` DecisionPoint recorded with reason (terminal state — counts as Clear for coverage purposes) |

Helper `rubric-coverage` returns `{category: state}` map. `rubric-finalize` exits 0 iff all 7 categories ∈ `{Clear, NoDPInCategory}`; non-zero on any `Partial` or `Missing`.

**Per-DP turn cap** (mirrors /discover 3/dim):
- Hard cap = 3 follow-ups per DecisionPoint.
- After cap, helper auto-transitions DP to `status=deferred_open_question` with `deferral_reason="exceeded follow-up cap"`.
- DP lands in §8 Open Questions with [exceeded cap] marker.
- Prevents indefinite loops on stubborn DPs.

**Mode-dependent execution path (Variance rule #8 — C-strict)**:

Helper `detect-mode`. Auto mode iff ANY:
- `os.environ.get("DEVFORGE_AUTO_MODE") == "1"`
- `--auto` flag on /specify invocation
- Case-insensitive substring match for `"auto mode is active"` OR `"auto mode still active"` in latest `<system-reminder>` block (orchestrator detects, passes bool to helper)

Otherwise interactive. User natural-language prose NOT a signal — no LLM judgment in mode detection.

Auto path:
- For each DecisionPoint, helper accepts setter with `status=default_applied` + named default in `default_applied` field.
- Orchestrator drafts defaults from Phase 1.5 findings + model recommendation.
- Spec §8 marks each entry `[default applied]`.
- Phase 5 approval gate surfaces all `[default applied]` entries for user review.

Interactive path:
- Helper rejects setter with `status=default_applied` (exit 2 + message "Interactive mode — DP requires user answer or explicit deferral").
- Orchestrator presents via `AskUserQuestion` (preferred) or numbered markdown fallback.
- Bundling: ≥4 related questions → single `AskUserQuestion` call (multi-question form).
- Wait for answers before proceeding.

When uncertain about mode → prefer pausing (interactive default). Asking is reversible; proceeding without input is not (v3 verbatim).

**Stop rule (v3 verbatim, Variance rule #7)**:
- Helper `verify-decision-coverage` checks: every category state ∈ `{Clear, NoDPInCategory}` (per per-category coverage state enum above).
- Any category in `Partial` or `Missing` state → exit 2.
- Coverage achieved → exit 0.

**Question rounds**:
- Up to 5 questions per round.
- Prioritization order (v3 verbatim): scope > breaking changes > data flow > tooling > UX > edge cases.
- After each round, decide if more clarification needed based on **whether all decision points have been covered, not on subjective sufficiency** (v3 verbatim).

**Question discipline (v3 verbatim)**:
- Only ask questions you CANNOT answer by reading the codebase or Phase 1.5 findings.
- Stop only when every DP has answer OR explicit OOS/open-question entry.

**Persistence**: every `record-decision-point` + answer write to `.devforge/specify-state.json`.

## Phase 3: Codebase analysis (spec-type classification + per-type reads)

Goal: classify spec type, read mandatory per-type files, supplement with CBM/Glob/Grep exploration.

**Step 1 — Spec-type classification (v3 + greenfield 5th type)**:

Helper subcommand `classify-spec-type` accepts:
```python
class SpecTypeClassification(BaseModel):
    spec_type: Literal["migration_tooling", "feature_addition", "bug_fix", "refactor", "greenfield_feature"]
    rationale: str
    seeded_by_upstream: bool = False  # True when Phase 1 adapter pre-seeded from /discover or /research handoff
```

Classification stated at start of Phase 3 output.

**Upstream pre-seeding** (path-based, from Phase 1 source_origin tags):
- Any Phase 1 input has `source_origin == "discover"` → adapter calls `classify-spec-type` with `spec_type="greenfield_feature"` + `seeded_by_upstream=True`. Rationale: "/discover scope-locked to greenfield (per DISCOVER-PLAN); a discover/ file read implies greenfield origin."
- Only `source_origin == "research"` or `"prior_spec"` Phase 1 inputs (no discover) → **no pre-seeding**. /research is neutral on bug/enhancement/refactor; Phase 3 LLM classifies from research report content.
- Cold mode (no research/, no discover/) → no pre-seeding; Phase 3 LLM classifies.

Pre-seeding uses path signal only — no content parsing, no LLM re-interpretation (Variance rule #5 preserved). Helper allows Phase 3 override of /discover seed only with explicit user confirmation via AskUserQuestion ("Upstream is /discover → spec_type=greenfield_feature; override?").

**Step 2 — Mandatory read list per spec type (v3 verbatim)**:

| Spec type | Mandatory reads |
|---|---|
| `migration_tooling` | Root `package.json`, every `.github/workflows/` file, every per-package `package.json` with peerDependencies/dependencies/workspace links, hook configs (`.husky/`, `.pre-commit-config.yaml`, `.lefthook.yml`), all monorepo configs (`lerna.json`, `turbo.json`, `nx.json`, `pnpm-workspace.yaml`, `rush.json`), all lockfiles (note presence/size only), root `.npmrc` / `.yarnrc` / `.pnpmrc` |
| `feature_addition` | Root component/entry files (router, store, app init), most-similar existing feature (via grep), type defs for affected entities, API/GraphQL ops for affected resources, test files for affected area |
| `bug_fix` | The buggy file(s) named in request, direct deps of buggy file, direct callers (via grep), recent git log on buggy file (`git log -5 -- path/to/file`) |
| `refactor` | The file(s) being refactored, all callers (via grep), all tests for refactored code |
| `greenfield_feature` | Constitution Section 7 (Scaffolding Guide), framework docs via WebSearch for feature pattern, MEMORY.md prior-feature lessons, /discover reference md (if Phase 1 adapter loaded one — read full report for context). Does NOT include grep-similar-feature or read-callers (nothing exists yet). |

Helper subcommand `record-mandatory-read` accepts:
```python
class MandatoryRead(BaseModel):
    spec_type: str
    read_path: str
    n_a_reason: str = ""  # populated if file/N/A documented
```

**Per-type validator** (`verify-mandatory-reads`):
- For active `spec_type`, check every entry in mandatory list has either `read_path` populated OR `n_a_reason` populated.
- Missing entry → exit 2.

**Step 3 — Discretionary exploration (v3 verbatim)**:

After mandatory reads, additional exploration via Glob/Grep tools (NOT Bash `grep`/`find` per v3 audit-trail rule). Helper logs tool selection in `.devforge/specify-tool-log.json`.

**Step 4 — Cross-reference (v3 verbatim)**:
- Cross-reference findings with MEMORY.md for known issues.
- Verify docs accuracy if Phase 1 read docs — flag discrepancies between docs and actual code.
- Note patterns from most-similar existing feature.

**Greenfield branch (v3 verbatim)**:
- Read constitution Section 7 (Scaffolding Guide).
- Identify what needs to be CREATED.
- Reference framework docs via WebSearch when needed.
- Check MEMORY.md for prior-feature lessons.
- Phase 4 §2 "Current State" describes what exists so far + scaffolding location.

**Persistence**: every `record-mandatory-read` + Step 3/4 finding writes to `.devforge/specify-state.json`.

## Phase 4: Write the specification

Goal: deterministic markdown render matching v3 9-section template + 7-subsection AC, with helper-enforced coverage rule.

**Helper subcommands**:

1. `assign-spec-number` — scan existing `specs/` for highest NNN, return next.
2. `assign-feature-name` — 2-4 word kebab-case slug. LLM generates via setter; user can override.
3. `create-branch` — if branch deferred from Phase 0, checkout `spec/NNN-short-desc` matching spec NNN.
4. `record-affected-area` — table row: `{area, files, impact}`.
5. `set-overview` / `set-current-state` / `set-desired-behavior` — single-string sections.
6. `add-ac` — categorized AC; see schema below.
7. `record-out-of-scope` — items with optional Phase 1.5 finding cross-ref.
8. `record-constraint` — "must follow / must not break / must use".
9. `record-open-question` — uncertainties + per-category "no DP" reasons from Phase 2.
10. `record-risk` — table row.
11. `verify-coverage` — Variance rule #5; every Phase 1.5 finding has `landed_in != unlanded`.
12. `verify-numerical-consistency` — Variance rule #6; grep rendered spec for counts, cross-check.
13. `verify-ac-shape` — Variance rule #10; validates every AC `statement` matches declared EARS variant regex.
14. `check-constitution-compliance` — runs at Phase 4 end + Phase 5 entry; greps constitution.md for MUST/MUST NOT/SHALL lines; cross-checks rendered AC + Constraints + Out-of-Scope against constitution mandates; emits warnings on conflict surfaced to user before approval (non-blocking — user decides whether to amend or proceed with conflict noted in §8 Open Questions). Adopted from Spec Kit Constitution Check gate.
15. `resolve-open-question` — downstream-callable subcommand (used by /plan + /breakdown). Accepts `{question_id, resolution_text, resolution_phase}`. Appends audit entry to `.devforge/specify-state.json` under `open_question_resolutions`. Subsequent renders of §8 mark resolved entries struck through with resolution note. /specify itself does not call this; it ships in helper for downstream consumers. Adopted from Spec Kit checklist.md parity.
16. `render` — produce markdown matching v3 template.

**AC schema (Variance rule #4 — 7-subsection categorization + Variance rule #10 — EARS notation)**:

```python
class AcceptanceCriterion(BaseModel):
    ac_id: str  # "AC-1", "AC-2", ...
    subsection: Literal[
        "tooling_artifact_presence",  # 5.1
        "behavior_preservation",      # 5.2
        "behavior_change",            # 5.3
        "ci_pipeline",                # 5.4
        "hooks_gates",                # 5.5
        "documentation",              # 5.6
        "hygiene",                    # 5.7
    ]
    ears_variant: Literal["ubiquitous", "event_driven", "state_driven", "optional", "unwanted"]
    statement: str                    # EARS-formatted; helper validates via regex per variant
    verification_command: str = ""    # e.g., `grep -r "lerna" returns 0 matches`
    test_anchor: str = ""             # optional path::test_name; rendered as `> Test: <test_anchor>` line
    n_a_reason: str = ""              # set on subsection-level N/A entries
```

**EARS validation regex (helper `verify-ac-shape`)**:

| Variant | Anchor pattern |
|---|---|
| ubiquitous | `^The [^.]+ shall [^.]+\.$` |
| event_driven | `^WHEN [^,]+,? the [^.]+ shall [^.]+\.$` |
| state_driven | `^WHILE [^,]+,? the [^.]+ shall [^.]+\.$` |
| optional | `^WHERE [^,]+,? the [^.]+ shall [^.]+\.$` |
| unwanted | `^IF [^,]+, THEN the [^.]+ shall [^.]+\.$` |

Patterns are starter set; refine during Step 3 empirical testing. Reject statement that fails declared variant's regex → exit 2 + retry prompt.

**Subsection-EARS constraints (Variance rule #10)**:

| Subsection | Allowed EARS variants | `verification_command` |
|---|---|---|
| 5.1 tooling_artifact_presence | `ubiquitous` ONLY | REQUIRED |
| 5.2 behavior_preservation | any 5 | optional |
| 5.3 behavior_change | any 5 | optional |
| 5.4 ci_pipeline | any 5 | optional |
| 5.5 hooks_gates | any 5 | optional |
| 5.6 documentation | any 5 | optional |
| 5.7 hygiene | `ubiquitous` ONLY | REQUIRED |

Helper `add-ac` enforces. Reject on subsection-variant mismatch OR missing-required-verification.

**`test_anchor` render rule**: when `test_anchor` populated, render adds line under AC checkbox: `> Test: <test_anchor>`. /verify reads + runs.

**Subsection coverage rule**:
- For each of 7 subsections: helper checks ≥1 AC OR explicit `N/A — [reason]` entry.
- Collapsed/missing subsection → `verify` exit 2.

**Coverage rule (Variance rule #5 — v3 §6 verbatim)**:

For each Phase 1.5 finding, the helper traces a landing in §5 (AC), §6 (OOS), §7 (Constraint), or §9 (Risk). Unlanded finding = hard error. Helper `verify-coverage` runs at Phase 4 end + at Phase 5 entry.

**Numerical verification (Variance rule #6 — v3 Rule 8 verbatim)**:

Helper `verify-numerical-consistency`:
- Greps rendered spec for digit patterns.
- For each multi-occurrence digit value (e.g., "24 packages" appears in §2 + §4), confirms same value across all occurrences.
- Inconsistent occurrences → exit 2 + cite locations.
- LLM also runs Bash enumeration during drafting; helper validates result.

**Spec render template (v3 verbatim, byte-identical structure)**:

```markdown
# Spec: [Feature Name]

**Date**: [YYYY-MM-DD]
**Status**: Draft | Approved | In Progress | Complete
**Author**: Claude + [User]

## 1. Overview

[2-3 sentences]

## 2. Current State

[Brownfield: existing behavior with file:line refs + docs context.]
[Greenfield: what exists + scaffolding ref from constitution Section 7.]

## 3. Desired Behavior

[Specific. "Button blue" not "improve button".]

## 4. Affected Areas

| Area | Files | Impact |
|------|-------|--------|
| [name] | [paths] | [what changes] |

## 5. Acceptance Criteria

Each AC must be testable and unambiguous. **Cover each category that applies. Mark non-applicable categories with "N/A — [reason]".**

### 5.1 Tooling / artifact presence and absence
- [ ] **AC-X**: [must exist / must NOT exist]

### 5.2 Behavior preservation
- [ ] **AC-X**: [existing behavior that must continue to work + verification command]

### 5.3 Behavior change
- [ ] **AC-X**: [new behavior + verification command]

### 5.4 CI / pipeline
- [ ] **AC-X**: [pipeline step that must pass]

### 5.5 Hooks / gates
- [ ] **AC-X**: [pre-commit / pre-push / husky / other hooks that must fire]

### 5.6 Documentation
- [ ] **AC-X**: [doc files that must be updated]

### 5.7 Hygiene
- [ ] **AC-X**: [grep check confirming no forbidden strings remain]

## 6. Out of Scope

**Coverage rule (v3)**: For each Phase 1.5 finding, the finding either (a) becomes an AC in §5, (b) becomes a Constraint in §7, (c) is explicitly listed here as out of scope, OR (d) is in §9 Risks with documented mitigation. Unlanded finding = hard error — re-verify Phase 1.5 enumeration is complete before saving.

- NOT included: [thing 1] — [optional Phase 1.5 ref, e.g., "research:Q5"]
- NOT included: [thing 2]

## 7. Technical Constraints

- Must follow: [architecture pattern]
- Must not break: [existing feature]
- Must use: [specific API/pattern]

## 8. Open Questions

[Remaining uncertainties + per-Phase-2-category "no DP" reasons]

## 9. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| [risk] | Low/Med/High | Low/Med/High | [how to handle] |
```

**Persistence**: every setter writes to `.devforge/specify-state.json`. Kill-resume safe.

## Phase 5: Approval + branch creation + /plan handoff

Goal: hard-gate user approval, branch creation if deferred, deterministic /plan handoff block.

**Steps**:

1. Helper `render-summary` produces 4-bullet summary (v3 verbatim):
   ```
   I've created the specification at `specs/NNN-[feature-name]/spec.md`. Key points:
   - **What changes**: [1-2 sentences]
   - **Files affected**: [count] files across [areas]
   - **Acceptance criteria**: [count] testable criteria across [count of applicable subsections] AC categories
   - **Out of scope**: [key exclusions]

   Please review and either approve or request changes. Once approved, run `/plan` to create the technical implementation plan.
   ```

2. Orchestrator copies summary VERBATIM into user message (per `feedback_verbatim_echo_directive`) as fenced code block.

3. AskUserQuestion approval: Approve / Request changes / Cancel (single-line question per `feedback_askuserquestion_single_line_only`).

4. If Approve → helper `set-status Approved` + render `/plan` handoff block.

5. If Request changes → return to relevant phase, re-render, re-prompt.

6. If Cancel → preserve state in `.devforge/specify-state.json`, exit.

**Hard gate**: `/plan` cannot run until spec status is Approved. Enforced by /plan's preflight.

**Next-step handoff (to /plan)**:

```
## Next step: /plan handoff

Run:

~~~
/plan specs/NNN-feature-name/spec.md
~~~

Minimum handoff data:
- Spec status: Approved
- Spec type: <migration_tooling | feature_addition | bug_fix | refactor | greenfield_feature>
- AC count: <count> across <subsection count> subsections (<5.1 count>, <5.2 count>, ..., <5.7 count>)
- Decision-point coverage: <count> answered, <count> default-applied, <count> deferred-OOS, <count> deferred-open-question
- Affected areas: <count> across <package list>
- Out-of-scope items: <count>
- Open questions: <count>
- Constraints: <count>
- Risks: <count>
- Phase 1.5 finding coverage: 100% (all findings landed)

Reference: specs/NNN-feature-name/spec.md
```

## Misalignment detection (mirror /discover + /research)

When user's later answer contradicts or drifts from earlier confirmed values or imported findings, helper + orchestrator detect and respond by severity. Same three-category model as DISCOVER-PLAN + REDESIGN-RESEARCH-PLAN:

| Category | Example | Detection | Response |
|---|---|---|---|
| Direct contradiction | §6 OOS contains "OAuth" + AC adds "Login via OAuth" | Helper-side token overlap | Hard-block via AskUserQuestion |
| Drift / scope creep | `scope_boundaries` DP = "one module" + later AC touches 3 modules | LLM-side per-setter check | Soft-flag, log, surface at next pause |
| Refinement | `scope_boundaries` narrows: "Admin > Products" → "Admin > Products + Admin > Orders" (superset) | LLM-side | Quiet update, log |

Per-setter protocol identical to /discover (see DISCOVER-PLAN.md "Per-setter call protocol").

Anti-patterns explicitly forbidden:
- Silent overwrite — later answer must never replace earlier without surfacing in conflicts log.
- LLM-only detection for direct contradictions — token-overlap runs first.
- Force user to re-walk all categories on conflict — only re-ask affected category.

## Agent ownership — orchestrator-only

Decision: no new subagent. `/specify` stays orchestrator-direct across all 6 phases.

Per `feedback_avoid_subagents_for_sequential_identical_workflows` 3-benefit test:

- **Parallelism**: no — every phase sequential. Phase 1 → 1.5 → 2 → 3 → 4 → 5 strictly ordered.
- **Tool isolation**: weak — orchestrator already has Read + AskUserQuestion + CBM. Dispatch isolates nothing not already accessible.
- **Context-budget**: weak — typical spec covers 1-3 packages; Phase 3 CBM trace below dispatch threshold.

Critically: orchestrator-only also preserves variance — v3 was orchestrator-direct; preserving this means dispatch-axis variance is structurally guaranteed at zero.

Revisit only if Phase 3 CBM cost grows past ~50 calls (cost gate condition; revisit in OQ).

## Constraints

- Zero-escape-hatch policy: no OR / if / except / unless / use-judgment in spec body (per `feedback_zero_escape_hatch_policy`).
- Helper-owns-shape: `src/devforge/lib/specify_helper.py` owns SpecDoc + FindingsLog + DecisionPointLog + SpecTypeClassification structure; LLM composes values via setters (per `feedback_helper_owns_shape_principle`).
- LLM-first density: spec body is LLM instructions (per `feedback_llm_instructions_self_contained`).
- Triple-agent verification on every spec edit: instruction-author → instruction-reviewer + claude-code-guide (parallel). Iterative apply-verify loop (per `feedback_iterative_review_loop_preferred`).
- No real project names in examples (per `feedback_no_real_project_names`).
- Test-first for helper functions (per `feedback_test_first_python_helpers`).
- No `model:` override in `src/commands/specify/main.md` frontmatter (per `feedback_avoid_command_model_override`).
- Verbatim echo directive when spec instructs LLM to display helper output (per `feedback_verbatim_echo_directive`).
- Spec body is self-contained — no forward refs to `/plan` / `/breakdown`. Forward-handoff lives in OUTPUT spec.md's "Next step: /plan handoff" section.
- Spec document keeps v3 9-section identity through render — not a /discover report, not a /research report.
- **10 Variance Preservation rules are non-negotiable.** Pinned into spec body verbatim. Rule #9 (LLM-facing prose preserved verbatim) requires explicit diff between v3 baseline prose and rewrite prose at Step 4a; any deviation logged with re-tune justification. Rule #10 (EARS notation for AC statements) is a v3.1 SDD-adoption — divergence from v3 baseline is intentional, documented in Appendix A "SDD-adopt prose blocks" subsection.

## Work order

- **Step 1**: confirm v3 baseline + 10 variance constraints. Empirical variance gate deferred (see "Empirical variance gate — DEFERRED" section).
- **Step 2**: draft schemas (Python pydantic) for `specify_helper.py`:
  - `SpecDoc` — 9-section v3 template + `status` enum + `spec_type` enum + `feature_name` + `spec_number`.
  - `Finding` — Phase 1.5 enumeration entry + `landed_in` tracking (per Variance rule #5).
  - `FindingsLog` — list of Finding + per-source coverage flags.
  - `DecisionPoint` — Phase 2 entry + 7-category enum + `status` enum.
  - `DecisionPointLog` — list of DecisionPoint + per-category coverage flags.
  - `SpecTypeClassification` — 4-type enum + per-type mandatory-read tracking.
  - `MandatoryRead` — per-spec-type read entry.
  - `AcceptanceCriterion` — 7-subsection enum + `ears_variant` enum (5 EARS variants) + `statement` (EARS-validated) + `verification_command` + `test_anchor` (optional path::test_name) + `n_a_reason`.
  - `OpenQuestionResolution` — `{question_id, resolution_text, resolution_phase, resolution_timestamp}` audit entry; written by downstream `/plan` + `/breakdown` via `resolve-open-question` subcommand.
  - `AffectedArea` / `Constraint` / `Risk` / `OutOfScopeItem` — table-row schemas.
  - `Conflict` — misalignment-detection log entry (mirror /discover).
  - State persisted to `.devforge/specify-state.json` (mirrors /constitute, /discover, /research).
- **Step 3**: implement helper subcommands. Test-first per `feedback_test_first_python_helpers`. Subcommands:
  - Phase 0: `preflight`.
  - Phase 1: `record-input-read` (auto-tags `source_origin` from file path), `phase1-finalize`.
  - Phase 1.5: `record-finding`, `verify-findings`, `render-findings`, `findings-finalize`.
  - Phase 2: `detect-mode`, `record-decision-point`, `set-dp-answer`, `set-dp-default-applied`, `set-dp-deferral`, `dp-coverage` (DP-level statuses), `rubric-coverage` (per-category Clear/Partial/Missing/NoDPInCategory wrapping DP statuses), `verify-decision-coverage` (gate: all 7 categories ∈ {Clear, NoDPInCategory}), `rubric-finalize`, `dp-finalize`. Per-DP turn cap enforced inside `set-dp-deferral` (auto-fires at 3 follow-ups).
  - Phase 3: `classify-spec-type`, `record-mandatory-read`, `verify-mandatory-reads`, `phase3-finalize`.
  - Phase 4: `assign-spec-number`, `assign-feature-name`, `create-branch`, `record-affected-area`, `set-overview`, `set-current-state`, `set-desired-behavior`, `add-ac` (validates EARS variant), `record-out-of-scope`, `record-constraint`, `record-open-question`, `record-risk`, `verify-coverage` (Phase 1.5 finding landing), `verify-numerical-consistency`, `verify-ac-subsection-coverage`, `verify-ac-shape` (EARS regex), `check-constitution-compliance` (post-render constitution-recheck), `render`.
  - Phase 5: `render-summary`, `set-status`, `render-plan-handoff`, `check-constitution-compliance` (re-run as entry gate; warnings re-surfaced if state changed since Phase 4 invocation).
  - Downstream (callable by /plan + /breakdown): `resolve-open-question` (audit-trail append).
  - Cross-phase: `read-state`, `summary`, `verify` (full SpecDoc validity).
  - Misalignment: `check-conflicts`, `record-conflict-resolution`.
  - **Test fixtures**: author TWO fixtures covering most-distinct spec_types (mirrors /research + /discover pattern — skeleton lives in helper code as inline render per /constitute precedent; fixtures are complete examples, not skeletons):
    - `tests/lib/fixtures/specify-sample-migration.md` — `migration_tooling` happy-path. Exercises §5.1 Ubiquitous + paired verification_command, §5.4 CI pipeline, §5.7 hygiene with grep verification. Phase 1.5 coverage rule lands every finding into AC / Constraint / OOS / Risk. Numerical-verification stress test on package counts (Rule 8). Generic placeholders per `feedback_no_real_project_names`.
    - `tests/lib/fixtures/specify-sample-greenfield.md` — `greenfield_feature` happy-path. Pre-seeded via Phase 1 adapter from a synthetic `discover/<date>-topic.md` companion fixture. Exercises constitution Section 7 scaffolding refs, §5.5 hooks AC, §5.6 documentation AC. Demonstrates auto-mode `[default applied]` markers in §8 Open Questions.
    - Matching state fixtures: `tests/lib/fixtures/specify-sample-migration-state.json` + `tests/lib/fixtures/specify-sample-greenfield-state.json` (canonical SpecDoc + FindingsLog + DecisionPointLog + SpecTypeClassification state).
    - Companion upstream fixture for greenfield: `tests/lib/fixtures/specify-sample-greenfield-discover-input.md` (synthetic /discover output placed in `discover/` to exercise Phase 1 adapter path-based source tagging + spec_type pre-seeding).
    - Companion upstream fixture for from-research mode: `tests/lib/fixtures/specify-sample-research-input.md` (synthetic /research output placed in `research/` to exercise Phase 1 adapter path-based source tagging on the `research` axis — `source_origin="research"`, no Phase 3 spec_type pre-seed, LLM classifies spec_type from content). Mirrors shape of already-shipped `tests/lib/fixtures/research-sample-bug-report.md` and `research-sample-enhancement-report.md` (committed d7750ad). Required to make Step 8 from-research empirical test deterministic — without it the test couples /specify CI to /research helper state.
    - Round-trip discipline (per `feedback_test_first_python_helpers`): build state via real helper setter calls → `render` → byte-diff against fixture md. Fixtures are canonical expected-shape artifacts for `render()` regression tests AND reference examples for `/specify` spec-body authoring at Step 4a (LLM reads fixtures during drafting for shape clarity, especially EARS application across subsections).
    - Add fixtures F3-F5 (feature_addition / bug_fix / refactor) only if Step 8 empirical testing reveals shape drift on those types.
- **Step 4a**: author spec at `src/commands/specify/main.md` + reference docs (if any). Spec body covers all 6 phases with explicit transition gates (each phase requires prior phase's finalize exit 0). Diff v3 baseline prose vs rewrite prose for blocks listed in Appendix A; any deviation logged with re-tune justification. **Reference fixtures during authoring**: spec body MAY cite fixture paths as concrete examples for LLM at runtime (e.g., "see `tests/lib/fixtures/specify-sample-migration.md` for migration_tooling shape").
- **Step 4b**: ~~no subagent~~ — skipped (orchestrator-only per Agent ownership).
- **Step 5**: triple-agent verify in iterative apply-verify loop:
  1. `instruction-author` drafts/edits spec.
  2. `instruction-reviewer` + `claude-code-guide` review in parallel (single message, two Agent calls).
  3. If either reviewer returns findings → loop back to step 1.
  4. Present clean draft to user for approval.
  5. User approves → Step 6.
- **Step 6**: update emitter `scripts/emitters/claude.py` `_PROMOTED` list for `specify` (per `feedback_emitter_promoted_cross_check`).
- **Step 7**: cross-update README, DEVELOPMENT-STATUS, CLAUDE.template, storage-rules (per `feedback_release_docs`).
- **Step 8**: empirical test on testForge20 — three modes:
  - Cold mode: `/specify "<topic prompt>"` — no research/ or discover/ files present.
  - From-research mode: place a synthetic research/<date>-topic.md file (or run /research once if shipped) → run `/specify "<topic>"` → confirm Phase 1 enumerates research/, Phase 1.5 produces findings from it, Phase 3 LLM classifies without pre-seed.
  - From-discover mode: place a synthetic discover/<date>-topic.md file (or run /discover once if shipped) → run `/specify "<topic>"` → confirm Phase 1 enumerates discover/, source_origin tag = "discover", Phase 3 pre-seeds spec_type=greenfield_feature, override-confirmation prompt surfaces.
  - Validate: hard-gate, all 7 phases run, Phase 1.5 produces ≥3 bullets per read source, Phase 2 covers all 7 categories, Phase 3 spec-type classifier + per-type reads + path-based pre-seeding, Phase 4 7-subsection AC + EARS-variant validation + coverage rule + numerical-verification gates + constitution-recheck warnings surface correctly, Phase 5 deterministic summary + /plan handoff block.
  - SDD-adoption-specific validation:
    - `verify-ac-shape` rejects free-prose AC; accepts each of 5 EARS variants in a happy-path AC.
    - `check-constitution-compliance` surfaces a synthetic conflict (e.g., AC violates a constitution MUST rule) as warning before approval.
    - `test_anchor` field renders correctly when populated; omitted from render when empty.
    - `resolve-open-question` writes audit entry; subsequent render strikes through resolved entries.

## Verify criteria

- **Step 3**: 100% helper subcommand tests pass; helper round-trips state via JSON; coverage check on real input shapes. Specifics:
  - Phase 1: `record-input-read` accepts each of 7 sources (constitution / MEMORY / CLAUDE / docs / research/ / discover/ / specs/) and auto-tags `source_origin` from path; phase1-finalize gates Phase 1.5.
  - Phase 1.5: `verify-findings` exits non-zero when any read source has fewer than 3 findings without "No items relevant" marker.
  - Phase 2: `rubric-coverage` returns accurate `{category: state}` map (Clear / Partial / Missing / NoDPInCategory) after each setter; `verify-decision-coverage` exits non-zero when any category is `Partial` or `Missing`; `detect-mode` correctly identifies auto vs interactive given env/flag/system-reminder signals; `record-decision-point` rejects `default_applied` status in interactive mode; per-DP turn cap (3 follow-ups) auto-transitions DP to `deferred_open_question` on overage with `[exceeded cap]` marker visible in §8 render.
  - Phase 3: `verify-mandatory-reads` exits non-zero when any per-type mandatory entry has neither `read_path` nor `n_a_reason`.
  - Phase 4: `add-ac` rejects ACs without subsection AND without declared EARS variant; `verify-ac-subsection-coverage` exits non-zero when any subsection has zero ACs without N/A reason; `verify-ac-shape` exits non-zero when any AC `statement` fails the regex for its declared `ears_variant`; `verify-coverage` exits non-zero when any Phase 1.5 finding has `landed_in=unlanded`; `verify-numerical-consistency` detects digit inconsistencies across sections; `check-constitution-compliance` surfaces conflicts between rendered AC/Constraints/OOS and constitution.md MUST/SHALL lines as user-visible warnings (non-blocking).
  - Downstream subcommand: `resolve-open-question` accepts `{question_id, resolution_text, resolution_phase}`, writes audit entry, subsequent render strikes through resolved entries with note.
  - `render` produces byte-identical output for byte-identical state (determinism check).
- **Step 4a**: spec passes intra-file consistency check (instruction-author). Phase transitions documented with helper gate references. No forward refs to /plan or /breakdown in spec body. Prose diff vs v3 baseline justified or matches verbatim.
- **Step 5**: both reviewer agents return clean across iterative loop; user approves final draft.
- **Step 6**: `./install.sh` on fresh testForge20 promotes `/specify` into `.claude/commands/`.
- **Step 8**: empirical run validates all three modes; spec.md produced has all 9 sections populated; 7-subsection AC categorization correct; coverage rule enforced; numerical consistency enforced; misalignment detection fires on contradiction + drift + refinement.

## Open questions

1. ~~What did 5% variance measure?~~ **Closed 2026-05-11** — all 4 axes (structural / AC count / output length / decision-drift). Encoded in "Variance preservation" section. Empirical re-verification deferred to follow-up plan.
2. ~~Same input cases as original?~~ **Closed 2026-05-11** — primary `/specify` input path will be generated by /research or /discover; cold-mode is secondary. Canonical input case will be selected when upstream ships and empirical re-verification fires. Not needed for current redesign through Step 8.
3. ~~Should `/specify` allow re-import if user re-runs `/research` mid-flow?~~ **Closed 2026-05-11** — no. Re-opens variance risk + violates Variance rule #5. Revisit only if empirical signal surfaces.
4. ~~Phase 1.5 findings "task-relevant" criterion enforcement~~ **Closed 2026-05-11** — structural-only enforcement (≥3 bullets / "No items relevant" marker). Semantic-relevance decision stays with LLM. Spec body documents the helper-scope gap explicitly.
5. **Cost gate for Phase 3 CBM chain** — surface estimated CBM call count before Phase 3? Default no in v1 (typical 1-3 packages); revisit if empirical shows Phase 3 costs balloon.
6. ~~Handoff format normalization~~ **Closed 2026-05-11 (N/A)** — /research and /discover do NOT emit structured handoff blocks. Each saves a plain md file to its own directory (research/ or discover/). /specify uses path-based source tagging only; no content parsing of handoff format. If /breakdown later adopts a similar pattern, it can use the same path-based convention without a shared parser.
7. ~~Greenfield spec-type assignment~~ **Closed 2026-05-11** — 5th enum value `greenfield_feature` added to SpecTypeClassification. Dedicated mandatory-read list (constitution Section 7 + framework docs via WebSearch + MEMORY.md + /discover ref md if loaded). /discover handoff pre-seeds spec_type=greenfield_feature (scope-locked per DISCOVER-PLAN). /research handoff does NOT pre-seed (research is neutral on bug/enhancement/refactor — Phase 3 LLM classifies from report content).
8. ~~Mode-detection signals~~ **Closed 2026-05-11 (C-strict)** — three signals only: `$DEVFORGE_AUTO_MODE=1` env var, `--auto` flag, exact substring match (case-insensitive) for `"auto mode is active"` OR `"auto mode still active"` in latest `<system-reminder>` block. User natural-language prose ignored. Variance rule #8 updated to encode these rules verbatim.
9. ~~EARS variant for §5.1 + §5.7 (presence/hygiene)~~ **Closed 2026-05-11 (D1)** — §5.1 + §5.7 = Ubiquitous variant only. Both `statement` (EARS Ubiquitous) AND `verification_command` (executable check) REQUIRED on these subsections. Other subsections accept any of 5 variants; verification_command optional. Subsection-EARS constraint table pinned in Phase 4 schema. IEEE 29148-2018 conformance preserved.
10. **Constitution-recheck conflict surfacing** — `check-constitution-compliance` is non-blocking (warning, not error). Open: should user be able to acknowledge a conflict via `record-constitution-override` setter that suppresses subsequent re-checks within same session, or should warnings re-surface on every render? Default = re-surface every render (zero-escape-hatch). Revisit if empirical shows it's noisy.
11. **`resolve-open-question` ownership ambiguity** — subcommand ships in `specify_helper` but is only callable by `/plan` + `/breakdown`. Open: should `/plan` + `/breakdown` plans (when authored) explicitly document this dependency, or should the subcommand emit a deprecation warning if called from `/specify` itself? Decide when `/plan` redesign plan starts.
12. **Ambiguity-term lint as adjunct to EARS shape check** — sddforge cross-pollination 2026-05-14 (Appendix B). Open: do we add a 20-term ambiguity scanner alongside `verify-ac-shape` to reject AC statements containing weasel words (`reasonable`, `appropriate`, `intuitive`, …) the same way EARS regex rejects malformed statements? Default = defer to empirical signal. Build only if Step 8 testForge20 run produces an AC that passes EARS regex but is clearly untestable; until then the ambiguity-term list lives in Appendix B as a recoverable spec, not in code.
13. **Durable gate-record schema for `set-status Approved`** — sddforge cross-pollination 2026-05-14 (Appendix B). Current Phase 5 design persists approval state only in `.devforge/specify-state.json` (single file, overwritten per run). Open: should approval emit a durable per-stage gate record (sddforge-shape: `version`, `gateId`, `stage`, `approvedArtifact`, `approvedScope`, `denied`, `nextAllowed`, `approvedBy`, `relatedArtifacts`) to enable cross-session resume + downstream `/plan` / `/breakdown` audit? Default = defer until /plan + /breakdown ship and the multi-stage approval chain creates a real "did I approve the spec last week" problem; the existing `set-status Approved` setter + state file cover single-session resume today.

## When resuming work

1. Read this file in full.
2. Read v3 baseline: `/Users/mykolakudlyk/Projects/doosan/cse-strata-ws-forge/.claude/commands/specify.md` (Appendix A below summarizes; baseline is authoritative).
3. Read SPECIFY-PLAN.md — original WATCHLIST plan that promoted into this redesign.
4. Read DISCOVER-PLAN.md + REDESIGN-RESEARCH-PLAN.md — `/specify` consumes their handoff blocks in Phase 1; field-name drift in either upstream plan breaks adapter parsing.
5. Read Obsidian `20 Projects/AIDevTeamForge/parityTest/4-way comparison results - spec 007.md` — v1 parity-test data + variance methodology.
6. Read `/constitute` as reference helper-owns-shape pattern: `src/devforge/lib/constitute_helper.py` + `src/commands/constitute/main.md`.
7. Pick up at next unaddressed Work order step. Empirical variance gate is deferred — re-introduce as SPECIFY-VARIANCE-GATE-PLAN.md when upstream (/discover OR /research-redesign) ships.

---

## Appendix A: v3 frozen baseline

Authoritative source: `/Users/mykolakudlyk/Projects/doosan/cse-strata-ws-forge/.claude/commands/specify.md` (371 lines).

### v3 phase structure

- **Phase 0**: Branch setup (git rev-parse + branch detect + default-branch detect + branch decision deferred to Phase 4)
- **Pre-Step**: Reset `.claude/session-state.md` to empty placeholder
- **Phase 1**: Read 7 inputs in rewrite (v3 had 6; v3.1 adds `discover/` for /discover output): constitution + MEMORY + CLAUDE + docs + research/ enumerated + **discover/ enumerated (v3.1)** + specs/ enumerated. All required if exists. Constitution populate-guard.
- **Phase 1.5**: REQUIRED INTERMEDIATE OUTPUT — findings enumeration per source, ≥3 bullets/source.
- **Phase 2**: Decision-point coverage across 7 categories (scope_boundaries, existing_behavior, data_flow_state, edge_cases, ui_ux_details, breaking_changes, tooling_configuration). Mode-dependent (auto/interactive). AskUserQuestion preferred, markdown fallback.
- **Phase 3**: Spec-type classification (migration_tooling / feature_addition / bug_fix / refactor / greenfield_feature) + per-type mandatory file list + Glob/Grep discretionary + cross-reference. /discover handoff pre-seeds greenfield_feature.
- **Phase 4**: Write spec at `specs/NNN-feature-name/spec.md` + branch creation `spec/NNN-short-desc`. 9-section template + 7-subsection categorized AC + Coverage rule.
- **Phase 5**: Hard-gate approval via 4-bullet summary.

### v3 9-section spec template

1. Overview (2-3 sentences)
2. Current State (brownfield narrative / greenfield scaffolding)
3. Desired Behavior (specific)
4. Affected Areas (table: Area | Files | Impact)
5. Acceptance Criteria — 7 categorized subsections:
   - 5.1 Tooling / artifact presence and absence
   - 5.2 Behavior preservation
   - 5.3 Behavior change
   - 5.4 CI / pipeline
   - 5.5 Hooks / gates
   - 5.6 Documentation
   - 5.7 Hygiene
6. Out of Scope (with Coverage rule banner)
7. Technical Constraints (must follow / must not break / must use)
8. Open Questions (uncertainties + per-Phase-2-category "no DP" reasons)
9. Risks (table: Risk | Likelihood | Impact | Mitigation)

### v3 Rules 1-10 (must preserve verbatim in rewrite spec body)

1. Specs are contracts — once approved, implementation must satisfy every AC.
2. Be exhaustive on Out of Scope — prevents scope creep.
3. Every AC must be testable.
4. Reference specific files — `path/to/file.ts:line` format for existing; constitution scaffolding refs for greenfield.
5. Check MEMORY.md — reference prior similar work.
6. Don't propose solutions — spec is WHAT, not HOW.
7. Greenfield: include scaffolding needs in Affected Areas table.
8. Verify numerical claims — every count/size/version verified via Bash before write; inconsistency = hard error.
9. Phase 1.5 is mandatory — every input read produces enumerated findings before Phase 2; skipping = hard error.
10. Decision points exhaustively surfaced — every DP with ≥2 valid implementations gets a clarifying question; model default does not justify skipping; document no-DP categories in Open Questions.

### LLM-facing prose blocks to preserve verbatim (Variance rule #9)

- Phase 1 "All bullets are required if the file/directory exists. Do not skip discretionarily — every applicable input must be read." (v3 strict-read mandate)
- Phase 1 constitution populate-guard wording: "⛔ constitution.md has not been populated yet. Run `/constitute` before using `/specify`."
- Phase 1.5 framing: "This intermediate output converts implicit recall into explicit enumeration. It prevents silent dropping of input content (the dominant variance source observed in parity tests of v1)."
- Phase 2 "Decision Point" definition (5-element list of what changes).
- Phase 2 Rule: "For every decision point with ≥2 valid implementations, generate a clarifying question. Do not skip a decision point because the model has a default preference — surface the choice to the user. The model's default is one valid answer; the user's input is required to commit to it."
- Phase 2 categories framing: "Categories to scan for decision points (cover each — none are optional)".
- Phase 2 priority order: "scope > breaking changes > data flow > tooling > UX > edge cases".
- Phase 2 stop rule: "Stop only when every decision point identified above has either (a) a user answer, or (b) an explicit 'out of scope' / 'open question' entry. Do not stop early based on subjective sufficiency."
- Phase 2 tool-preference paragraph (AskUserQuestion + fallback + bundling discipline).
- Phase 2 mode-dependent path paragraph (auto vs interactive + pause-when-uncertain).
- Phase 3 Step 3 audit-trail rule: "Use Glob/Grep tools specifically (not Bash `grep`/`find`) so the tool-call log is auditable."
- Phase 4 §5 framing: "Each AC must be testable and unambiguous. **Cover each category that applies. Mark non-applicable categories with 'N/A — [reason]'.**" + "Each subsection: at least one AC if applicable, or 'N/A — [reason]'. Do not collapse subsections that don't apply — explicitly mark them N/A so reviewers know they were considered."
- Phase 4 §6 Coverage rule paragraph verbatim.
- Phase 5 4-bullet approval-summary block verbatim.
- Rules 1-10 closing list verbatim.

Variance-preservation requirement: redesigned `/specify` MUST produce a spec.md whose section ordering + header fields + section heading text + AC subsection headings + status enum + branch name format + spec path format are byte-identical to this baseline. Render determinism enforced via helper `render` subcommand returning identical output for identical state (Step 3 test). Two test fixtures in `tests/lib/fixtures/` (migration_tooling + greenfield_feature) provide canonical state.json + expected-render.md pairs for byte-diff regression. Skeleton lives in helper code (inline render mirrors /constitute); fixtures are complete examples, not skeletons (pattern matched to /research + /discover plans).

Prose-diff requirement: rewrite spec body at `src/commands/specify/main.md` reproduces the bulleted verbatim blocks above. Any deviation requires explicit re-tune justification logged.

### SDD-adopt prose blocks (v3.1 additions — intentional divergence from v3 baseline)

Adopted from popular SDD frameworks (Spec Kit, Kiro, Tessl); v3.1 designation marks divergence from v3 verbatim. Each block ships in rewrite spec body in addition to the v3-verbatim blocks above.

- **EARS notation for AC statements** (Kiro / IEEE 29148-2018). Rule #10 + Phase 4 schema. EARS framing block: "Every AC statement uses EARS notation (Easy Approach to Requirements Syntax). Choose one of 5 variants: Ubiquitous, Event-driven, State-driven, Optional, Unwanted. Helper validates statement matches declared variant via regex; malformed statements rejected." Hygiene + tooling-presence subsections (5.1, 5.7) accept Ubiquitous variant only.
- **`discover/` enumeration in Phase 1** (parallel to v3's `research/` enumeration). v3 only enumerated `research/` because /discover did not exist at v3 author time. v3.1 adds discover/ to Phase 1 input list with path-based source tagging. Phase 1 input source count: 6 (v3) → 7 (v3.1).
- **Constitution recheck at Phase 4 + 5** (Spec Kit Constitution Check gate). Helper `check-constitution-compliance` greps constitution.md for MUST/MUST NOT/SHALL lines, cross-checks rendered spec against mandates, emits warnings (non-blocking; user decides amend-vs-proceed). Framing block: "After Phase 4 render and before Phase 5 approval, helper re-checks rendered spec against constitution.md mandates. Conflicts surface as warnings — user decides whether to amend or proceed with noted exception in §8."
- **Optional `test_anchor` field on AC** (Tessl-lite). Schema field + render rule. Framing block: "When a brownfield AC corresponds to an existing test, populate `test_anchor` with path::test_name. /verify (downstream) reads + runs. Leave empty when no test exists yet — /breakdown will plan the test."
- **`resolve-open-question` audit trail** (Spec Kit checklist.md parity). Subcommand only; /specify itself does not call. /plan + /breakdown invoke during their phases when §8 entries get resolved. Framing block: "§8 Open Questions are static at /specify write time. /plan + /breakdown call `specify_helper resolve-open-question` to mark resolved with audit entry. Re-rendered spec.md strikes through resolved entries with resolution note + phase + timestamp."

---

## Appendix B: SDDForge cross-pollination (2026-05-14)

Reference: external Codex-built scratch project at `/Users/mykolakudlyk/Projects/private/sddforge` (TypeScript CLI for SDD wrapper workspace). Reviewed 2026-05-14 — two design patterns from sddforge are worth recording for `/specify`. Both are **deferred, not adopted**, per the YAGNI discipline in `feedback_track_a_yagni_rollback`. This appendix is the recoverable spec — code lands only when a real consumer surfaces.

Source files reviewed:

- `private/sddforge/src/core/requirements.ts` — deterministic EARS normalizer + ambiguity-term scanner.
- `private/sddforge/src/schemas/spec.ts` — zod `requirementSchema` with `superRefine` for EARS shape per type (mirrors what `verify-ac-shape` already encodes).
- `private/sddforge/docs/ROADMAP.md` §"Canonical Artifact Model" + §"Epic 5 — Approval Gates" — versioned-artifact + gate-record schema described in roadmap (no code yet in sddforge; `gate` command is vapor as of 2026-05-14).

### B.1 Ambiguity-term lint

**Spec (if built)**:

- Add `src/devforge/lib/_ambiguous_terms.py` as sibling to existing `src/devforge/lib/_banned_phrases.py`. Same shape: `AMBIGUOUS_TERMS: Tuple[str, ...]` with case-insensitive whole-word `\b` match, hyphens as boundaries.
- v0 seed list (from sddforge `requirements.ts` lines ~111-134, deduplicated): `as needed`, `appropriate`, `better`, `easy`, `efficient`, `etc`, `fast`, `friendly`, `improve`, `intuitive`, `maybe`, `nice`, `optimize`, `probably`, `quick`, `reasonable`, `robust`, `seamless`, `simple`, `some`, `soon`, `user-friendly`. 22 entries.
- New helper subcommand: `specify_helper verify-ac-ambiguity` — scans every AC `statement` for any term in the list; emits `LintIssue { code: "ambiguous", severity: "warning", featureId, requirementId, message: "AC statement contains ambiguous term '{term}'" }`.
- Default severity = warning (non-blocking, surfaces in Phase 5 approval summary). Zero-escape-hatch: `--strict` flag promotes to error and blocks `set-status Approved` only when explicitly invoked.

**Relationship to existing `verify-ac-shape`**:

- `verify-ac-shape` checks structural EARS conformance (Ubiquitous starts with "the", Event-driven starts with "when", contains "shall", etc.) — already specified in Work order Step 3 Phase 4.
- `verify-ac-ambiguity` checks semantic vagueness — orthogonal, runs after `verify-ac-shape`. An AC like "The system shall respond fast" passes the EARS Ubiquitous regex but fails the ambiguity scan.
- Both share `LintIssue` shape if introduced.

**YAGNI verdict**: build only if Step 8 testForge20 empirical run produces at least one AC that passes EARS regex but is clearly untestable due to a weasel word. Until then the list lives in this appendix as recoverable spec. Open Question #12 carries the empirical trigger.

### B.2 Durable gate-record schema

**Spec (if built)**:

- Add `src/devforge/lib/_schemas/gate.py` (new directory — first pydantic schema package in `lib/`). Schema:

  ```python
  from datetime import datetime
  from typing import Literal
  from pydantic import BaseModel, Field

  GateStage = Literal["context", "spec", "impact", "plan", "breakdown", "verification", "acceptance"]
  GateStatus = Literal["approved", "denied", "deferred"]

  class GateScope(BaseModel):
      paths: list[str] = Field(default_factory=list)
      files: list[str] = Field(default_factory=list)

  class GateRecord(BaseModel):
      version: Literal[1] = 1
      gateId: str
      stage: GateStage
      createdAt: datetime
      status: GateStatus
      approvedArtifact: str
      approvedScope: GateScope = Field(default_factory=GateScope)
      denied: GateScope = Field(default_factory=GateScope)
      nextAllowed: GateStage | None = None
      approvedBy: Literal["user"] = "user"
      relatedArtifacts: dict[str, str] = Field(default_factory=dict)
  ```

- Target-side artifact location: `<target>/.devforge/gates/<stage>-<runId>.json`. One file per approval. Append-only; never overwrite.
- New `specify_helper` subcommands (extend Work order Step 3 Phase 5):
  - `record-gate --stage spec --artifact specs/NNN-feature-name/spec.md --scope-paths <…> --denied-paths <…> --next-allowed plan` — writes the gate file. Called by Phase 5 on `set-status Approved`.
  - `list-gates --stage spec` — enumerates all spec gates across sessions.
  - `show-gate <gateId>` — dumps full record.
  - `latest-gate --stage spec` — returns the most recent approved gate for resume.

**Relationship to existing `set-status Approved`**:

- Current Phase 5 design (line 631 of this plan) writes `status: Approved` into `.devforge/specify-state.json`. This file is overwritten on every `/specify` run — it answers "what's the status NOW" but not "what was approved last week, by whom, with what scope". Gate records add the durable history.
- Downstream `/plan` preflight could query `latest-gate --stage spec` to confirm the spec it's planning was actually approved (today this is implicit — `/plan` reads `specs/NNN/spec.md` and trusts the embedded `Status: Approved` marker).

**YAGNI verdict**: build only when /plan + /breakdown ship AND the multi-stage approval chain creates a "did I approve this last session" problem in practice. Until then, `specify-state.json` covers single-session resume. Open Question #13 carries the trigger. If built, the same schema should generalize to other stages (`/plan`, `/breakdown`) — design the helper to live in `src/devforge/lib/gate_helper.py` rather than embedded in `specify_helper.py`, so downstream commands can write their own gate records without depending on `/specify`'s helper.

### B.3 Patterns observed but NOT borrowed

For completeness, the sddforge patterns reviewed and rejected for `/specify`:

- **Hardcoded normalization branch** (sddforge `requirements.ts` `if (lower.includes("rate limit") && lower.includes("login"))`) — demo-driven, would fail `feedback_sentence_level_hallucination_check_specs`. Skip.
- **TypeScript + pnpm + zod stack** — wrong stack for ADTF (vendored Python helpers + Claude Code markdown specs). Migration cost ≫ marginal static-check value. Skip.
- **Single-file artifact store (sddforge `artifacts/specs/specs.json`)** — `/specify` writes per-spec directories under `specs/NNN-feature-name/` already; single-file collapse is a regression. Skip.
- **`status: draft | approved | implemented | verified | rejected` requirement enum** — overlaps with existing `Status: Approved` spec-level marker. Per-requirement status enum is a downstream `/plan` / `/verify` concern, not `/specify`. Skip at /specify; revisit when /verify plan opens.

### B.4 Recovery path

If this appendix needs to be acted on:

1. Re-read `private/sddforge/src/core/requirements.ts` for the ambiguity-term list + linter contract.
2. Re-read `private/sddforge/docs/ROADMAP.md` §"Canonical Artifact Model" + §"Epic 5 — Approval Gates" for the gate-record metadata field list.
3. Cross-check against `src/devforge/lib/_banned_phrases.py` (existing pattern sibling) before adding `_ambiguous_terms.py`.
4. Cross-check against `src/devforge/lib/cbm_sync_helper.py` + `src/devforge/lib/init_helper.py` `.devforge/state.json` writes (existing artifact-emission patterns) before adding `gate_helper.py`.
5. Update Work order Steps 2 + 3 inline rather than re-introducing this appendix as a separate plan file.

All four blocks are **additive** — they extend v3 mechanics, do not replace v3 prose. Variance impact: EARS ↓ axis 4; constitution-recheck neutral; test_anchor neutral; resolve-open-question neutral on /specify (writes happen at downstream phases). Net prediction: equal-or-better than v3 baseline.
