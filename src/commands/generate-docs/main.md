---
description: Plan F vertical slice (concern tier only) — preflight + per-concern compose/render/validate. Package + project tiers ship under forthcoming F.4 expansion.
---

# /generate-docs — Plan F vertical slice (concern tier)

**Status (2026-05-07)**: this command runs the concern-tier pipeline end-to-end. Package and project tier dispatches (F.7 / F.8 / F.4 expansion) are NOT yet wired — those phases are no-ops in this build. The vertical slice exists to validate F.0 → F.2 → F.3 → F.4 setters → F.5 validate-doc → F.4 render-doc against testForge20 before scaling to upper tiers.

The full Plan E skeleton-fill spec is preserved at git commit `bdae59d` (`git show bdae59d:src/commands/generate-docs/main.md > src/commands/generate-docs/main.md` to restore).

---

## ⚠️ TEST SCOPE OVERRIDE — pkg-cse-client ONLY (V5 SMOKE)

**Active until removed.** V5 empirical smoke for the F.7 package tier flow on the smallest viable package. Phase 2 concern tier loop is restricted to the scope below; Phase 3 package tier loop runs against the same package set.

**In-scope concerns**:
- `db-cse-ui-strata/packages/pkg-cse-client/*` — 14 files / 2 concerns. Exercises both per-concern dispatch (Phase 2) AND multi-concern aggregation in package overview/architecture (Phase 3).

**Out-of-scope (deferred)**:
- `pkg-cse-core/*` — already rendered via prior V4 round. Stamp-gate skips concerns; package tier deferred until V5 design proven on pkg-cse-client first.
- Every other package + app-web — focus V5 on smallest viable target.

Behavior: after preflight returns `concerns[]`, FILTER to entries whose `<package>/<concern>` starts with `db-cse-ui-strata/packages/pkg-cse-client/`. Process the filtered list. Phase 3 derives unique packages from the filtered concerns set (just `pkg-cse-client` here) and runs the package overview + architecture pipelines.

**Expected dispatches**: 2 concern + 2 package-tier (overview + architecture) = 4 dispatch units. Wall-clock target: ~3-4 min. Cost target: ~$0.50.

**Removing this override**: after V5 passes (clean docs land + validate-doc green), expand to multi-package or rip the override entirely. Phase 2/3 then process the full preflight `concerns[]` list.

---

## ⚠️ HELPER CHAIN MANDATORY — NO ALTERNATIVE PATHS, NO SUBAGENT DISPATCH

**Active for the entirety of this command.** The Phase 2 per-concern flow MUST go through the helper chain in this order:

```
init-doc → set-doc-purpose → set-doc-structure → render-doc → validate-doc
```

Concern-tier authoring is **orchestrator-direct**: the main /generate-docs thread reads the F.2 concern-input batch JSON inline and emits Purpose + per-leaf annotations itself. NO Task-tool dispatch to the doc-composer subagent. Empirical V4 finding: doc-composer subagent dispatch costs 30-90K tokens per concern + redundant source-file Read calls inside the subagent. Orchestrator-direct is 3-10× cheaper because the orchestrator already has session context loaded; it just inlines the concern's batch JSON (~3-5K tokens) and emits structured output (~2-4K tokens).

The following are FORBIDDEN under /generate-docs:

- Dispatching the `doc-composer` subagent via the Task tool. The agent file at `src/agents/doc-composer.md` is reference material describing the output contract; it is NOT invoked at runtime in this build.
- Writing concern markdown to disk via the Write tool (helper owns that path via `render-doc`).
- Running custom Python or bash that emits markdown content directly to `docs/<pkg>/<concern>/index.md`.
- Invoking Part D setters (`set-concern-overview`, `set-concern-tree`, `add-concern-export`, `add-concern-type`, `add-concern-dep`, `add-concern-hazard`, `set-concern-usage-example`, `render-concern-doc`, `validate-concern`) — those are dormant Plan E primitives that emit the wrong shape.
- Running `reset` (Part D primitive) — `init-doc` resets the F.4 state slot wholesale on every call.
- Writing defensive cleanup of `.devforge/.f4-doc-state.json` — `init-doc` is idempotent and self-resets.
- Using `set-package-*` or `add-package-*` setters — those are Plan E package tier (not yet ported).
- Adding `## Hazards` to concern docs. Hazards are out of scope for /generate-docs; they belong to `/audit` (separate command, on-demand quality review). Concern docs carry **only** `## Purpose` and `## Structure` (annotated tree).

The helper chain is the ONLY canonical path. Any divergence emits the wrong shape and breaks downstream consumers expecting Plan F (`## Purpose`, `## Structure`).

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

After preflight returns `concerns[]`, apply the TEST SCOPE OVERRIDE filter (above) — keep only entries under `db-cse-ui-strata/packages/pkg-cse-core/`. Drop the rest.

Then for each kept entry where `status` is `changed` or `new`, run Steps 2.1–2.5 in order. The retry loop wraps Steps 2.3–2.5 (capped at 3 retries).

### Step 2.1 — Pull batch input (helper, once per concern)

```
./.devforge/lib/generate_docs_helper concern-input \
    --package "$pkg" --concern "$concern"
```

Capture full JSON output to a variable. Fields used downstream:
- `tree_text` — mechanical ASCII tree from index.json, fed to `set-doc-structure`
- `files[].path` — project-relative file paths
- `files[].comment_rich_span` — top-of-file lines + TODO context windows; used by orchestrator to infer leaf annotations
- `source_stamp` — frontmatter input

### Step 2.2 — init-doc with helper-built frontmatter + F.2 tree

```
./.devforge/lib/generate_docs_helper init-doc --tier concern --target "$pkg/$concern" \
    --frontmatter "$(jq -n --arg c "$concern" --arg p "$pkg" --argjson f "$files_count" \
                       --arg s "$source_stamp" --arg d "$today" \
                       '{concern:$c, package:$p, files:$f, source_stamp:$s, last_indexed:$d}')" \
    --tree "<step 2.1 tree_text verbatim>"
```

Frontmatter values:
- `concern`, `package` — string literals from the preflight entry
- `files` — count from `concern-input`'s JSON `files` field
- `source_stamp` — `concerns[*].source_stamp` from preflight
- `last_indexed` — today's ISO date (`date -u +%Y-%m-%d`)

`init-doc` writes `docs/<target>/index.md.skeleton` with frontmatter + Purpose placeholder + ## Structure section + the F.2 tree wrapped in a `text` code fence. Re-running overwrites the skeleton. No `.devforge/.f4-doc-state.json` — the skeleton file IS the state.

### Step 2.3 — Compose Purpose + leaf annotations (orchestrator-direct, NO subagent)

The orchestrator (the main /generate-docs thread) reads the Step 2.1 batch JSON inline and produces:

1. **Purpose** — 1-3 sentences describing what the concern does. Concrete + cross-cuts named. No banned phrases ("this document", "in this section", "various", "several", "many", "some", "other"). Sourced from filename inference + `files[].comment_rich_span` content.

2. **Annotations** — a flat `{<basename>: <1-line description ≤60 chars>}` JSON map covering every non-trivial leaf in `tree_text`. One annotation per leaf. Skip canonical-aggregator filenames (`mod.rs`, `lib.rs`, `__init__.py`, `index.ts`, `index.js`, `doc.go`).

Do NOT dispatch the `doc-composer` subagent. Agent file at `src/agents/doc-composer.md` describes the contract for reference; it is not invoked at runtime in this build.

For monster concerns (>100 leaves), the orchestrator emits the annotations map progressively in chunks during a single response — Plan F's set-doc-structure helper accepts the full map atomically; the orchestrator must build the map fully before invoking the setter.

### Step 2.4 — Setters

Two setter calls (Hazards dropped — `/audit` territory). Setters edit the skeleton file in-place:

```
./.devforge/lib/generate_docs_helper set-doc-purpose --tier concern --target "$pkg/$concern" \
    --text "<orchestrator-composed Purpose>"

./.devforge/lib/generate_docs_helper set-doc-structure --tier concern --target "$pkg/$concern" \
    --annotations '<orchestrator-composed {basename: annotation} JSON>'
```

`set-doc-purpose` replaces the `<!-- TODO: purpose -->` placeholder with the supplied text (idempotent — re-running with new text replaces the prior content).

`set-doc-structure` walks lines inside the ` ```text ` fence and appends `  # <annotation>` to each leaf line whose basename matches an entry in `--annotations`. Idempotent — leaves already annotated are passed through.

The orchestrator MUST NOT:
- Write the markdown directly via the Write tool
- Run custom Python or bash that emits markdown directly to docs/

Disk writes happen via the setters (in-place skeleton edit) and Step 2.5's `render-doc` (atomic rename).

### Step 2.5 — Render + validate

```
./.devforge/lib/generate_docs_helper render-doc --tier concern --target "$pkg/$concern"
./.devforge/lib/generate_docs_helper validate-doc --tier concern --target "$pkg/$concern"
```

`render-doc` renames `docs/<target>/index.md.skeleton` → `docs/<target>/index.md` (atomic; no content mutation).

- Both exit 0 → done with this concern; advance to next.
- validate-doc exit 2 → capture stderr verbatim. Re-run Step 2.2 (init-doc, wipes the skeleton), then Step 2.3 (orchestrator re-composes Purpose + annotations using the stderr as feedback) → Step 2.4 → Step 2.5. Cap at 3 retries; on the 4th, surface failure to the user and continue with the next concern.

**Why init-doc on retry**: re-init wipes the skeleton wholesale; setters overwrite cleanly. Cheaper than tracking partial state.

---

## Phase 3 — Package tier loop (after concern tier completes)

After Phase 2's concern docs are all rendered + validated, run the package tier for every package whose concerns appeared in the concern-tier loop. Two docs per package: `overview.md` + `architecture.md`. (Glossary tier dropped 2026-05-08 — Purpose paragraphs surface terms in context.)

For each in-scope package P (derive the unique set from preflight's `concerns[*].package`):

### Step 3.1 — Pull batch input

```
./.devforge/lib/generate_docs_helper package-input --package "$P"
```

Returns JSON with `concern_seeds[]` (frontmatter + Purpose text from each rendered concern doc) + `package_root_files[]` (README/CHANGELOG/package.json comment-rich spans) + `source_stamp`.

If all of P's concerns were `status=unchanged` AND the prior package overview/architecture docs' frontmatter `source_stamp` matches the new `source_stamp` from package-input → SKIP this package's package-tier dispatches. (Per-package stamp comparison; F.0 currently does NOT compute package stamps, so the orchestrator does this check inline.)

### Step 3.2 — package-overview pipeline

Frontmatter:
```json
{"package": "<P>", "last_indexed": "<today>", "source_stamp": "<from package-input>"}
```

```
./.devforge/lib/generate_docs_helper init-doc --tier package-overview --target "$P" \
    --frontmatter "$FM"
```

Compose orchestrator-direct (no subagent):
- **Purpose** (1-3 sentences) — synthesize across `concern_seeds[*].purpose_text` + `package_root_files[*].comment_rich_span`. Cross-cuts named. Banned phrases absent.
- **Concerns** (bullet list) — one entry per `concern_seeds[*]`: `{name: <concern>, role: <one-line role from concern_seeds[*].purpose_text>, cite: <docs/<P>/<concern>/>}`.
- **Files** (bullet list) — one entry per `src_root_files[*]`: `{name: <basename>, role: <1-line description from comment_rich_span>}`. Loose files at `<P>/src/` root (e.g. `index.ts` barrel, `env.d.ts`, `apolloClient.ts`) are NOT inside any concern subfolder; this section surfaces them at package tier so they don't fall through unannotated.

```
./.devforge/lib/generate_docs_helper set-doc-purpose --tier package-overview --target "$P" --text "..."
./.devforge/lib/generate_docs_helper set-doc-concerns --tier package-overview --target "$P" \
    --concerns '<json array>'
./.devforge/lib/generate_docs_helper set-doc-files --tier package-overview --target "$P" \
    --files '<json array>'
./.devforge/lib/generate_docs_helper render-doc --tier package-overview --target "$P"
./.devforge/lib/generate_docs_helper validate-doc --tier package-overview --target "$P"
```

On validate-doc failure: re-init the slot + re-compose with stderr as feedback. Cap 3 retries.

### Step 3.3 — package-architecture pipeline

Frontmatter (same shape as 3.2). Sections:
- **Layers** (bullet list) — derived from concern groupings in `concern_seeds[]` (e.g., concerns under `presentation/`, `domain/`, `data/`) + cross-package layer cites. Each entry `{name, role, cite}`.
- **Patterns** (bullet list) — package-wide conventions from `package_root_files[]` + cross-concern patterns observed in `concern_seeds[]`. Each entry `{name, rule, cite}`.

```
./.devforge/lib/generate_docs_helper init-doc --tier package-architecture --target "$P" \
    --frontmatter "$FM"
./.devforge/lib/generate_docs_helper set-doc-layers --tier package-architecture --target "$P" \
    --layers '<json array>'
./.devforge/lib/generate_docs_helper set-doc-patterns --tier package-architecture --target "$P" \
    --patterns '<json array>'
./.devforge/lib/generate_docs_helper render-doc --tier package-architecture --target "$P"
./.devforge/lib/generate_docs_helper validate-doc --tier package-architecture --target "$P"
```

Same retry semantics as Step 3.2.

## Phase 4 — Project tier (NO-OP in this build)

Project overview/architecture docs ship under forthcoming F.8. Skip silently.

---

## Phase 5 — Verify

For each rendered doc — concern AND package tier — walk the on-disk file and run `validate-doc` once more (defensive — per-tier validation in Steps 2.5/3.2/3.3 should have caught everything). Aggregate any new failures.

---

## Phase 6 — Report

Print:
- Total concerns from preflight: `concern_counts.unchanged + .changed + .new + .empty`
- Concerns dispatched: count of `changed + new`
- Concerns skipped via stamp gate: `unchanged`
- Concerns rendered + validated: count of green
- Concerns failed after 3 retries: list with paths
- Packages dispatched (Phase 3): count + skipped count
- Package overview docs rendered + validated: N
- Package architecture docs rendered + validated: N
- Package-tier failures: list with paths
- Wall-clock: vue-extract + index_repository + per-concern + per-package dispatch totals
- Token-cost estimate: ~$0.10-0.20 per dispatched concern + ~$0.05-0.15 per package tier doc (Haiku)

---

## Restoring the full Plan F flow

This is the vertical slice. The full multi-tier flow (F.4 with all tiers) lands once F.7 + F.8 input helpers ship and the package/project setter primitives are added. When that lands, replace this main.md with the full Plan F.4 spec.
