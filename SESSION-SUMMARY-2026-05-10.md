# Session summary 2026-05-10 — `/configure` shipped, `/constitute` next

Branch: `develop-2.0-init`. Last commits: docs/v2/ARCHITECTURE.md /configure section + Step 7+8 status flips.

## What shipped this session

`/configure` feature-closed end-to-end. Verified empirically on testForge20 (wrapper + 26-pkg monorepo).

**Commit ledger (~20 commits this session):**

| Step | What |
|---|---|
| 0 | Scaffolding + emitter wiring |
| 1 | FIELD_SCHEMA (28 fields) + emit/parse + 4 read-* subcmds |
| 2 | 27 setters + atomic `_state_transaction` + flock |
| 3 | render-config + verify + summary |
| 4 | substitute-templates engine (25 placeholders, 4 categories) |
| 5 | Spec authoring (main.md + q11-tiers.md + q12-ac.md) |
| — | tree-annotator delete (concern 3 of agent-pruning trio) |
| — | applies_to frontmatter on 16 agents |
| — | Pruning system (project_natures field + prune-agents subcmd + tests) |
| — | Phase 5.2 spec + emitter passthrough + plan count sync |
| 6 | index.json shape drift + wrapper-mode read-configs |
| 6 | Phase 3 stop-discipline directive |
| 6 | JSON-array setter + case-insensitive enum + Phase 3 echo cancel |
| 6 | per-package framework_hint helper-side enforcement |
| 6 | dash-delimited frontmatter parser (installed agents) |
| — | install.sh stray-state-file guard + .gitignore |
| 7+8 | install.sh chain message + ARCHITECTURE-PIVOT status flip + memory |
| — | docs/v2/ARCHITECTURE.md /configure section |

## Final empirical state on testForge20

- 28 fields persisted in `.devforge/configure.yaml`
- 36 keys rendered in `.devforge/project-config.json`
- Agent pruning live: 4 dropped (backend-engineer, db-engineer, migration-engineer, mobile-engineer), 12 kept
- `CLAUDE.md` + 12 surviving `.claude/agents/*.md` substituted clean (only deliberate `{{UPPERCASE}}` identity passthrough remains)
- `ac_runtime_url: https://okta.local.dev.dice-tools.com:8080` (wrapper-mode fix verified)

Suite: 1678 tests OK, skipped=3.

## What's next — `/constitute` schema-anchor

Per `ARCHITECTURE-PIVOT-PLAN.md` §Step 8. Existing memory: `project_schema_anchored_constitute.md` (schema design — 7 sections, closed rule-tag enum, validated against `cse-strata-ws-forge/constitution.md`). Read that memory + ARCHITECTURE-PIVOT §Step 8 first.

### Patterns to inherit from `/configure` (mirror exactly)

1. **Single-file helper.** `src/devforge/lib/constitute_helper.py` — no submodule split (configure_helper is the size template, ~3.5k lines).
2. **State + render shape.**
   - State: `.devforge/constitute.yaml` (canonical, atomic write)
   - Render artifact: `constitution.md` at install root (regenerated each `render` call; never edited between renders)
3. **`_state_transaction` with `fcntl.LOCK_EX`** on `<constitute.yaml>.lock` sidecar. All setters route through it.
4. **Validation helpers.** Reuse the 5 patterns:
   - `_validate_scalar` — non-empty after strip
   - `_validate_enum` — case-insensitive, normalize to canonical (rule-tag input `extracted` / `EXTRACTED` / `Extracted` → canonical case)
   - `_validate_string_array` — accept BOTH JSON-array form (`'["a", "b,c"]'`) AND comma-sep (TS generic syntax `Either<DataError, T>` requires JSON form)
   - `_validate_path_value` — non-empty, no newlines
   - `_validate_verbatim` — non-empty, preserve internal whitespace
5. **Subcommand surface.** Mirror `/configure`'s grouping: reset / read-* (capture inputs as JSON) / setters / render / verify / summary.
6. **Phase shape.** Mirror `/configure`:
   - Phase 0: pre-flight gate (init.yaml + configure.yaml + docs/overview.md + docs/architecture.md + docs/glossary.md present)
   - Phase 1: reset + read-* (capture JSON variables)
   - Phase 2: orchestrator-direct compose (NO subagent dispatch)
   - Phase 3: plain-prose bulk-confirm with explicit STOP discipline directive (NOT AskUserQuestion — multi-line content)
   - Phase 4: sequential AskUserQuestion for any user-only fields (if needed)
   - Phase 5: render
   - Phase 6: verify + summary

### Empirical bugs to PREEMPT (all surfaced + fixed during /configure; bake fixes in from day one)

7. **Phase 3 stop discipline.** Plain-prose echo has no harness wait. Spec MUST explicitly say "end assistant turn after echo; do NOT call any tool / subcommand in same turn." Otherwise LLM auto-advances past confirmation.
8. **Internal-comma values break comma-sep split.** TypeScript generics, parenthetical clauses with internal commas. JSON-array form support is non-negotiable from day one.
9. **LLM lowercases enum values.** Case-insensitive `_validate_enum` is non-negotiable.
10. **install.sh stray-state-file guard.** Already includes `constitute.yaml` + `constitute.yaml.lock`. `.gitignore` complements. Forward-compat shipped 2026-05-10.
11. **Wrapper-mode path resolution.** Helpers reading source files MUST consult init.yaml's `workspace_mode` + `project_root`. Read-* subcmds prepend `project_root` when wrapper. Pure-`docs/`-reading subcmds don't need this (docs/ lives at install root in wrapper mode).
12. **Re-install propagation.** When iterating, re-run install.sh to propagate framework src changes into target's `.devforge/lib/`. LLM session running the slash command may have cached the older spec — fresh session start ensures latest spec read.
13. **Frontmatter parsing dual-form.** N/A for /constitute body markdown. Pattern exists in `_parse_agent_frontmatter` if future agent-touching work needs it.

### Schema specifics for /constitute

Per `project_schema_anchored_constitute.md` memory:

- 7 top-level constitution.md sections
- Closed rule-tag enum: `extracted` / `enforced` / `universal` / `project-specific`
- Code examples + rule tables per section
- Validated against cse-strata-ws-forge constitution.md (451 lines)

Render pattern: manual concatenation per section + per rule, mirroring `/generate-docs`'s render approach (no template engine; helper owns markdown shape).

### Test bed

testForge20 has `/init-forge` + `/generate-docs` + `/configure` all run end-to-end. State preserved:
- `.devforge/init.yaml` (wrapper, db-cse-ui-strata, 26 packages)
- `.devforge/configure.yaml` (28 fields populated)
- `docs/{overview,architecture,glossary}.md` rendered
- `CLAUDE.md` substituted

Fresh `/constitute` invocation will read these + synthesize `constitution.md`.

`cse-strata-ws-forge/constitution.md` is the empirical reference shape (451 lines; read during schema validation).

### Resume protocol

1. Read this file in full.
2. Read `ARCHITECTURE-PIVOT-PLAN.md` (§Step 8 specifically).
3. Read memory `project_schema_anchored_constitute.md` for schema design.
4. Read `docs/v2/ARCHITECTURE.md` §4 (`/configure`) — mirror its patterns for `/constitute`.
5. Read `CONFIGURE-PLAN.md` as template for writing new `CONSTITUTE-PLAN.md`.
6. Read `src/devforge/lib/configure_helper.py` for helper pattern detail (single-file, ~3.5k lines, 32 subcmds).
7. Confirm test baseline: `python3 -m unittest discover tests/lib` — 0 failures.
8. Write `CONSTITUTE-PLAN.md` mirroring CONFIGURE-PLAN's structure (Status / Goal / Architecture / Helper subcommand registry / Phase shape / Step work order with verify criteria).
9. Execute Steps 0-N per new plan, using iterative apply-verify loop:
   - python-engineer writes function + tests in same turn
   - python-reviewer audits; loop until clean
   - instruction-author writes spec; instruction-reviewer + claude-code-guide audit; loop until clean
10. Empirical run on testForge20 after Step 5 (spec authoring) — expect 3-6 follow-up commits to settle Step 6 bugs.

### Open follow-ups (not blocking /constitute)

- Pivot Step 7: full delete of `setup-wizard/` source + `detect_report.py` + `wizard_render.py`. Emitter already drops them; src retained as historical reference. Schedule during /constitute work or after.
- /configure cosmetic: PACKAGE_STACKS framework column reads stray manifest deps honestly (codebase hygiene issue surfaces, e.g., pkg-cse-common stray React dep). Substitute engine matches DOCS-example placeholders. Phase 2 LLM compose drift across re-runs.
- Per-record subfield override syntax in Phase 3 parser (e.g., `package_stacks.<pkg>.framework: null`) — currently NOT supported; minor cleanup.

### Cleanup checklist post-/constitute

When `/constitute` ships + verified end-to-end:
- ARCHITECTURE-PIVOT-PLAN.md §Step 8 → DONE
- CLAUDE.md "Active work" → strike through CONSTITUTE-PLAN.md
- docs/v2/ARCHITECTURE.md → add §5 `/constitute` section, renumber CBM hooks + later sections
- Memory: project_4command_architecture_pivot.md → all 4 commands DONE
- New session-summary doc replacing this one

Pivot status post-/constitute: full 4-command sequence shipped. Pivot plan retired.
