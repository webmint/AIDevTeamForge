# Phase 0 — Pre-flight Findings

Date: 2026-04-15
Branch: `feature/codex-support`

## Summary

All three load-bearing assumptions are resolved via documentation. Live-test fixtures are in `fixtures/` for later confirmation, but the architectural decisions below can be made now.

**Verdict: GO.** The generator-based architecture in `PLAN.md` §1 holds. Proceed to Phase A.

---

## 0.1 — `@import` transclusion: FALSE (as a cross-runtime mechanism)

| Location | Supports `@path` imports? | Source |
|---|---|---|
| Claude CLAUDE.md + `.claude/rules/` | **Yes** (documented) | [Claude Code memory docs](https://code.claude.com/docs/en/memory#import-additional-files) |
| Claude subagents `.claude/agents/*.md` | **Not documented** (treat as no) | [Claude Code subagents docs](https://code.claude.com/docs/en/sub-agents) — frontmatter fields listed; no mention of imports in body |
| Claude slash commands `.claude/commands/*.md` | **Not documented** (unknown — live test optional) | Not in docs |
| Codex AGENTS.md | **No** — "layered file discovery, not a modular inclusion system" | [Codex AGENTS.md docs](https://developers.openai.com/codex/guides/agents-md) |
| Codex subagents `.codex/agents/*.toml` | **No** — TOML schema requires inline `developer_instructions`; no include directive | [Codex subagents docs](https://developers.openai.com/codex/subagents) |
| Codex custom prompts `.codex/prompts/*.md` | **Deprecated** in favor of skills; import behavior not documented | [Codex custom prompts](https://developers.openai.com/codex/custom-prompts) |

**Decision locked in**: Generator is mandatory. The `.devforge/source/` → per-runtime generated files architecture stands. Do not rely on `@import` in any generated runtime file, even for the Claude side where it works in CLAUDE.md — consistency across runtimes is worth more than the small ergonomic win.

Exception: keep `@import` usage in the **user-facing CLAUDE.md** (project root) where it's the native mechanism to pull in shared context. This file is hand-authored, not generated.

---

## 0.2 — `.agents/skills/` cross-runtime: TRUE for Codex (Claude asymmetry noted)

Codex explicitly scans `.agents/skills/` at multiple levels:
- `$CWD/.agents/skills`
- Parent dirs up to `$REPO_ROOT/.agents/skills`
- `$HOME/.agents/skills`
- `/etc/codex/skills`

Source: [Codex skills docs](https://developers.openai.com/codex/skills) — "Skills build on the open agent skills standard (agentskills.io)."

**Asymmetry**: Claude Code stores skills in `~/.claude/skills/` or per-project `.claude/skills/`, **not** `.agents/skills/`. So the directory is not truly universal — Codex reads `.agents/skills/`, Claude reads `.claude/skills/`. This affects v1 slightly:

**Decision**: v1 generator writes skills into BOTH locations (copy, not symlink — symlinks are unreliable on Windows). One canonical source in `.devforge/source/skills/`, generator fans out to `.claude/skills/` and `.agents/skills/`.

Live confirmation: drop a test skill in `.agents/skills/codex-skill-pickup-test/` (already placed by fixture), run Codex CLI in this repo, ask it to invoke the skill. If it returns `CODEX-SKILL-PICKUP-CONFIRMED-9E4D`, docs match reality. See `fixtures/` + `HOW-TO-RUN.md`.

---

## 0.3 — Codex post-edit verification lifecycle: PARTIAL (the biggest gap)

Codex has hooks (experimental, feature-flagged via `codex_hooks = true`):

| Event | Equivalent of Claude Code event? | Note |
|---|---|---|
| `SessionStart` | Similar | — |
| `PreToolUse` | Similar (Bash only) | "Doesn't intercept all shell calls yet, only the simple ones" |
| `PostToolUse` | **Partial** | **Only fires on Bash tools. Does NOT fire on Write, Edit, MCP, WebSearch.** |
| `UserPromptSubmit` | Similar | — |
| `Stop` | Similar | — |

Source: [Codex hooks docs](https://developers.openai.com/codex/hooks).

**This is the critical gap.** AIDevTeamForge's PostToolUse hook today runs `tsc`/lint/build after every file edit (via Write/Edit tools). In Codex, `PostToolUse` will not fire on those tool calls — only after Bash commands.

**Decision locked in**: Phase D strategy #1 from the plan — **command-level verification as explicit step** — is required, not optional. Every code-writing command in `.devforge/source/commands/` needs to end with an explicit verify step that runs tsc/lint/build. This removes dependency on runtime hook lifecycles entirely and works uniformly across Claude and Codex.

Side benefit: simplifies the product story. "After I write code, I run a verify step" is a clear model; relying on invisible hooks is harder to explain.

---

## Additional discoveries

**Codex custom slash commands exist but are deprecated.** Markdown files in `~/.codex/prompts/` (user) or `.codex/prompts/` (project); filename becomes command name; supports `$1..$9`, `$ARGUMENTS`, `$$` for argument substitution. Deprecation notice: "Use skills for reusable instructions that Codex can invoke explicitly or implicitly."

**Implication for v1 Codex port**: two paths possible —

- **Path A (conservative)**: port 25 commands to `.codex/prompts/*.md`. Works today, 1:1 structural mapping to `.claude/commands/`. Risk: prompts are deprecated; may be removed in future Codex releases.
- **Path B (strategic)**: port 25 commands to skills under `.agents/skills/*/SKILL.md`. Aligns with Codex's recommended direction. Also works for Claude Code's skill mechanism. Risk: skills are "invoked when relevant" by the agent's judgment, which is less predictable than a user explicitly typing `/fix`.

**Recommendation**: **Hybrid — ship both.** Generator emits prompts AND skills from same source. Users invoke via `/fix` (prompt) or implicit skill trigger. Two files per command, generated, zero maintenance cost beyond the generator itself.

**Codex AGENTS.md byte limit**: 32 KiB default (`project_doc_max_bytes`). Current `CLAUDE.md` template may exceed this when expanded with imports — the AGENTS.md generator will need to produce a more compact version, possibly by moving detail into skills rather than inlining everything.

---

## Decisions locked

1. **Architecture**: single source `.devforge/source/`, per-runtime generators, no cross-file `@import` dependency in generated files.
2. **Verification lifecycle**: command-level explicit verify, not hook-based (works for both runtimes).
3. **Commands → skills + prompts hybrid** for Codex v1.
4. **Skills copied into both `.claude/skills/` and `.agents/skills/`** — not a single universal dir.
5. **AGENTS.md must stay under 32 KiB**; detail pushed into skill files, not inlined.

## Still open (non-blocking for Phase A)

1. Does `@import` work in `.claude/commands/*.md`? — can live-test, but generator-first decision makes this moot.
2. Live confirmation that `.agents/skills/` pickup works on actual Codex install (not just docs).
3. Prompt-quality delta between Claude and Codex on identical command — **this is Phase A's core question** and what the `/fix` spike will measure.

## Live-test fixtures (ready to run when you want confirmation)

See `fixtures/HOW-TO-RUN.md`.
