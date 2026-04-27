# /setup-wizard — Project Initialization Wizard

You are running the initial setup wizard for AIDevTeamForge. Your job is:

1. Analyze the current project.
2. Ask the user targeted questions via confirm / override / defer.
3. Substitute the user's answers into the `{{PLACEHOLDER}}` markers in every target file that has them. All files are already in place — **you do NOT create new files**.
4. Where specific files have designated project-specific sections (e.g., CLAUDE.md architecture notes, agent files with project paths), append content derived from detection + user answers to those sections only. **Never rewrite whole files.**
5. Write the answers record to `.devforge/project-config.json` so later commands and `update.sh` can consume user decisions.

## Variation markers (template syntax)

This wizard and its reference files use a small set of variation markers that the install-time emitter processes. When the emitter has run, you should see these already substituted. If you encounter any of them unsubstituted, treat them as follows rather than emitting the literal `{{...}}` text to the user:

- `{{ask "question text"}}` … `{{/ask}}` — interactive user-question block. **Invoke the AskUserQuestion tool to present this question.** The marker's bullet list (the `- option` lines between the `{{ask}}` and `{{/ask}}` tags) maps directly to the tool's `options` array. The same contract applies to questions described in prose `>` blockquotes inside the reference files (questions.md Q0–Q11, etc.) — they are interactive questions and follow the same rules even though they do not use the literal `{{ask}}` marker.

  **AskUserQuestion mechanics — apply to every interactive question:**

  - **Option count must be 2–4.** The tool rejects more than 4 options. If the spec lists 5+ options, restructure (split into a two-step funnel, collapse into broader buckets, or drop the question to a plain prompt) — do NOT silently truncate the option list.
  - **Never include an "Other" option in the list.** The tool injects "Other" automatically as a free-text affordance. Listing it explicitly wastes a slot.
  - **Use `multiSelect: true` for multi-pick questions.** No more "pick one or pick Multiple → follow-up" workarounds — model multi-pick natively (e.g., Q11 verification modes).
  - **Bypass the tool when AskUserQuestion can't represent the question.** Two cases: (1) **free-text-only** — the question has no enumerable options (e.g., "Describe this project in 1–3 sentences", "What languages will you use?") and AskUserQuestion requires at least 2 options. (2) **>4-option exceptions** — questions whose full taxonomy genuinely doesn't fit 4 options and doesn't fit a funnel/bucket restructure (e.g., Q2 with 13 project-type categories). For >4-option exceptions, prefer a two-tier flow: small AskUserQuestion at L1 ("use suggestion / browse full list") with a plain-prose listing at L2 only when the user opts in. Either case uses a plain `>` blockquote prompt instead of the tool.
  - **Recommended option goes first** with a `(Recommended)` suffix on the label.
  - **Batch only the 3-tier model question (Q10).** AskUserQuestion accepts 1–4 questions per call and Q10's three tier picks (Think / Do / Verify) are independent and presented together — batch them in a single call. Every other question is its own call.

  **One turn = one AskUserQuestion call** (except Q10's batched tier picks). Never present multiple unrelated questions in a single call even though the tool allows up to 4 — each question is a distinct user-input stop with its own answer-dependent follow-ups.

  **Wait-before-compute for conditional follow-ups.** When a question has a sub-follow-up whose content depends on the user's answer (e.g., Q11 `Runtime-assisted` selected → URL prompt; wrapper-mode selected → folder-name prompt), do NOT compute, pre-render, or present the follow-up until the primary answer is in hand. Follow-up defaults (URL defaults, option subsets) depend on the primary answer — batching them in with the primary question pre-commits the user to a path they haven't chosen yet.

  This contract applies in every command that uses `{{ask}}` or describes interactive questions in prose — wizard, onboard, constitute, breakdown, specify, verify, and any future interactive command.

Any `{{UPPERCASE}}` marker (e.g., `{{PROJECT_NAME}}`, `{{LANGUAGE}}`) is a wizard-substitution placeholder — the wizard itself fills these with user answers or detection values during Phase 3. Do NOT emit them literally to user-visible output; substitute before presenting.

## Execution Flow

Execute these phases in order. Each phase's detailed instructions live in a dedicated reference file; **read the reference file fully before executing the phase.** Do not attempt any phase from memory or guesses.

### Phase 0 — Reset stale helper state

Before invoking any helper setter, clear any state files left over from a previous interrupted wizard run:

```
scripts/lib/detect_report reset
scripts/lib/wizard_render reset
```

Both commands are idempotent — they delete the state file if present, no-op otherwise. Skipping this risks silent duplication: `add-language`, `add-architecture`, etc. append to whatever's already in state, so a re-run after interruption would produce `["TypeScript", "TypeScript"]` etc. and compose would emit corrupted output without complaint.

### Phase 1 — Detection (read-only)

**Read `references/detect.md` and follow it.** Covers:

- STEP 0: Workspace Mode Detection (wrapper vs standalone)
- STEP 1: Project State (empty / greenfield / brownfield)
- STEP 2: Default Branch
- STEP 3: Auto-Detect Project Structure (languages, frameworks, tooling)

Detection outputs are written to `.devforge/detection_report.yaml` via the `scripts/lib/detect_report` CLI helper at the end of Phase 1 (keys enumerated in `references/detect.md`). Later phases read this file directly — no conversational-memory handoff for structured detection values.

### Phase 2 — Questions (interactive)

**Read `references/questions.md` and follow it.** Covers Q0 through Q11 (project name, description, type, languages/frameworks confirmation, architecture pattern, error handling convention, API layer, testing framework, workflow enforcement, AI attribution, agent model assignments, AC verification). Questions Q3–Q7 produce per-stack arrays (`LANGUAGES`, `FRAMEWORKS`, `ARCHITECTURES`, `ERROR_HANDLINGS`, `API_LAYERS`, `TESTINGS`) — each parallel-indexed so downstream phases can reason per stack.

Retain every captured answer in conversational memory under the keys documented in `references/questions.md`.

### Phase 3 — Population (file substitution)

**Read `references/populate.md` and follow it.** Covers STEP 5: populating CLAUDE.md / Claude config files / baselines / MCP permissions / project config / memory seed / constitution header (§5.7) / docs stubs (§5.8), using the answers from Phase 2 and the detection data from Phase 1.

### Phase 4 — Agent Curation

**Read `references/agents.md` and follow it.** Covers STEP 6: selecting, removing, populating, and baselining agents for the project.

### Phase 5 — Summary

Present this summary to the user. **Substitute each `{VALUE}` placeholder below with the actual captured value** — do NOT emit the literal `{VALUE}` text. Detection-derived values come from `.devforge/detection_report.yaml`; Phase 2 question answers come from your working tracking. For `{N}` in the Packages line, compute `len(PACKAGES_DETECTED)`. Labels use plurals so they read naturally whether the project has one or many stacks. Include the `Packages:` line only when `PACKAGES_DETECTED` has 2 or more entries (multi-package project) — omit it for single-package projects.

```
## Setup Complete

### Populated Files:
- CLAUDE.md — Project instructions for Claude Code
- .devforge/project-config.json — Answers record (includes per-stack arrays and PACKAGE_STACKS)

### Project:
- Description: {PROJECT_DESCRIPTION}
- Type: {PROJECT_TYPE}
- Frameworks: {FRAMEWORKS joined with ", "}     (single-stack: one name; multi-stack: comma-joined list)
- Languages: {LANGUAGES joined with ", "}       (same rule)
- Packages: {N} detected (see `## Packages` in CLAUDE.md)   ← include only if multi-package

### Workspace Mode:
- Mode: {WORKSPACE_MODE}                          (value: "standalone" or "wrapper")
- Source Root: {SOURCE_ROOT}

### Next Steps:
1. Review CLAUDE.md — adjust if needed
{BRANCH ON PROJECT_STATE:
  if PROJECT_STATE == "brownfield":
    2. Run /onboard — scans your codebase and populates `docs/` + `.devforge/memory.md` with observed patterns, module boundaries, and pitfalls
    3. Run /constitute — turns onboard's findings and your architectural preferences into enforceable rules in `constitution.md`
    4. Start working with /specify "your first feature"
  else (PROJECT_STATE == "greenfield" or "empty"):
    2. Run /constitute — turns your architectural preferences (and framework best-practice research) into enforceable rules in `constitution.md`. Skip /onboard — there's nothing to scan yet.
    3. Start working with /specify "your first feature"
}
```

`.devforge/setup-complete` is written by `wizard_render compose` at the end of Phase 4 (see `references/agents.md` §6.7). The marker carries the timestamp + the authoritative list of files compose actually touched (presence-checked + conditional MCP/baseline writes included). Downstream commands check for the marker's presence — if missing, setup may have been interrupted mid-execution; surface this to the user and offer to resume or re-run.

## IMPORTANT RULES (global)

1. **Never guess** — if you can't detect something, ask
2. **File placement vs. population** — `install.sh` places all template files (`CLAUDE.md`, `constitution.md`, `docs/*`, `.claude/agents/*`, `.devforge/memory.md`, etc.) at install time. Phases 3 and 4 do NOT create new files; they compose values that the helper (`wizard_render compose`) substitutes into the placed templates. Phase 4 may delete rejected agent files (helper does the deletion); no Phase creates new files at runtime.
3. **Use real paths** — all paths must point to actual directories in the project
4. **Use real commands** — all commands must come from the project's actual scripts
5. **Validation is helper-owned** — `wizard_render compose` validates that no `{{PLACEHOLDER}}` markers remain unresolved and refuses to write if any do; on success the populated files are guaranteed clean. Do NOT read populated files back to re-verify.
6. **Wrapper isolation** — in wrapper mode, never create any artifact inside SOURCE_ROOT
7. **Same values in CLAUDE.md and project-config.json** — CLAUDE.md gets prose-substituted values; `.devforge/project-config.json` gets the same values as JSON
8. **References are not optional** — you MUST read each phase's reference file in full before executing that phase. Do not attempt any phase from memory of previous invocations or guesses. Missing instructions from a reference file means stopping and re-reading it, not improvising.
9. **Respect `{{ask}}` semantics** — one turn = one `{{ask}}`; never batch multiple questions into a single user-facing prompt; wait for the primary answer before computing or presenting any conditional follow-up. Full contract in the "Variation markers" section above.
