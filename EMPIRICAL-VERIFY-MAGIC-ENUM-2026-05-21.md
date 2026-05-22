# EMPIRICAL-VERIFY-MAGIC-ENUM — 2026-05-21

Phase 2 ledger for `01-CONSTITUTION-FORCING-FUNCTIONS-PLAN.md`. Empirical verify of `verify-magic-enum` (Phase 1 pilot) against the testForge20 consumer to validate the FP rate gate before extending the detector family.

## Procedure

- Consumer: `~/Projects/testForge20` (wraps `module`).
- Forge build: `develop-2.0-init` @ `ccc25b8` (Phase 1 commit) + one in-flight parser tightening (`_parse_type_unions` rejects object/function types in RHS).
- Config: ad-hoc `/tmp/phase2-magic-enum-verify/config.json` pointing `--root /Users/mykolakudlyk/Projects/testForge20`; generated_types_dirs at `module/packages/pkg-foo-types/src/generated` + `module/packages/pkg-foo-core/src/generated`; allowlist excludes `node_modules`, `.git`, `.devforge`, `dist`, `build`, test/mock/spec/fixture files, `scripts/`.
- Generated-types inventory: `index.d.ts` (587 KB) with 32 `export enum X { ... }` declarations including the seed case `Color.Red = 'RED'` at line 2561.

## Round 1 — verbatim Phase 1 detector

- Findings: **496** across 225 files.
- Distribution by literal:
  - `'id'` (71), `'name'` (36), `'AAA'` (27), `'BBB'` (26), `'Foo'` (25), `'ID'` (14), `'BILLING'` (14), `'STOCK'` (14), `'DRAFT'` (13), `'Foo'` matched 22 ambiguous enums.
- Multi-enum-match (literal collides with members of multiple distinct enums): 143 / 496 = **28.8%** ambiguous.
- Rough manual triage (LIKELY_FP-list + LIKELY_TP-list classification):
  - Lower-bound FP rate: 191 / 496 = **38.5%**.
  - Including ambiguous-multi-match as FPs: 230 / 496 = **46.4%**.
- **Phase 2 gate threshold (plan §"Phase 2"): ≤5%. Round 1 FAILS the gate.**

### Round 1 root cause

GraphQL-codegen-style `type X = { __typename?: 'Y', ... }` aliases were caught by `_parse_type_unions` as if they were string-literal unions. Example from `index.d.ts:4509`:

```ts
export type FooMutation = { __typename?: 'Mutation', fooField: { __typename?: 'Foo', id: number } };
```

Parser extracted `'Mutation'` + `'Foo'` as union members of `FooMutation`, flooding inventory with property-typed string literals. Every consumer reference to `'Foo'` in unrelated context — route name, log message, identifier — got flagged.

## Round 2 — parser tightening

Patch applied to `_inventory.py:_parse_type_unions`: reject RHS containing `{` (object type) or `=>` (function type). Two new tests pin the behavior (`test_inventory_rejects_object_typed_alias`, `test_inventory_rejects_function_typed_alias`). Test count: 303 → 305.

- Findings: **429** across 209 files (-67 vs Round 1; -13.5%).
- Top literals (same distribution, GraphQL `__typename` discriminators gone):
  - `'id'` (71), `'name'` (36), `'AAA'` (27), `'BBB'` (26), `'ID'` (14), `'BILLING'` (14), `'STOCK'` (14), `'DRAFT'` (13), `'type'` (11), `'ACTIVE'` (10), `'RETAIL'` (10), `'SHIPPING'` (9), `'INTERNAL'` (9).
- Multi-enum-match: 81 / 429 = **18.9%** (-9.9 pp).

### Round 2 quality

Remaining literals split into two qualitatively distinct buckets:

1. **High-actionable, semantic uppercase enum values** (truly magic strings duplicating enum members): `BILLING`, `SHIPPING`, `DRAFT`, `ACTIVE`, `RETAIL`, `STOCK`, `INTERNAL`, `CUSTOM`, `CITY`, `STATE`, `COUNTRY`, `ORDER_TYPE` — ~158 findings. These are textbook §3.5 violations the detector is designed to catch (the seed `Color.Red` is here).

2. **Low-actionable, generic lowercase enum values** (real enum members, but the literal collides with general property names): `id` (71), `name` (36), `ID` (14), `type` (11), `NAME` (7), `User` (10), `Order` (6), `Item` (6) — ~155 findings. Source: enums like `SortField { Id = 'id', Name = 'name', ... }` are codegen sort-field enums. Consumer code constantly uses `'id'` / `'name'` as property keys, query parameters, route names, fixture identifiers. The scanner cannot distinguish "magic-string dup of enum" from "general property-name string" without semantic / AST analysis it does not perform.

Net: ~37% of Round 2 findings are precision-bounded by the regex-only parser's lack of context awareness, not by parser bugs. **Round 2 still fails the 5% gate** by the same magnitude (low-actionable bucket is too noisy regardless of regex tightness).

## Decision point — surfaced to user 2026-05-21

The plan's ≤5% FP threshold was set without empirical data. testForge20 reveals the detector is structurally noisy on GraphQL-codegen-heavy TS codebases:

- **GraphQL sort-field enums** typically declare lowercase property-name members (`Id = 'id'`, `Name = 'name'`, ...). Every consumer use of those generic strings as property keys triggers a finding.
- **`__typename` discriminators** (Round 1 cause) — fixed in Round 2 parser tightening.
- **Type-discriminator names** (`'Foo'`, `'User'`, `'Order'`) — fixed in Round 2.

Round 2's ~38% rate is concentrated in the lowercase-enum-value bucket. Further regex tightening cannot fix this without semantic analysis (AST-based tree-sitter parsing of property-key context vs string-literal-value context).

Three forward paths:

1. **Tighten further with heuristics** — e.g., skip enum values where the value matches the lowercase form of its own member name (`Id = 'id'` → skip member). This drops the noisy bucket but loses some real violations where lowercase enum values ARE meaningfully duplicated (e.g., a sort-field literal in API construction). Need to confirm acceptable lossiness with the user.

2. **Adjust the FP threshold** — recognize that for this codebase shape, even 30% FP rate is actionable because the remaining 70% TP findings (semantic enum dups) are valuable and the noisy bucket can be allowlisted per-file. The plan's 5% bar was speculative.

3. **Defer Phase 3+4 + revisit Phase 1 strategy** — invest in AST-based parsing (tree-sitter or ts-morph subprocess) before extending the detector family. Higher upfront cost; higher precision ceiling.

## Recommendation

Document Round 2 as a meaningful precision improvement (-13.5% findings, 28.8% → 18.9% ambiguous) and decline to gate-pass on 5%. Two viable orchestrator-level next steps:

- **Pragmatic**: ship Path 2 (relax threshold; document detector's known precision floor; consumer enables per-detector with awareness). Phase 3+4 extend the family on the same regex-based substrate. Tree-sitter upgrade stays future-work for whoever owns precision regression on a real PR review surface.
- **Disciplined**: ship Path 1 (one more heuristic tightening + re-measure) OR Path 3 (tree-sitter upgrade now). Phase 3+4 blocked until Round N passes a revised gate.

User decision required before proceeding to Phase 3.

## Files modified (Round 2)

- `src/devforge/lib/_constitute/_forcing_functions/_magic_enum/_inventory.py` — `_parse_type_unions` rejects RHS containing `{` or `=>`.
- `tests/lib/test_magic_enum_inventory.py` — +2 regression tests.

Test suite: 305 pass (303 → 305).

## Out of scope (this ledger)

- Per-consumer custom inventory filter (e.g., "skip enums matching `*SortingField`"). Future-work; surface as detector config knob if Path 2 chosen.
- Tree-sitter upgrade. Future-work; large change requiring a separate dispatch + review loop.
- Second wrapper-consumer verify. Plan §"Phase 2" lists it; defer until first-consumer decision lands.
- Actual triage of every Round 2 finding to a definitive TP/FP. Rubric-based classification is sufficient for the decision; full triage requires consumer-developer review.
