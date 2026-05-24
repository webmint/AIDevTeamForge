# Plan: Widget Catalog Full-Text Search

**Date**: 2026-05-22
**Spec**: specs/009-widget-catalog-search/spec.md
**Status**: Draft

## Specialist Consultation

**Invocations**:
- Phase 0 alternatives: no — N/A (client-side only, no 2+ architectural alternatives)
- Phase 1.3 architecture decisions: yes (mandatory)
- Specialists consulted: see table below

| Specialist | Sub-question | Input summary | Verdict | Cites |
| --- | --- | --- | --- | --- |
| backend-engineer | Should search run server-side? | No — spec §7 forbids new endpoint | accepted | spec.md §7 |
| db-engineer | <the specific sub-question> | <1-line summary of their input> | accepted | <file:line or doc ref> |
| (none) | — | — | — | — |

**Verdict** must be one of: `accepted` / `modified` / `rejected` / `no-response`. Every row requires a **Cites** entry.

**Architect-authored sections** (transcribed verbatim from architect return):
- Layer Map: rows 1-2
- Key Design Decisions: rows 1-1
- Risk Assessment seeds: rows 1-2

## Summary

Adds client-side keyword search to the widget catalog page.
Typing filters the rendered widget list by name and tag; clearing restores the full list.

## Technical Context

**Architecture**: Presentation layer only — no backend changes required
**Error Handling**: Graceful fallback to full list on filter error
**State Management**: Local component state for the search query string

## Constitution Compliance

- No new backend endpoint: compliant — filter runs entirely in the Presentation layer
- Dependency injection: compliant — filter predicate injected, not hardcoded

## Implementation Approach

### Layer Map

| Layer | What | Files (existing or new) |
| --- | --- | --- |
| Presentation | Search input + filter wiring | src/widgets/catalog_page.ts (existing) |
| Presentation | Filterable list renderer | src/widgets/widget_list.ts (existing) |
| [placeholder] | [placeholder] | [placeholder] |

### Key Design Decisions

| Decision | Chosen Approach | Why | Alternatives Rejected |
| --- | --- | --- | --- |
| Filter location | Client-side substring | Spec §7 forbids a new backend endpoint | Server-side full-text index |
| Match strategy | Name + tag substring | Spec §6 excludes fuzzy matching | Levenshtein distance |
| [decision] | [approach] | [rationale] | [alternatives] |

### File Impact

| File | Action | What Changes |
| --- | --- | --- |
| src/widgets/catalog_page.ts | Modify | Add search input element and wire change handler |
| src/widgets/widget_list.ts | Modify | Accept filter predicate; render filtered set |
| src/widgets/widget_filter.ts | Create | New substring filter over name and tag |
| tests/widgets/widget_filter.test.ts | Create | Unit tests for the filter function |
| [path] | Create/Modify | [brief description] |

### Documentation Impact

| Doc File | Action | What Changes |
| --- | --- | --- |
| docs/widgets/overview.md | Update | Document new search capability |
| docs/widgets/architecture.md | Update | Add filter predicate injection pattern |
| [path] | Update | [brief description] |

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- |
| Large catalogs make client-side filtering janky | Med | Med | Debounce input and cap rendered rows at 200 |
| Tag field missing on legacy widgets | Low | Low | Treat absent tag as empty string in filter |
| [risk] | Low/Med/High | Low/Med/High | [how to handle] |

## Dependencies

No external package dependencies — uses native DOM APIs only.
Requires widget-core >= 1.0 (already installed).

## Supporting Documents

- No deep research was needed (no signals detected — all libraries already in stack).
