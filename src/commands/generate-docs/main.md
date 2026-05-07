---
description: Plan F vertical slice (concern tier only) — preflight + per-concern compose/render/validate. Package + project tiers ship under forthcoming F.4 expansion.
---

# /generate-docs — Plan F vertical slice (concern tier)

**Status (2026-05-07)**: this command runs the concern-tier pipeline end-to-end. Package and project tier dispatches (F.7 / F.8 / F.4 expansion) are NOT yet wired — those phases are no-ops in this build. The vertical slice exists to validate F.0 → F.2 → F.3 → F.4 setters → F.5 validate-doc → F.4 render-doc against testForge20 before scaling to upper tiers.

The full Plan E skeleton-fill spec is preserved at git commit `bdae59d` (`git show bdae59d:src/commands/generate-docs/main.md > src/commands/generate-docs/main.md` to restore).

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

## Phase 2 — Concern tier loop (only changed/new)

For each `concerns[*]` entry where `status` is `changed` or `new`:

### Step 2.1 — Pull batch input

```
./.devforge/lib/generate_docs_helper concern-input \
    --package "$pkg" --concern "$concern"
```

Capture the batch JSON. Pipe to the dispatch.

### Step 2.2 — Dispatch doc-composer (Task tool, agent type `doc-composer`)

Pass:
- `tier=concern`
- `batch_json=<F.2 output>`
- `previous_attempt_feedback=<empty on first attempt; populated on retry>`

Agent's full instructions live at `src/agents/doc-composer.md` (or installed at `.claude/agents/doc-composer.md`). Strict LLM-first density format; output is Markdown with `## Purpose`, `## Structure`, `## Hazards` anchors.

### Step 2.3 — Parse + invoke setters

Parse the agent's output by `## ` anchor:
- Purpose section → `set-doc-purpose --tier concern --target "$pkg/$concern" --text "..."`
- Structure section → extract leaf annotations (lines containing ` — `) into a `{filename: annotation}` JSON map; `set-doc-structure --tier concern --target X --tree "<F.2 tree_text>" --annotations '<json-map>'`
- Each hazard bullet → `add-doc-hazard --tier concern --target X --text "..." --cite "..."`

First call to any setter for a target auto-creates the state slot via `init-doc`. Frontmatter is helper-supplied: source_stamp comes from preflight's `concerns[*].source_stamp`; files count from the same source; last_indexed = today's ISO date; concern + package = literals.

```
./.devforge/lib/generate_docs_helper init-doc --tier concern --target "$pkg/$concern" \
    --frontmatter "$(jq -n --arg c "$concern" --arg p "$pkg" --argjson f "$files_count" \
                       --arg s "$source_stamp" --arg d "$today" \
                       '{concern:$c, package:$p, files:$f, source_stamp:$s, last_indexed:$d}')"
```

### Step 2.4 — Render

```
./.devforge/lib/generate_docs_helper render-doc --tier concern --target "$pkg/$concern"
```

Writes `docs/$pkg/$concern/index.md`.

### Step 2.5 — Validate

```
./.devforge/lib/generate_docs_helper validate-doc --tier concern --target "$pkg/$concern"
```

Exit 0 → done. Exit 2 → capture stderr verbatim. Re-dispatch doc-composer (Step 2.2) with `previous_attempt_feedback=<verbatim stderr>`. Cap at 3 retries; on the 4th, surface failure to the user and continue with the next concern (the failed one is left unrendered for the user to inspect).

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
