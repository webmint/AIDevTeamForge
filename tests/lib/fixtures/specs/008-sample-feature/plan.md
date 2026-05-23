# Plan: Widget Catalog Search

**Date**: 2026-05-22
**Status**: Approved
**Spec**: specs/008-sample-feature/spec.md

## Summary

Add a client-side keyword search box to the widget catalog page. Typing filters
the rendered widget list by name and tag; clearing the box restores the full list.

## Architect Consultation

Consulted: none. Single-package, single-layer client change — no cross-boundary
decision required.

## Architecture Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Filter location | Client-side | Spec §7 forbids a new backend endpoint |
| Match strategy | Substring on name + tag | Spec §6 excludes fuzzy matching |

### File Impact

| File | Action | Notes |
|------|--------|-------|
| src/widgets/catalog_page.ts | Modify | Add the search input element and wire its change handler |
| src/widgets/widget_list.ts | Modify | Accept a filter predicate and render the filtered set |
| src/widgets/widget_filter.ts | Create | New substring filter over name and tag |
| tests/widgets/widget_filter.test.ts | Create | Unit tests for the filter |

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Large catalogs make client-side filtering janky | Med | Med | Debounce input and cap rendered rows |
| Tag field missing on legacy widgets | Low | Low | Treat absent tag as empty string |

### Dependencies

| Dep | Version | Note |
|-----|---------|------|
| widget-core | 1.0 | required |
