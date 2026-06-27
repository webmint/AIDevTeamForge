# Regression Anchors

Meta-bugs this framework has fixed, each pinned to the gate/test that guards it.
A future refactor that deletes a guard reintroduces the bug. The GUARD TEST is
the load-bearing anchor — re-run it; the SHA is historical provenance.
Reconstructed from git during a design-critique engagement (plan 45).

## 1. Orphaned agent — design-auditor named responsible, dispatched nowhere
A roster agent claimed a responsibility (visual-fidelity audit) that no command
dispatched. Born orphaned at `09bcbf2`; first real dispatch (`/review` PHASE 2.5)
at `6cc933c`.
- Guard: `tests/lib/test_agent_reachability.py` (orphan_agents + relay-only
  fixtures) — fails if a roster agent has no executor.
- Re-verify: `uv run --with pytest python -m pytest tests/lib/test_agent_reachability.py -q`

## 2. Design-manifest trigger skippable — reference present, manifest absent
A feature with `design/reference.html` could ship with no `design-manifest.json`,
leaving the design-fidelity gates nothing to check. Gate shipped at `f0a9e95`.
- Guard: `tests/lib/test_breakdown_helper.py::test_reference_present_manifest_absent_exits_2`
- Re-verify: `uv run --with pytest python -m pytest tests/lib/test_breakdown_helper.py -k reference_present_manifest_absent -q`

## 3. Import-handoff dedup gap — spec-state buckets overwritten without dedup
`/specify`'s import-handoff persisted duplicate / whitespace-variant seed entries
(overwrite, no cross-list dedup). Introduced `ccbd2db` (research lane) +
`8e4c8e9` (discover lane); fixed `de3f334`.
- Guard: `tests/lib/test_specify_helper.py::TestImportHandoffDedupe`
- Re-verify: `uv run --with pytest python -m pytest tests/lib/test_specify_helper.py -k TestImportHandoffDedupe -q`

---
NOT an anchor (recorded so it isn't re-attempted): the tier-1.5 "probe misroute"
was investigated and REJECTED — git showed no failing-state-then-fix. The probe
classifier was introduced complete at `dac77c9`, and its decision-tree body is
byte-identical to HEAD (the file itself moved at the `_research/` split `6c8545c`
and `af7f4ed` touched surrounding code — but the classifier logic is unchanged).
A phantom, not a fixture.
