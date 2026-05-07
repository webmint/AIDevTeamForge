---
description: Plan F vertical slice (concern tier only) — preflight + per-concern compose/render/validate. Package + project tiers ship under forthcoming F.4 expansion.
---

# /generate-docs — Plan F vertical slice (concern tier)

**Status (2026-05-07)**: this command runs the concern-tier pipeline end-to-end. Package and project tier dispatches (F.7 / F.8 / F.4 expansion) are NOT yet wired — those phases are no-ops in this build. The vertical slice exists to validate F.0 → F.2 → F.3 → F.4 setters → F.5 validate-doc → F.4 render-doc against testForge20 before scaling to upper tiers.

The full Plan E skeleton-fill spec is preserved at git commit `bdae59d` (`git show bdae59d:src/commands/generate-docs/main.md > src/commands/generate-docs/main.md` to restore).

---

## ⚠️ TEST SCOPE OVERRIDE — TWO TARGETS (TEMPORARY)

**Active until removed.** Phase 2 concern tier loop is restricted to the two scope sets below for the empirical iteration cycle. All other concerns from preflight's `concerns[]` list are DEFERRED — they remain unrendered for this run.

**In-scope concerns**:
1. `db-cse-ui-strata/apps/app-web/components` — single concern
2. `db-cse-ui-strata/packages/pkg-cse-core/*` — every concern under pkg-cse-core (e.g., `accounts`, `activeQuote`, `alerts`, `common`, `configurationMenu`, `customItem`, `favoriteQuotes`, `featureFlags`, `helpers`, `irw`, `itemsByBQids`, `itemsByPartNumbers`, `order`, `organizations`, `quote`, `quotes`, `salesForceContacts`, `securityRoles`)

Behavior: after preflight returns `concerns[]`, FILTER to entries whose `<package>/<concern>` matches one of the two patterns above. Process the filtered list. Skip every other concern silently.

**Removing this override**: when the iteration locks shape, delete this `## ⚠️ TEST SCOPE OVERRIDE` section. Phase 2 then processes the full preflight `concerns[]` list.

---

## ⚠️ HELPER CHAIN MANDATORY — NO ALTERNATIVE PATHS

**Active for the entirety of this command.** The Phase 2 per-concern dispatch MUST go through the helper chain documented below, in the order shown:

```
init-doc → set-doc-purpose → set-doc-structure → add-doc-hazard (×N) → render-doc → validate-doc
```

The following are FORBIDDEN under /generate-docs:

- Writing concern markdown to disk via the Write tool (helper owns that path via `render-doc`)
- Running custom Python or bash that emits markdown content directly to `docs/<pkg>/<concern>/index.md`
- Invoking Part D setters (`set-concern-overview`, `set-concern-tree`, `add-concern-export`, `add-concern-type`, `add-concern-dep`, `add-concern-hazard`, `set-concern-usage-example`, `render-concern-doc`, `validate-concern`) — those are dormant Plan E primitives; they emit the wrong shape
- Running `reset` (Part D primitive) — `init-doc` resets the F.4 state slot wholesale on every call
- Writing defensive cleanup of `.devforge/.f4-doc-state.json` — `init-doc` is idempotent and self-resets
- Using `set-package-*` or `add-package-*` setters — those are package tier (Plan E shape, not yet ported)

The helper chain is the ONLY canonical path for concern-tier doc authoring. Any divergence emits the wrong shape (Plan E sections like `## Overview`, `## Public Surface`, `## Types`, `## Dependencies`, `## Usage Example`) and breaks downstream consumers expecting Plan F (`## Purpose`, `## Structure`, `## Hazards`).

---

## Phase 0 — Pre-flight gate

1. `.devforge/index.json` exists:
   ```
   test -f .devforge/index.json
   ```
   If non-zero → ABORT: "missing .devforge/index.json — run /init-forge first."

2. `codebase-memory-mcp` binary on PATH:
   ```
   command -v codebase-memory-mcp >/dev/null
   ```
   If non-zero → ABORT with install link: `curl -fsSL https://raw.githubusercontent.com/DeusData/codebase-memory-mcp/main/install.sh | bash`.

---

## Phase 1 — Preflight (delegates to F.0)

```
./.devforge/lib/generate_docs_helper preflight
```

Captures stdout JSON. Key fields used downstream:
- `concerns[]` — list of `{package, concern, source_stamp, prior_stamp, status}`
- `concern_counts` — `{unchanged, changed, new, empty}`
- `vue_extract` + `index_repository` — wall-clock and counts; surface to user

vue-extract regenerates `.devforge/vue-tmp/`; CBM `index_repository` reindexes. Both idempotent. On non-zero exit → ABORT with stderr verbatim.

---

## Phase 2 — Concern tier loop (only changed/new, scope-filtered)

After preflight returns `concerns[]`, apply the TEST SCOPE OVERRIDE filter (above) — keep only entries matching `db-cse-ui-strata/apps/app-web/components` OR any concern under `db-cse-ui-strata/packages/pkg-cse-core/`. Drop the rest.

Then for each kept entry where `status` is `changed` or `new`, run Steps 2.1–2.6 in order. The retry loop wraps Steps 2.2–2.6 (capped at 3 retries; init-doc is NOT re-run on retry because it wipes setter state).

### Step 2.1 — Pull batch input (helper, once per concern)

```
./.devforge/lib/generate_docs_helper concern-input \
    --package "$pkg" --concern "$concern"
```

Capture full JSON output to a variable. Used downstream for both the dispatch payload and the `tree_text` passed to `set-doc-structure`.

### Step 2.2 — init-doc with helper-built frontmatter

```
./.devforge/lib/generate_docs_helper init-doc --tier concern --target "$pkg/$concern" \
    --frontmatter "$(jq -n --arg c "$concern" --arg p "$pkg" --argjson f "$files_count" \
                       --arg s "$source_stamp" --arg d "$today" \
                       '{concern:$c, package:$p, files:$f, source_stamp:$s, last_indexed:$d}')"
```

Frontmatter values:
- `concern`, `package` — string literals from the preflight entry
- `files` — `concerns[*].source_stamp` count is implicit; use the count from `concern-input`'s JSON output (`files` field)
- `source_stamp` — `concerns[*].source_stamp` from preflight
- `last_indexed` — today's ISO date (`date -u +%Y-%m-%d`)

`init-doc` resets the slot every call (Purpose / Structure / Hazards wiped to empty). The orchestrator does NOT need to clear `.devforge/.f4-doc-state.json` separately — that file is helper-owned.

### Step 2.3 — Dispatch doc-composer (Task tool, agent type `doc-composer`)

Pass:
- `tier=concern`
- `batch_json=<Step 2.1 JSON output>`
- `previous_attempt_feedback=<empty on first attempt; verbatim Step 2.6 stderr on retry>`

Agent's full instructions live at `src/agents/doc-composer.md` (installed at `.claude/agents/doc-composer.md`). Strict LLM-first density format; output is Markdown with `## Purpose`, `## Structure`, `## Hazards` anchors.

### Step 2.4 — Parse + invoke setters

Parse the agent's output by `## ` anchor. Then run the three setters in this order:

```
./.devforge/lib/generate_docs_helper set-doc-purpose --tier concern --target "$pkg/$concern" \
    --text "<purpose section content>"

./.devforge/lib/generate_docs_helper set-doc-structure --tier concern --target "$pkg/$concern" \
    --tree "<step 2.1 tree_text verbatim>" \
    --annotations '<json map of {filename: annotation_string} extracted from composer Structure>'

# Hazards: one add-doc-hazard call per bullet
./.devforge/lib/generate_docs_helper add-doc-hazard --tier concern --target "$pkg/$concern" \
    --text "<bullet text without trailing cite>" \
    --cite "<file:line OR file:start-end OR file:line1,line2>"
```

The orchestrator MUST NOT:
- Write the markdown directly via the Write tool
- Run custom Python that bypasses these setters
- Concatenate composer output into `docs/<pkg>/<concern>/index.md` itself

The setter chain owns disk writes via Step 2.5's `render-doc`.

### Step 2.5 — Render

```
./.devforge/lib/generate_docs_helper render-doc --tier concern --target "$pkg/$concern"
```

Writes `docs/$pkg/$concern/index.md`. Helper owns the markdown shape (frontmatter + 3 sections); LLM-supplied values fill the slots. No Write-tool call by the orchestrator at any phase.

### Step 2.6 — Validate

```
./.devforge/lib/generate_docs_helper validate-doc --tier concern --target "$pkg/$concern"
```

- Exit 0 → done with this concern; advance to next.
- Exit 2 → capture stderr verbatim; loop back to Step 2.3 with `previous_attempt_feedback=<verbatim stderr>`. Do NOT re-run Step 2.2 (init-doc) on retry — that wipes prior setter state and forces composer to redo its work for no reason. Re-running setters via Step 2.4 OVERWRITES purpose/structure (those setters are idempotent); for Hazards, the orchestrator MUST clear them first by running `init-doc` again — accept the trade-off (one re-init per failed validate).
- Cap at 3 retries; on the 4th, surface failure to the user and continue with the next concern. The failed doc is left unrendered.

**Retry-cycle nuance**: because `add-doc-hazard` appends, the only safe way to retry hazards is to re-init the slot (which re-wipes Purpose / Structure / Hazards). On retry, the cycle becomes: init-doc → composer → set-doc-purpose → set-doc-structure → add-doc-hazard ×N → render-doc → validate-doc. Same shape as the first attempt; just re-runs.

---

## Phase 3 — Package tier (NO-OP in this build)

Package overview/architecture/glossary docs ship under forthcoming F.4 expansion. Skip silently.

## Phase 4 — Project tier (NO-OP in this build)

Project overview/architecture docs ship under forthcoming F.4 expansion. Skip silently.

---

## Phase 5 — Verify

For each rendered concern doc, walk `docs/<pkg>/<concern>/index.md` and run `validate-doc` once more (defensive — Step 2.5 should have caught everything). Aggregate any new failures.

---

## Phase 6 — Report

Print:
- Total concerns from preflight: `concern_counts.unchanged + .changed + .new + .empty`
- Concerns dispatched: count of `changed + new`
- Concerns skipped via stamp gate: `unchanged`
- Concerns rendered + validated: count of green
- Concerns failed after 3 retries: list with paths
- Wall-clock: vue-extract + index_repository + per-concern dispatch totals
- Token-cost estimate: ~$0.10-0.20 per dispatched concern (Haiku, ~10K input + ~5K output)

---

## Restoring the full Plan F flow

This is the vertical slice. The full multi-tier flow (F.4 with all tiers) lands once F.7 + F.8 input helpers ship and the package/project setter primitives are added. When that lands, replace this main.md with the full Plan F.4 spec.
