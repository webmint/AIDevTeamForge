# MIG-2957 — Comparative Analysis of Five AI-Generated Solutions

**Date**: 2026-07-31
**Analyst**: Claude (Fable 5), evidence-based comparison
**Task**: Remove the `distributionChannel`, `primaryShipToCity`, and `primaryShipToState` filters from the `searchOrganizationsV2` query on the "Suggested" Customer search.

**Method**: All five solutions were diffed against the same dev baseline (`c94d18d1`), type-checked (`tsc --noEmit`), and had the full `pkg-cse-core` vitest suite executed in isolated git worktrees. A probe test simulating the order-detail modal path (Surface B) was run against every solution. Routing claims were verified from source code only (`AccountsBLoC`, `DealerToAccountNumberModal`, both use cases) — not from spec documents, to avoid biasing toward the local solution.

---

## 1. The Solutions

| ID | Location | Tool | Author | Files | Δ Lines |
|---|---|---|---|---|---|
| **A** | local `bugfix/MIG-2957-mk` | Claude Code (spec-driven pipeline) | Webmint | 5 | +487 / −32 |
| **B** | `origin/bugfix/MIG-2957` | Cursor (corroborated, not proven¹) | npineda | 3 | +9 / −8 |
| **C** | `origin/bugfix/MIG-2957-test` | Claude + custom skills | Anton Dvornyk | 6 | +155 / −33 |
| **D** | `origin/test/MIG-2957` | Kiro | Mykola Kudlyk | 6 | +194 / −2 |
| **E** | `origin/test/MIG-2957-curs` | Cursor agent | Mykola Kudlyk | 3 | +22 / −5 |

¹ B's attribution is not from the MIG-2957 commits themselves (no trailer). It rests on: (a) the branch owner's stated recollection, initially a similarity-based guess; (b) hard evidence that npineda uses Cursor on this repo — commit `2691f6d5` (MIG-2875) carries the machine-added `Co-authored-by: Cursor <cursoragent@cursor.com>` trailer. Treat as probable, not proven. Note that code-shape similarity alone is unreliable for attribution here: D (Kiro) and E (Cursor) produced near-identical mechanisms while the two supposed Cursor runs (B, E) chose different ones — on a narrow ticket, competent agents converge on the same minimal shapes regardless of vendor.

**Key structural fact discovered during analysis**: `SUGGESTED_CUSTOMERS` runs on **two live surfaces** — the Customers tab "Suggested" sub-tab (Surface A → `SearchSuggestedOrganizationsV2UseCase`) and the order-detail delivery modal (Surface B → accounts `SearchOrganizationsV2UseCase`, because `DealerToAccountNumberModal` provisions the BLoC without identity hooks, so `isInternal` = false and the fetch falls through to the passport path with `tabType = CUSTOMER`). Surface B sends the city/state search terms (never `distributionChannel`). The ticket requirement was Surface A only; solution A deliberately covered both (author's informed decision, made knowing both screens existed).

---

## 2. Verification Matrix

| Check | A (Claude Code) | B (Cursor) | C (Claude+skills) | D (Kiro) | E (Cursor agent) |
|---|---|---|---|---|---|
| `distributionChannel` removed (Surface A) | ✅ | ✅ | ✅ | ✅ | ✅ |
| city/state removed (Surface A) | ✅ | ✅ | ✅ | ✅ | ✅ |
| city/state removed (Surface B, modal) | ✅ | ❌ still sent | ❌ still sent | ❌ still sent | ❌ still sent |
| Contract tab / Dealer tabs preserved | ✅ | ✅ | ✅ | ✅ | ✅ |
| `tsc --noEmit` clean | ✅ | ✅ | ✅ | ✅ | ✅ |
| New test failures vs baseline (6 pre-existing) | 0 | +5 (unrelated, stale base) | 0 | 0 | 0 |
| Tests added | **25** (both surfaces, use-case level) | 0 | 8 (service level) | **12** (incl. use-case level) | 0 |
| Based on current dev | ✅ | ❌ 146 files behind | ✅ | ✅ | ✅ |
| Repo commit convention `[MIG-XXXX] - ` | ✅ | ✅ | ✅ | ❌ `feat(...)` | ✅ |
| Ships clean | ⚠️ 2 stray `console.log` in working tree | ⚠️ needs rebase | ✅ | ✅ | ✅ |

---

## 3. Design Quality Analysis

### A — Claude Code (local)

**Mechanism**: `getCustomerSuggestedFilters()` composes a new shared private `getBaseOrgTypeAndStatusFilters()` + `getSalesAreaFilters({includeDistributionChannel: false})`. `buildSearchQueryFilters` gains a SHIP_TO early return — both surfaces covered through the shared builder, no signature changes.

- ✅ **DRY**: only solution that extracted the duplicated type/status blocks instead of copy-pasting them
- ✅ Removed two pre-existing `as any` casts (type-safety improvement)
- ✅ Best tests by far: deep-tree assertions, positive *and* negative checks, both surfaces, captures the actual repository input
- ✅ Two-screen coverage was a deliberate, researched decision — the divergence between identical searches is prevented, not created
- ⚠️ Encodes broad policy ("SHIP_TO tabs never search address fields") — correct for today's entire live call graph (verified: no caller ever passes CONTRACT), but a future Contract-tab caller would silently inherit it; doc comments mitigate
- ⚠️ Two uncommitted `console.log` debug lines must be dropped before commit

### B — Cursor (npineda)

**Mechanism**: `getContractTabFilters(options?)` gains an opt-out flag; customer delegates to it with `{includeDistributionChannel: false}`; `buildSearchQueryFilters` gains `includeAddressFields`, passed from the suggested use case only.

- ❌ **Leaky abstraction**: Customer semantics threaded through a *Contract*-named public API
- ❌ **Dual mechanisms**: `buildSearchQueryFilters` now honors both the old userType-based internal-dealer check *and* the new flag — two ways to express one thing
- ❌ No tests; stale base (146 files behind dev, needs rebase); 3-commit history with churn
- ✅ Smallest diff; compiles; no behavioral collateral

### C — Claude + custom skills (Anton)

**Mechanism**: Full refactor — replaces `userType` inference with intent-named options (`searchPrimaryAddressFields` / `sortByPrimaryAddressFields`) across `mapSortField` and `buildSearchQueryFilters`; shared `getNationalAccountFilters()` base; all three use-case callers updated.

- ✅ **Best pure design of the branches**: explicit intent over identity-inference, single mechanism, no duplication
- ✅ Outstanding commit message — documents the 'sunbelt' timeout context, the MIG-2458 precedent being replaced, and what to escalate to the backend team
- ❌ **Widest churn for a bugfix ticket**: public API signatures changed, dealer use case touched, internal-dealer business rule relocated out of the service into every caller (future callers must remember to opt out)
- ⚠️ Tests stop at service level — nothing proves the wire-level query
- Verdict: right refactor, wrong PR

### D — Kiro

**Mechanism**: Additive-only — `buildSearchQueryFilters` gains a 4th optional param `{isSuggestedTab?}`; the suggested use case passes it; `getCustomerSuggestedFilters` builds its own filter list with `{includeDistributionChannel: false}`.

- ✅ **Most disciplined diff**: exactly scoped to the ticket, zero signature breakage, zero collateral
- ✅ Only branch with a use-case-level test capturing the actual repository input, plus regression tests for Contract/Dealer tabs
- ❌ **DRY violation**: copy-pastes the type/status blocks from `getContractTabFilters`
- ❌ `isSuggestedTab` names the *caller*, not the behavior (control coupling); condition `isSuggestedTab && tabType === CUSTOMER` couples service to caller context
- ❌ Imposed its own `feat(MIG-2957):` commit convention instead of the repo's `[MIG-XXXX] - `

### E — Cursor agent

**Mechanism**: Same shape as D — additive `{omitAddressFields?}` param passed from the suggested use case for CUSTOMER; copy-pasted customer filter list.

- ✅ **Best flag name of all five**: `omitAddressFields` describes behavior, not caller
- ✅ Updated doc comments on `getSalesAreaFilters`; correct commit convention
- ❌ Same copy-paste DRY violation as D
- ❌ **Zero tests** — for a filter-shape change that's invisible until someone compares result sets

---

## 4. Rankings

**Final ranking** (two-screen coverage counted as the author's deliberate, informed decision):

| Rank | Solution | Tool | One-line verdict |
|---|---|---|---|
| 🥇 | **A** | Claude Code | Only solution built with full knowledge of the call graph; covers both surfaces by decision; best tests and DRY structure |
| 🥈 | **D** | Kiro | Best strictly-ticketed solution: minimal, additive, well-tested |
| 🥉 | **E** | Cursor agent | Right shape, best flag name — but untested |
| 4 | **C** | Claude + skills | Best engineering of the branches, in the wrong PR |
| 5 | **B** | Cursor | Leaky API, dual mechanisms, no tests, stale base |

**Sensitivity to scope interpretation**: under a strict "Screen 1 only, no exceptions" reading, A's Surface B coverage is unrequested behavior change and D wins (D > E > C > A > B). A's position depends entirely on the two-screen decision being ratified — which it was, and which should be recorded in the PR description and confirmed with the ticket owner.

---

## 5. Observations

1. **The single most consistent differentiator across all five runs was test coverage.** Both Cursor runs shipped zero tests; Claude and Kiro shipped meaningful ones. Whatever tool is used, "did it write tests?" should be the first review question for agent-produced PRs.
2. **Both Claude runs investigated before editing** — C's commit message demonstrates deep context discovery (timeout history, precedent commits, tab-to-query mapping); A found a second live surface no other solution knew existed. The flip side: both did more than the minimal ask (C's cross-cutting refactor, A's scope extension). Thoroughness and scope discipline pulled in opposite directions.
3. **Kiro behaved like a spec-executor**: safest, most surgical diff, tests at the right boundary — but no restructuring the spec didn't mention (hence the copy-paste), and it imposed its own commit convention rather than reading the repo's.
4. **Same tool, different outcomes**: Cursor produced both the cleanest minimal branch (E) and the weakest solution (B) — driver and context mattered as much as the product.
5. **Only two solutions were forensically attributable from git alone**: E (Cursor's `Co-authored-by` trailer) and A (this workspace's documented pipeline). B, C, D left no tool fingerprint in their own commits — commit trailers are currently the only reliable provenance marker. B was later corroborated as probable-Cursor via the author's prior trailered commit (see footnote ¹); C and D attributions rest solely on the experiment owner's records.
6. **Recommended merge path**: take D's scoping discipline, rename its flag to E's `omitAddressFields`, port A's test suite (re-pointed per the chosen scope), and record the Surface B decision in the PR — that combination beats any single solution as submitted.
7. **Pre-ship actions for A** (if chosen as-is): delete the two `console.log` lines; add the two-sentence scope rationale to the PR; get the ticket owner's cheap veto on the Surface B extension now rather than a bug report later.
