# 28 — /generate-docs INCREMENTAL MODE

> **CLOSED 2026-08-07 — OUTDATED (maintainer disposition, not built).** The core cost this plan targeted is substantially addressed by shipped machinery: the cbm_sync preamble routes drift through `detect_changes` (not a full `index_repository`), and the `source_stamp` skip already gates the LLM compose. The remaining delta (skipping the whole-tree stamp scan) is not worth a build. Do not build; retained as rationale record.

**Status**: DEFERRED — decision recorded 2026-06-19, not started, no code yet. This file is a DECISION RECORD, not an active execution plan: it captures the chosen design so a future session does not re-litigate it. There is no per-phase task breakdown and no per-step `## Verify` — those get authored when this is promoted to a full plan (see `## When resuming work`).

## Problem

On repos where not every developer uses the framework, `docs/` drifts as non-framework devs commit changes that never run `/generate-docs`. Re-syncing periodically is the natural fix, but `/generate-docs` is disproportionately expensive for that job because every run pays a fixed overhead regardless of how small the delta is:

- A CBM `index_repository` reindex in preflight (the non-incremental full pass, as opposed to `detect_changes`) (`src/commands/generate-docs/main.md:77` — "CBM `index_repository` reindexes").
- A whole-tree `source_stamp` scan to compute the per-concern delta.
- A cost gate that recommends confirming above $5 / 5 min (`src/commands/generate-docs/main.md:92`, the threshold sentence; the `### Cost gate (split-aware estimate)` section heading is at :79).

The LLM compose work is ALREADY stamp-gated today — unchanged concerns skip dispatch via `source_stamp` (`src/commands/generate-docs/main.md` Phase 2 only processes `status ∈ {changed, new}`). So the waste is NOT recomposition; it is the fixed preflight + whole-tree-scan overhead paid even when one file changed, plus the lack of any way to scope a run to a subset of the tree.

## Chosen design — an incremental MODE on `/generate-docs`

Add an incremental MODE to the existing `/generate-docs` command. **NOT a standalone command, and NOT a `--module` flag.** The mode scopes the run to the files changed since the last index, using the git delta as the scoping mechanism:

1. Read `.devforge/cbm-last-indexed-sha` (the JSON stamp maintained by `cbm_sync_helper`, shape `{"git_sha": "<sha>", "indexed_at": "<iso8601>"}`; see the CBM-sync hooks in `src/CLAUDE.md`) and extract its `git_sha` field.
2. `git diff <git_sha>..HEAD --name-only` → the changed source files (cheap; no whole-tree hashing).
3. Map the changed files → only the affected concern/package docs; regenerate only those; propagate to the project tier only if a changed concern bubbles up; update the stamp. The concern/package topology comes from `.devforge/index.json` (already read by `generate_docs_helper preflight` for the `vue_extract` check), so a stripped preflight that skips the `source_stamp` hashing — or a direct `index.json` read — supplies the changed-file → concern-dir mapping without the whole-tree scan.
4. Swap the full `index_repository` preflight for `detect_changes` (incremental CBM); skip the whole-tree `source_stamp` scan.

The git-delta-since-last-index IS the scoping mechanism, so no `--module` flag is needed — the changed-file set already names the subset to regenerate.

## Why a standalone command was rejected

A second doc producer that bypasses the CBM / tier / glossary / cite-back model would drift `docs/` from `/generate-docs`'s shape and duplicate the doc-shape logic. One producer, one source of truth — the cheap path must be a MODE of the same producer, not a parallel command.

## Note on the pre-pivot draft

`src/_pending/commands/refresh-docs.md` is a pre-pivot standalone-command draft that calls itself a "lightweight alternative to `/onboard`" and routes `--all` to `/onboard`. It is RETAINED as reference prose only. It is superseded as a seed by this decision — do NOT build from it directly; build the mode into `/generate-docs`. Its Phase 1.2 git-delta prose (`git diff [base-commit]..HEAD --name-only`) is the closest existing description of the incremental scoping mechanism and may be referenced for that pattern only; its `--module` flag, tech-writer dispatch, and `/onboard` delegation are all superseded and must NOT be ported.

## When resuming work

This is a recorded decision, not an active build. Promote it to a full plan (phases + per-step `## Verify`) when scheduled, then re-confirm the cited `src/commands/generate-docs/main.md` line numbers and the `cbm_sync_helper` / stamp-file references against the live tree before writing any edit instruction.
