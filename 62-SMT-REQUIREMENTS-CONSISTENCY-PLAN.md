# 62 — `/spec-check`: SMT Requirements-Consistency Command

**Status:** RATIFIED (Phase 0 complete 2026-07-15) / **Phases 1–8 SHIPPED 2026-07-15/16** — the feature is CODE-COMPLETE + DOC-COMPLETE (working tree, not committed); only **Phase 9 (consumer/testForge20 e2e) remains, user-driven HARD GATE.** Command RUNNABLE (emitter `_PROMOTED += spec-check`, emits folder+2 refs 0 `{{` leaks, `spec_check_helper` dispatches all 8 verbs, `spec-formalizer` agent emits `model: opus` + plan-41 reachability gate GREEN). Phase 8 docs done: `src/CLAUDE.md` catalog (chain `[/spec-check]` + caveat + bullet + Command Details, under-promise copy) + `src/devforge/storage-rules.md` row (plan-39 matching-pick gate) + repo-root `CLAUDE.md` active-work entry + `CHANGELOG.md` `[Unreleased]` feat entry; cross-ref sweep clean (0 dangling, only `_smt` ref is the deliberate rename note). Built behind python-engineer→python-reviewer + instruction-author→instruction-reviewer+claude-code-guide loops (~28 review findings fixed across phases; 1 claude-code-guide false-positive on `disable-model-invocation` REJECTED with evidence — it's on all 20 commands). Prior milestone: **Phases 1–6 SHIPPED 2026-07-15/16** (working tree; `_spec_check/{ir_schema,_solve,_consume,_brief,_report,_preflight,_seed,_cli}.py` + `spec_check_helper{,.py}` launcher + `_shared/{spec_acs,seed_schema}.py` relocations + `/specify` Phase-0.5 re-entry consumer generalized; `_spec_check` **327 tests** + `_shared` seed 52 + `_grill` 345 + `_verify` 544 regression green). **Package renamed `_smt` → `_spec_check`** (convention/`--only` fix). **D9 reconciled + D13/D14/OQ-9 added 2026-07-16** (post-ratification design critique). Phases 7–9 NOT started (Phase 7 now also owns emitter registration + D13 quorum).
**Branch:** `develop-2.0-init`
**Origin:** Surfaced 2026-07-15 during a Forge-vs-AWS-Kiro capability-gap research session. The one capability where Kiro's architecture is genuinely ahead of Forge, and it fits Forge's own "every gate is mechanical, not prose" philosophy. Phase-0 brainstorm + maintainer ratification completed this session.

---

## What this is

A new **standalone, opt-in `/spec-check` command** that reads a completed feature spec's acceptance criteria (ACs), uses an LLM to translate each AC into formal logic, and runs the **Z3 SMT solver** to *deterministically prove* whether the AC set is self-consistent. When two+ ACs cannot all hold, the solver returns the exact conflicting subset. It is the **first requirement-tier consistency check** in the framework.

Neurosymbolic — two parts, one soft, one hard:
1. **Auto-formalization (soft, LLM):** each AC → a typed constraint IR (helper owns the IR schema; the LLM fills values). E.g. "response < 100ms" → `response_ms < 100`.
2. **Logical analysis (hard, Z3):** the conjunction of formalized constraints is checked. `unsat` → contradiction; `unsat_core()` → the minimal conflicting AC set.

**Sound only over the subset the LLM formalized** — it proves the *formalized logic* is consistent, NOT the whole natural-language spec, and NOT semantic correctness. Do not frame it as "proves the spec is correct."

**Determinism is layered, and only one layer is deterministic (honest framing, see D13):** the Z3 proof is deterministic *given an IR*; the English→IR **formalization is a soft LLM step and is stochastic** — the same `spec.md` can formalize differently on two runs and flip the verdict. So the honest claim is "a deterministic proof over a human-checked, quorum-stable formalization" — NEVER a bare "deterministic proof of your spec." Verdict stability is bought by the D13 quorum pass + the D4 human check, not by Z3 alone.

---

## Ratified decisions (Phase 0, 2026-07-15)

### D1 — Home: standalone opt-in `/spec-check`, spec tier
NOT inside `/specify`, NOT inside `/grill`.
- **Why not `/grill`:** `/grill` attacks the *plan* (the HOW). Contradiction is a property of the *ACs* (the WHAT) = spec tier. Checking spec logic inside a plan-attacking command checks the right thing at the wrong tier, *after* the plan is built. Wanted: know ACs conflict *before* planning.
- **Why not inside `/specify`:** `/specify` is 888 lines, mandatory, and the heaviest-run command. Inline pays the cost on every spec run AND — because it's mandatory — a mistranslation false-positive would fire on *everyone* (collides with plan 19's cry-wolf discipline).
- **Why standalone opt-in wins:** layer-correct (operates on `spec.md` ACs), zero bloat to `/specify`, and opt-in kills the mandatory-false-positive problem outright (it only runs when the user invokes it). Mental model: **`/spec-check` is to `/specify` what `/grill` is to `/plan`** — an opt-in adversarial check, each guarding its own artifact, one tier apart.

### D2 — Output model: grill-shaped, with inverted confidence semantics
Writes `specs/[feature]/spec-check.md`, recommends a disposition, human owns the verdict. BUT the confidence meaning is *inverted* vs `/grill`:
- `/grill` findings are soft LLM opinion (`Likely`/`Speculative`).
- `/spec-check`'s Z3 proof is **hard** — a proven contradiction is math. The softness lives in a *different* place: the **LLM's English→logic translation**.
- The report therefore surfaces **two layers**: (a) "here's how I read your ACs as logic" [soft, LLM, the human checks THIS] and (b) "given that reading, these are provably incompatible" [hard, deterministic]. The reader's job is to check the *translation*, not the proof.

### D3 — Disposition: ~3-way (smaller target space than `/grill`)
`/grill` routes 4 ways to 4 tiers. `/spec-check` sits right after `/specify`, before `/plan` — its only backward target is one hop to the spec:
- **CONSISTENT** → proceed to `/plan` (no conflict, or nothing formalizable).
- **REVISE-SPEC** → back to `/specify`, fix the named conflicting ACs (translation confirmed correct by the human).
- **DISMISS** → false positive; the human says "you misread AC-3," proceed anyway.
Recommend-not-decide; the user owns the verdict.

### D4 — Human-check loop is the cry-wolf guard (OQ-3)
Because the softness is in the translation, `/spec-check` MUST surface the full formalization (variables + glosses + constraints + coverage ledger) for human confirmation before a contradiction is treated as real. This is not grill-parity nice-to-have — it's the mechanism that stops a mistranslation from becoming a false "your spec contradicts itself." DISMISS is the escape hatch when the human finds the translation wrong.

### D5 — Re-entry seed: Option B (structured, contained), schema promoted to `_shared/`
`/spec-check` emits a structured backward seed — it does NOT diverge from the framework's structured-handoff direction into a report-only dead-end.
- Seed file: `specs/[feature]/spec-check-seed.json` (honest filename — NOT `grill-seed.json`).
- `source="spec-check"`, `target_stage="spec"`, via the `ReEntrySeed` dataclass made **multi-source**.
- **Schema RELOCATED to `_shared/`, not edited in place:** move `seed_schema.py` (and `ReEntrySeed`) from `src/devforge/lib/_grill/seed_schema.py` → `src/devforge/lib/_shared/seed_schema.py`, and re-point `_grill`'s imports at `_shared` (byte-behaviorally identical; `_grill`'s test suite is the regression net). This mirrors exactly how plan 20 Phase 0 / plan 22 Phase 0 extracted the refutation engine + feature-scope resolver into `_shared/` so no command depends on another command's package. Without this, `_spec_check/` would import `_grill/` internals — breaking the independence the `_shared/` pattern guarantees and contradicting D10's "normal command helper" claim. `_spec_check/` and `_grill/` both import the seed schema from `_shared/` (which already ships as a cross-cutting always-copy — `/audit`/`/review`/`/grill`/`/verify` depend on it).
- **`seed_schema.py` change (in its new `_shared/` home):** `SEED_SOURCE = "grill"` (single-value equality gate, currently `_grill/seed_schema.py:50,126`) → a source enum `("grill", "spec-check")`, relaxing the `__post_init__` equality check to membership. Sanctioned generalization — plan 36 already grew `SEED_TARGET_STAGES` 3→4 the same way; `"spec"` is already a valid target (`seed_schema.py:52`).
- **`/specify` change (one line):** Phase 0.5's glob `specs/*/grill-seed.json` (`src/commands/specify/main.md:125`) → `specs/*/*-seed.json`. The consumer already filters on `target_stage == "spec"` and **ignores `source`** (verified — the word `source` does not appear in the block; it parses raw JSON inline, no helper, no dataclass), so no other `/specify` change is needed. `/specify` gains ~0 lines.
- **Blast radius is contained to `/specify`** because `/spec-check`'s `target_stage` is always `"spec"` — the other three seed consumers (`/research`, `/discover`, `/plan`) never match a spec-targeted seed, so their globs stay as-is.
- Emitted only on the REVISE-SPEC matching pick (mirrors plan 39's verdict-gated seed-write — no orphan seed on a DISMISS/CONSISTENT/overridden verdict).

### D6 — Constraint IR schema (OQ-4)
Helper owns the shape; the LLM fills values. Three parts:

**1. `variables[]` — one shared declaration block (also the co-reference anchor, D8).**
```
- name: response_ms   sort: Real   gloss: "delete response latency, ms"
- name: is_admin      sort: Bool   gloss: "acting user has admin role"
- name: order_state   sort: Enum   domain: [pending, paid, shipped]   gloss: "..."
```
Four sorts only: `Int | Real | Bool | Enum` (Enum requires `domain`). `gloss` is load-bearing — it's what the human reads to catch a bad translation (D4).

**2. `constraints[]` — one+ per AC, tagged with `ac_id` (so the unsat core points at real ACs).**
```
- ac_id: AC-3   kind: assertion    consequent: [response_ms < 100]
- ac_id: AC-8   kind: assertion    consequent: [response_ms > 200]
```
Atoms are **flat** — `{var, op, value}` (ops `< <= = != > >=`) or `{var, negated}` for Bool, `{var, =, enum_member}` for Enum. NO nested expressions, NO arithmetic-over-multiple-vars in v1 (that's `skipped_unsupported`). `kind: implication` adds an `antecedent[]` for EARS `IF…THEN` / `WHEN` variants; `kind: assertion` is the plain `shall` invariant.

**3. `coverage[]` — the honesty ledger.**
```
- ac_id: AC-3   status: formalized
- ac_id: AC-5   status: skipped_prose         reason: "'feels responsive' — no logic"
- ac_id: AC-9   status: skipped_unsupported   reason: "arithmetic over two vars"
```
Makes "the solver only proves over the formalized subset" structural, not a footnote. The report says *"checked N of M ACs; K unformalizable."*

### D7 — v1 scope: contradiction-only (OQ-6)
`unsat` + `unsat_core()` (labeled by `ac_id`) only. **Vacuity and gap/underspecification detection are DEFERRED** (later phases). Contradiction is the highest-value, lowest-false-positive-risk check.

### D8 — Co-reference handling (OQ-8)
The single `variables[]` block + `gloss` + a helper validation that every atom references a declared variable, all surfaced to the human (D4). **No second adversarial-LLM formalization-verifier in v1** (YAGNI; it doubles LLM cost) — flagged for v2.

### D9 — Conditional-permission clashes: pure-`Implies`, NO reachability injection (RECONCILED 2026-07-16 with the Phase-1 build)
**Corrects a post-ratification drift.** The original D9 prose said "a formalized EARS trigger is assumed reachable (its antecedent CAN be true)" — describing a reachability *injection* the Phase-1 build deliberately does NOT do. The decision record oversold the code (a `/spec-check` plan with an internal consistency-drift between its decision record and its build — the exact failure mode this command exists to catch). Rewritten to match the build:
- **What the solver actually does:** v1 `solve()` uses plain `z3.Implies` — NO reachability injection. A set of pure-implication ACs with opposing consequents on a shared trigger stays `sat` (each is satisfied by making its `IF` false). A permission/role clash is proven `unsat` **only when some AC actually asserts the reachable scenario** (an `assertion` constraint).
- **On D9's own motivating example** — "only admins can delete" (`can_delete ⇒ is_admin`) ∧ "non-admins can delete" — the clash is caught **iff** the second AC is formalized as the assertion `can_delete ∧ ¬is_admin`. If BOTH are formalized as pure implications, the solver correctly returns `sat` (no contradiction exists among rules alone — a rule set that merely *permits* is genuinely consistent until a permitted case is asserted).
- **Why not inject reachability:** auto-asserting every implication's antecedent as reachable produces spurious `unsat` on mutually-exclusive triggers — a cry-wolf false-positive machine, incompatible with the framework's precision stance (plan 19). Low-false-positive wins; the code is right, the old prose was wrong.
- **Recovery lever (formalization guidance, NOT solver logic):** `render-formalize-brief` + `references/formalization-guidance.md` (Phase 3/7) instruct the formalizer to formalize a permission-GRANT statement ("<role> can <action>") as an **assertion** of the reachable case, so the common clash IS caught with no solver-side hack. Best-effort (the LLM chooses the formalization) — not guaranteed.
- **Honest v1 boundary (feeds D11 + Phase-7 user copy — MANDATORY under-promise):** v1 is STRONG on numeric/state/enum invariants; on conditional-permission clashes it catches ONLY the case where the permitting scenario is asserted reachable. User-facing copy must NOT claim "permission/role logic" is caught in general — say "permission clashes where a permitting case is asserted." Phase 7 MUST NOT inherit the old D9 "assumed reachable" phrasing.

### D10 — Z3 dependency: presence-gate, require pip, exit clean (OQ-7)
- `z3-solver` (PyPI, MIT, ~30MB, prebuilt per-OS wheel with bundled native lib, no system package). Pin a floor (e.g. `z3-solver>=4.12`).
- **`install.sh` does NOT install z3** — the install stays stdlib-clean. The stdlib-only discipline protects the *always-on* substrate (pre-commit hooks, setup-chain helpers); `/spec-check` is opt-in, so its dependency burdens only users who invoke it.
- `/spec-check` preflight does `import z3`; if missing → clean message (`pip install z3-solver`, one-time) and exit. NO vendoring, NO forced install, NO partial "show IR without solving" fallback (the solver IS the value).
- `_spec_check/` ships as a normal command helper (like `_grill/`, `_audit/`) — normal install copy + launcher promotion. NOT a cross-cutting always-copy like `_design/` (only `/spec-check` uses it).

### D11 — Scope boundary (fold into user-facing copy — under-promise)
`/spec-check` compares ACs *against each other* — it catches self-contradiction in the requirement set. It does **NOT** catch a single coherent-but-wrong AC (asking for the opposite of what you meant, when nothing else contradicts it) — that is semantic/intent correctness, which no solver can judge. Intent-checking stays with the soft-LLM stages that already exist: `/research`'s rubric, `/grill`'s devils-advocate, and human approval gates. Every user-facing description says "consistency prover, not mind-reader."

### D12 — The formalization step uses a dedicated read-only `spec-formalizer` agent
The one LLM-in-the-loop step (`Task(formalize)`, the soft half of the neurosymbolic design) dispatches a **new dedicated `spec-formalizer` agent** with `subagent_type: spec-formalizer` — NOT an unnamed `general-purpose` dispatch.
- **Why dedicated:** (a) forge convention — every existing command `Task` dispatch names a roster agent (`/grill` → `devils-advocate`); (b) tool-scoping — the formalizer is a **read-only** translation step (`tools:` allowlist = `Read, Grep, Glob` — NO `Edit`/`Write`, so it physically cannot wander into editing the spec it is translating).
- **Roster/gate implications:** the new agent follows the plan-15 agent skeleton (`src/agents/spec-formalizer.md`, authored via `src/agents-AUTHORING.md`); it is reachable by construction (the `/spec-check` command dispatches it via a literal `subagent_type:` in `src/commands/**`, satisfying plan 41's `scripts/verify-agent-reachability.py` gate); roster grows 18 → 19.

---

## Post-ratification amendments (2026-07-16 — design critique)

Three issues surfaced in a design critique AFTER Phase-0 ratification, during Phases 1–6 build. Recorded here rather than silently; D9 above was rewritten in place (its old prose contradicted the shipped code — the ironic consistency-drift a `/spec-check` plan must not have).

### D13 — Verdict reproducibility: quorum formalization (the stochastic-formalizer hole)
**The gap:** Z3 is deterministic, but the English→IR formalization is ONE LLM call. Same `spec.md`, two runs → possibly different IR → possibly different `sat`/`unsat` → a verdict that flips CONSISTENT↔REVISE-SPEC between runs. For a tool whose entire credibility rests on "this is math, not opinion," verdict instability is a direct cry-wolf hit. The plan's "deterministically prove" + "stateless/idempotent" framing was **file-idempotent, not verdict-deterministic** — corrected (see the opening + D-note on the stateless line).
**v1 mitigation — quorum formalization (fits D4 + the `/audit --passes` precedent):** the command formalizes **k times** (default **k=2**; opt-in cost is acceptable — `/spec-check` is opt-in and this mirrors `/audit --passes`) and surfaces a contradiction as CONFIRMED **only if the same unsat-core (by `ac_id` set) reproduces across a majority of passes**. A non-reproducing one-off `unsat` is surfaced as UNSTABLE / low-confidence (NOT a REVISE-SPEC recommendation, NOT buried). The `ac_id`-based core is comparable across passes even when the IRs differ internally, so the quorum is well-defined.
- **Why not low-temperature instead:** a Claude Code `Task`-dispatched subagent's temperature is NOT orchestrator-controllable, so "low-temp formalization" is not a clean lever; quorum is the actionable one. (If temperature control ever appears, it composes with — does not replace — quorum.)
- **Build home = Phase 7** (the command-orchestration layer): a k-loop over the `render-formalize-brief → Task(spec-formalizer) → consume-ir → solve` sub-chain in `main.md` + ONE new CLI verb (`quorum-core` / `merge-passes`) taking k solve-results → the reproduced core + a stability flag. The Phase-6 CLI stays single-pass and is reused per pass (no rework). The report (D2/D4) gains a `formalization stability: core reproduced in j/k passes` line.

### D14 — Why opt-in ADVISORY, never a blocking gate (affirmed against an earlier "make it blocking" push)
`/spec-check` recommends; the human owns the verdict (D3). It MUST NEVER become a blocking/mandatory gate. **Principle: blocking belongs to DETERMINISTIC gates (the forcing-functions family — magic-enum, cross-layer-imports — no stochastic link); advisory belongs to the NEUROSYMBOLIC.** A blocking gate atop a stochastic formalizer turns every mistranslation into a hard-stop of a CORRECT specification — cry-wolf at maximum severity, structurally incompatible with D4 (human confirms the translation BEFORE a contradiction is treated real) and the DISMISS escape. This is precisely why `/spec-check` is NOT a forcing-function rule (Phase-0 grounding) and NOT inlined into mandatory `/specify` (D1). A future session must not "strengthen" it into a gate.

### OQ-9 — Deterministic `/specify` nudge toward `/spec-check` (future enhancement, NOT v1)
Opt-in means `/spec-check` catches contradictions only when the author already suspects them — and misses the ones in specs the author was confident about (where it is most needed). A cheap DETERMINISTIC signal in `/specify`'s output — "this spec has N conditional/numeric ACs over shared variables → consider `/spec-check`" — directs attention by a static-classification RULE (not the author's memory), mirroring the framework's seam-classification pattern, and pays no `solve` cost on every `/specify`. It recovers most of Kiro's always-on coverage without Kiro's always-on cost or its mandatory-gate cry-wolf. Deferred past v1; recorded so the coverage-vs-cost tradeoff is not lost.

---

## Honest scope

| Catches | Cannot touch |
|---|---|
| Numeric/threshold conflicts on a shared variable (`<100` ∧ `>200`) | Whether the requirement is what the user *meant* (semantic correctness) |
| Permission/role clashes **only when a permitting case is asserted reachable** (`can_delete ⇒ is_admin` ∧ an asserted `can_delete ∧ ¬is_admin`) — NOT pure rule-vs-rule (see D9) | Vague prose ACs ("feels responsive") — marked `skipped_prose` |
| State/enum clashes (`order_state = shipped` ∧ `order_state = pending`) | Anything the LLM didn't/couldn't formalize (`skipped_unsupported`) |
| Transitive inconsistency (A→B, B→C, C→¬A) over formalized atoms | Vacuity + gaps (deferred past v1) |

Strong for numeric/state/enum invariants; conditional-permission clashes only when the permitting case is asserted (D9 — do NOT claim "permission logic" generally); weak for prose-heavy product specs. Under-promise everywhere.

---

## Command structure (mirrors `/grill`)

- `src/commands/spec-check/main.md` — thin orchestrator.
- `src/commands/spec-check/references/` — report-format + formalization-guidance references.
- `src/devforge/lib/_spec_check/` — helper subpackage (the heavy Python).
- `src/devforge/lib/spec_check_helper{,.py}` — launcher (mirrors `grill_helper`/`audit_helper`).
- `src/agents/spec-formalizer.md` — new dedicated read-only formalization agent (D12; roster 18 → 19).
- Emitter `_PROMOTED += spec-check` (`scripts/emitters/claude.py`).

The LLM formalization reuses grill's round-trip **shape** — **helper-render → orchestrator-Task → helper-consume** (a Python helper cannot dispatch an LLM; the orchestrator mediates). It does NOT reuse grill's agent: the `Task` dispatches the dedicated read-only `spec-formalizer` (D12), not `devils-advocate`.

**Planned `_spec_check/` verbs** (settle exact set at build): `preflight` (setup-chain + z3 presence-gate + feature/spec resolution), `resolve-scope` (extract ACs from `spec.md`), `render-formalize-brief` (emit ACs + IR schema for the Task), `consume-ir` (parse + validate LLM IR: declared vars, atom-refs, coverage completeness), `solve` (deterministic Z3: build vars → assert `ac_id`-labeled constraints → `check()` → `unsat_core()`), `render-report` (write `spec-check.md`), `write-seed` (emit `spec-check-seed.json` on REVISE-SPEC match). **No state verb — `/spec-check` is stateless and FILE-idempotent** (mirrors `/summarize` D8: a re-run overwrites `spec-check.md`; it gates on the setup chain + the presence of `spec.md`, not a run-state file). **File-idempotent ≠ verdict-deterministic** — the formalization is a soft LLM step, so the VERDICT can differ run-to-run; D13's quorum pass is the mitigation, not statelessness.

---

## Build phases

**Phase 0 — Ratification.** ✅ DONE 2026-07-15 (this session). Decisions D1–D11 locked.

**Build-env precondition (applies from Phase 1 on):** the maintainer's build/dev/CI environment running `python-engineer`/`python-reviewer` tests must have `z3-solver` pip-installed locally — a one-time manual `pip install z3-solver`, distinct from the consumer-install question D10 settles (this repo tracks no `requirements.txt`/`pyproject.toml`, so there is nothing for it to ride on; `z3-solver` is the first third-party pip dep in the helper layer). Without it, Phase 1's test-first requirement hits `ModuleNotFoundError: z3` on the very first function.

**Phase 1 — IR schema + deterministic Z3 solver core.** ✅ **SHIPPED 2026-07-15** (working tree, not committed). `_spec_check/ir_schema.py` (D6 dataclasses `Variable`/`Atom`/`Constraint`/`Coverage`/`SpecCheckIR`, stdlib-only, mechanical `__post_init__` validation modeled on `_grill/seed_schema.py`) + `_spec_check/_solve.py` (`solve(SpecCheckIR) -> SolveResult`: builds sorts/vars, asserts `ac_id`-labeled constraints via `assert_and_track`, `check()`, maps `unsat_core()` → deduped-sorted `ac_id` list). Pure — no LLM, no command. Built `python-engineer → python-reviewer`, test-first; **117 tests green** (`python3 -m unittest tests.lib._spec_check.test_ir_schema tests.lib._spec_check.test_solve`).
- **Two design facts locked at build (cite before Phase 2/3):** (1) **D9 reachability is NOT auto-injected** — `solve()` uses plain `z3.Implies` semantics; a pure-implication-only opposing-consequent set stays `sat`, a permission/role clash is `unsat` ONLY when an `assertion` constraint asserts the reachable scenario. The "assumed-reachable / surface-to-human" honesty note is a Phase-3 report-layer concern, NOT solver logic. (2) The **`SpecCheckIR` schema does NO cross-record validation** (atoms-reference-declared-vars, coverage-covers-every-AC) — that is Phase 2's `_consume.py`; the ONLY var/atom cross-check lives in `_solve`'s build step (which raises `ValueError` on undeclared-var / wrong-op-for-sort / enum-member-not-in-domain / Int-given-float).
- **Build note (z3 global-context bug fixed):** `z3.EnumSort(name, ...)` on the default context raises `enumeration sort name is already declared` on a 2nd `solve()` reusing an Enum var name in one process. Fixed by threading a fresh `z3.Context()` through every leaf z3 constructor in `solve()` (`Const` derives ctx from its context-bound `enum_sort` arg — it takes no `ctx=`).
- **Env precondition satisfied:** `z3-solver` 4.16 installed for the test-runner python (`/usr/bin/python3`, 3.9) into the user site-packages (`~/Library/Python/3.9`); tests run via `python3 -m unittest`.
- **Verify (met):** hand-authored IR fixtures assert `sat` on a consistent set, `unsat` + exact `{AC-3, AC-8}` core on a numeric clash, a role clash (implication + asserting AC, D9) + a pure-implications `sat` control, an enum clash, all 6 numeric ops + `Real` sort end-to-end, build-time raise paths, and an `ac_id`-contains-`!` delimiter regression. Every function tested the same turn.
- **Carry-forward for Phase 4:** the reviewer's HIGH finding (absolute `from src.devforge.lib...` import fails in the installed layout — no `src/` tree) leaves exactly ONE remaining outlier: `tests/lib/_grill/test_seed_schema.py`. Phase 4 relocates `seed_schema.py` → `_shared/`; **retarget that test file to the house `sys.path.insert(_LIB_DIR)` + bare `from _shared.seed_schema import` pattern during the move** (don't propagate the outlier).

**Phase 2 — AC extraction + IR validation.** ✅ **SHIPPED 2026-07-15** (working tree, not committed). `_spec_check/_consume.py`: `extract_acs` (entry point), `parse_ir` (raw IR JSON — dict or str — → the Phase-1 dataclasses; two D6 atom shapes: generic `{var,op,value}` + Bool short-form `{var,negated}`→`Atom(var,"=",not negated)`; dataclass `ValueError` re-raised as `IRParseError` with an AC-labeled element locator), `validate_ir(ir, ac_ids) -> List[str]` (collect-all, sorted+deduped cross-record checks the schema does NOT do: duplicate var names, undeclared-var refs, atom value/sort consistency mirroring `_solve`'s build raises, coverage completeness, formalized⇔has-constraint / skipped⇔no-constraint agreement) + `validate_ir_or_raise`. Two exception types: `IRParseError` (malformed IR → command re-prompts) vs `IRValidationError` (IR parses but is logically inconsistent → surface to human). Built `python-engineer → python-reviewer` (5 findings: 0 high, all fixed); `_spec_check` 165 tests green.
- **AC-parser decision (RESOLVED — supersedes the plan's "pick one of two" instruction):** chose `parse_acs` (richer — returns `{id,text,checked,subsection}`, path-or-text, real EARS format) over `breakdown_helper._parse_acs`. But reuse-by-import would couple `_spec_check → _verify` and BREAK a `--only spec-check` surgical install (which copies `_spec_check`+`_shared` but NOT `_verify`). So **`parse_acs` + its 4 regexes were RELOCATED to `src/devforge/lib/_shared/spec_acs.py`** (the always-copied package — mirrors plan 20/22 Phase 0 + this plan's own D5 seed-schema move), with a back-compat re-export shim `from _shared.spec_acs import parse_acs` left in `_verify/_ac.py` (keeps `_verify/_cli.py:262` + existing `_verify` tests byte-behavioral — 544 regression unchanged; `merge_ac_results`+`_parse_results_table` stayed in `_verify/_ac.py`). Maintainer-approved 2026-07-15. **Phase 6's `resolve-scope` verb imports `parse_acs` from `_shared.spec_acs` (NOT `_verify`).** New tests at `tests/lib/_shared/test_spec_acs.py` (30).
- **Verify (met):** round-trip via the REAL fixture `tests/lib/fixtures/specify-sample-migration.md` (7 ACs, EARS `WHEN`/`IF…THEN` variants) — `extract_acs` returns AC-1..AC-7; a valid IR over those 7 ids validates clean; invalid IRs reject with precise collected errors (undeclared var, missing coverage entry, unknown-AC coverage, skipped-AC-with-constraint, enum-member-not-in-domain, Int-given-float, dup var name, formalized-with-no-constraint). Every function + every validate/parse branch tested.

**Phase 3 — Formalization brief + report renderer.** ✅ **SHIPPED 2026-07-15** (working tree, not committed). `_spec_check/_brief.py` `render_formalize_brief(acs) -> str` (emits the numbered AC list + the machine OUTPUT-CONTRACT block — top-level `variables`/`constraints`/`coverage` keys, 4 sorts, 2 atom shapes, 3 coverage statuses; deeper worked examples deferred to Phase 7 `references/formalization-guidance.md`, injected by the command, NOT duplicated in the brief) + `_spec_check/_report.py` (`SPEC_CHECK_DISPOSITIONS = ("CONSISTENT","REVISE-SPEC","DISMISS")`; `recommend_disposition(solve_result)` unsat→REVISE-SPEC / sat|unknown→CONSISTENT, never DISMISS; `_atom_to_str`/`_constraint_to_str` readable renderers; `render_report(...)`; `write_spec_check_report(feature_dir, content)` atomic temp+os.replace, mirrors `write_grill_report`). Built `python-engineer → python-reviewer` (4 findings: 0 high, all fixed — incl. coverage N/K scoped to `acs` so the ledger can't print "Checked 2 of 1"); `_spec_check` 215 tests green.
- **`render_report` SIGNATURE (Phase 6 CLI must supply these):** `render_report(feature, date_str, solve_result, ir, acs, recommended_disposition)` — `feature`+`date_str` FIRST, matching the `_grill`/`_review`/`_verify` `render_report` house precedent (renders `# Spec-Check: <feature>` + `**Feature**` + `**Date**` header, then the D11 scope blockquote). Phase 6's launcher supplies `feature` (from preflight resolution) + `date_str` (`datetime`).
- **Report sections (verified):** D11 scope blockquote (verbatim, all branches) → `## Recommendation` (disposition + reason; honest "No formalizable logic found — nothing was proven" when all-skipped; `unknown` caveat line) → `## How your ACs were read as logic` (D4 SOFT layer — variable glosses + original-text↔logic-reading juxtaposition; the human checks THIS) → `## Contradiction` (D4 HARD layer, ONLY on `unsat`, names exactly the `unsat_core` ids) → `## Coverage` (D6 ledger "Checked N of M … (K unformalizable)"). D9 reachability note rendered only when the IR has ≥1 `implication`.
- **Producer↔consumer contract confirmed CLEAN at review:** `_brief.py`'s emitted OUTPUT-CONTRACT (var/atom/constraint/coverage key names + shapes) matches exactly what Phase-2 `_consume.py` `parse_ir`/`validate_ir` accepts (the brief deliberately narrows Bool atoms to the `{var,negated}` short-form; `_consume` also accepting the generic `{var,op:"=",value:<bool>}` is defense-in-depth).
- **Verify (met):** solved-IR fixtures render both layers, name the conflicting ACs, list the coverage ledger, state "checked N of M," carry the D11 line; sat/unknown/nothing-formalized/implication-present/invalid-disposition branches all covered; atomic write idempotent.

**Phase 4 — Seed schema (to `_shared/`, multi-source) + preflight + seed writer.** ✅ **SHIPPED 2026-07-15** (working tree, not committed). (a) `seed_schema.py` RELOCATED `_grill/` → `src/devforge/lib/_shared/seed_schema.py`; `SEED_SOURCE="grill"` → `SEED_SOURCES=("grill","spec-check")` tuple; `__post_init__` equality → `_require_in_enum(source, SEED_SOURCES, ...)` membership (reuses the existing helper). Re-pointed the ONLY source importer `_grill/_report.py:71` → `_shared.seed_schema`; `build_seed` now passes literal `source="grill"` (grill byte-behaviorally identical). Fixed a stale `_grill/seed_schema.py` path citation in `src/commands/grill/references/report-format.md` (grep-caught). The outlier test moved `tests/lib/_grill/test_seed_schema.py` → `tests/lib/_shared/test_seed_schema.py`, retargeted to the house `sys.path` header (closes the Phase-1 carry-forward — repo now has ZERO `from src.devforge.lib` test imports). (b) `_spec_check/_preflight.py`: `check_z3(importer=None) -> (bool, str)` (injectable importer seam — default does a real `import z3`; absent → `Z3_INSTALL_MESSAGE`) + `preflight(workspace_root=None, feature_dir=None, z3_importer=None) -> dict` gating on constitution-populated + setup-chain + **`spec.md` ONLY (NOT `plan.md`** — runs before `/plan`) + `z3_available`/`z3_message` keys. (c) `_spec_check/_seed.py`: `build_seed(...)` (`source="spec-check"` + `target_stage="spec"` HARDCODED, not caller-overridable) + `write_seed(feature_dir, seed)` → `spec-check-seed.json` (mkstemp+`os.replace`, pattern-identical to `_grill` `write_seed`). No state module — stateless/idempotent (mirrors `/summarize` D8). Built `python-engineer → python-reviewer` (1 finding, LOW docstring, fixed); reviewer independently byte-diffed the seed relocation, the sentinel/artefact constants (byte-identical), and the `asdict` round-trip. `_spec_check` 267 + `_shared` seed 52 + `_grill` 345 regression green.
- **Verdict-gating is Phase-7 command-side** (D5/plan-39): `write_seed` writes unconditionally what it's given; the command calls it ONLY in the REVISE-SPEC-matching arm. Its docstring says so (no false "gating here" claim).
- **Note — 3-way constant duplication:** `_UNPOPULATED_SENTINELS`/`_SETUP_CHAIN_ARTEFACTS` are now duplicated across `_audit`/`_grill`/`_spec_check` (byte-faithful copies, verified). Deliberate scope-containment; a future `_shared`-lift could DRY it (out of this plan's scope).
- **Verify (met):** `_grill` suite green post-relocation (byte-behavioral); preflight reports the install message on forced-ImportError, passes when z3 present, and never requires `plan.md`; `build_seed` emits a valid `source="spec-check"` `ReEntrySeed`; `write_seed` round-trips JSON → `ReEntrySeed`.

**Phase 5 — `/specify` re-entry consumer generalization (the D5 consumer wiring).** ✅ **SHIPPED 2026-07-15** (working tree, not committed). **Bigger than D5's "≈0 lines" claim** — D5 was right that the FILTER logic (`target_stage=="spec"`, source-agnostic) needed no change, but the Phase-0.5 block's NARRATION was grill-specific across ~5 sentences, so widening the glob alone would have mislabeled a `spec-check` seed as "re-entering from a `/grill` RE-ENTER-UPSTREAM verdict." Generalized the whole block (`src/commands/specify/main.md` §Phase 0.5) source-aware: both globs `specs/*/grill-seed.json` → `specs/*/*-seed.json`; heading → "Re-entry from `/grill` or `/spec-check`"; added a `source` field bullet; narration now reads `source` and narrates grill (RE-ENTER-UPSTREAM / plan design) vs spec-check (REVISE-SPEC / AC logic); **added a multi-match branch** (the widened glob can match BOTH `grill-seed.json` + `spec-check-seed.json` in one feature dir given the v1 no-delete rule → process all, union `carried_findings`, name still-pending); corrected an inverted upstream/downstream direction; de-asserted the seed-lifecycle sentence (no longer claims `/spec-check`'s unbuilt cycle_count mechanism). Built `instruction-author → instruction-reviewer` (5 findings: 0 high, all fixed). **`claude-code-guide` N/A** — the edit touched only orchestrator-facing prose (glob patterns, field-reads, narration), ZERO Claude Code integration surface (no frontmatter / `tools` / `permissions` / MCP / hooks); invoking it would be cargo-cult verification.
- **Verify (met):** the block reads coherently for BOTH sources; `grill-seed.json` still consumed byte-behaviorally (grill's story unchanged); a `spec-check-seed.json` `target_stage="spec"` is now matched + narrated correctly. The other three seed consumers (`/research`/`/discover`/`/plan`) are untouched — spec-check's `target_stage` is always `"spec"`, which they never match.
- **Phase-8 carry-forward:** `src/CLAUDE.md`'s command catalog + Workflow chain still describe the re-entry seed as grill-only (`grill-seed.json` in the `/plan` + `/grill` entries) with no `/spec-check` entry — flagged by both instruction agents. Phase 8 adds the `/spec-check` catalog entry AND generalizes those seed references.

**Phase 6 — CLI launcher (emitter registration MOVED to Phase 7).** ✅ **SHIPPED 2026-07-15/16** (working tree, not committed). `_spec_check/_cli.py` verb registry (7 verbs: `preflight`, `resolve-scope`, `render-formalize-brief`, `consume-ir`, `solve`, `render-report`, `write-seed`; scratch-chain I/O — each verb reads `--*-file` inputs + emits JSON/text to stdout, exit 2 on gate failure / 3 on IR-inconsistent-with-ACs) + `spec_check_helper{,.py}` launcher (POSIX + Python shims, byte-identical to `grill_helper` modulo names). **PACKAGE RENAMED `_smt` → `_spec_check`** (maintainer-approved 2026-07-15) so it matches the `spec-check` command name and `install.sh --only spec-check` resolves it — `_smt` was the only command package not matching its command; the plan's own "ships like `_grill`/`_audit`" analogy required the match. Built `python-engineer → python-reviewer` (5 findings: 0 high; F1 dead-code/validation, F2 `solve` ValueError→exit-2, F3 acs-element-type guard, all fixed); `_spec_check` 323 tests green; the IR serde round-trip `parse_ir(dataclasses.asdict(ir)) == ir` verified exact across all shapes (the load-bearing chain invariant).
- **Emitter `_PROMOTED += spec-check` DEFERRED to Phase 7** — the emitter silently `continue`s on a `_PROMOTED` name whose `src/commands/spec-check/` folder doesn't exist yet (Phase 7's `main.md`), so registering it before Phase 7 is a no-op AND the install-ride verify ("`spec-check command: yes`") is unachievable until `main.md` lands. The full-install `cp -R src/devforge/.` already ships `_spec_check/` + `spec_check_helper` today (inert until dispatched). Moved to Phase 7.

**Phase 7 — Emitter registration + quorum (D13) + the `spec-formalizer` agent + command spec.** (a) `scripts/emitters/claude.py` `_PROMOTED += spec-check` (moved from Phase 6). (b) **D13 quorum — ✅ SHIPPED 2026-07-16:** `_spec_check/_quorum.py` (`analyze_quorum(solve_results, k)` — strict-majority `ac_id`-core reproduction → verdict `confirmed_unsat`/`unstable`/`consistent` + `confirmed_core` + `stability{reproduced_in,of}` + `declared_k` visibility + `all_cores` D4 transparency; `synthesize_solve_result` — the load-bearing cry-wolf rule `unstable→sat`, NOT REVISE-SPEC) + the `quorum-core` CLI verb (`--passes-file`/`--k`, non-fatal stderr warning on a `k`/len mismatch so a dropped pass can't masquerade as a complete quorum) + a back-compat-safe `render_report(..., stability=None)` extension (`stability` line or `unstable` caveat in `## Recommendation`; `None` → byte-identical, pinned by a full-string-equality test) + `--stability-file`. Built `python-engineer → python-reviewer` (2 findings: 0 high — the k-mismatch visibility + a flat-shape test gap, both fixed); `_spec_check` **369 tests** green. (c) `src/agents/spec-formalizer.md` — new read-only agent per the plan-15 skeleton (`tools:` = `Read, Grep, Glob`; NO `Edit`/`Write`), per D12. (d) `src/commands/spec-check/main.md` + `references/` (incl. `formalization-guidance.md` with the D9 permission-grant→assertion guidance). Wires: preflight → resolve-scope → **k× [render-formalize-brief → `Task(subagent_type: spec-formalizer)` → consume-ir → solve]** (D13, default k=2) → quorum-core → render-report → human gate (AskUserQuestion, D3 disposition) → write-seed. `disable-model-invocation: true`. `instruction-author → instruction-reviewer` + `claude-code-guide`.
- **Verify:** install ride — `spec-check command: yes`, 0 `{{` leaks, executable installed `spec_check_helper`, every verb dispatches (`--help`); instruction-reviewer clean; every sentence verifiable-now / mechanically-true / explicit-forward-ref; the human-gate surfaces the formalization (D4); **every user-facing string (command `description`, report header, catalog entry) states the D11 scope boundary AND the D9 under-promise (NO "permission/role logic" general claim; permission clashes only when a permitting case is asserted) AND does NOT bare-claim "deterministic proof of your spec" (D13 — quorum-stable framing)**; `scripts/verify-agent-reachability.py` passes (the new agent is reached by the `/spec-check` literal `subagent_type:`).

**Phase 8 — Docs reconcile.** `src/CLAUDE.md` command catalog + Workflow chain (opt-in, spec-tier, beside `/grill`) + Command Details entry + Available-Agents list (roster 18 → 19) + `CHANGELOG.md` + this plan's entry in the repo-root `CLAUDE.md` active-work list + `src/devforge/storage-rules.md` if the seed/artifact needs a row. Cross-ref sweep.
- **Verify:** grep sweep — no dangling refs; the catalog line carries a purpose one-liner + the opt-in/spec-tier annotation + the D11 scope boundary (catalog is load-bearing — `disable-model-invocation:true` means the description isn't in model context).

**Phase 9 — testForge20 / consumer e2e (user-driven HARD GATE).** Run `/spec-check` on a real feature with a deliberately contradictory AC pair; confirm the unsat core names the right ACs, the human-check surfaces the formalization, DISMISS proceeds, REVISE-SPEC emits the seed, and a consistent spec returns CONSISTENT. Also confirm the z3-absent path shows the clean install message.

---

## Non-goals

- NOT semantic/intent correctness ("is this the right feature") — logic consistency only (D11).
- NOT vacuity or gap detection in v1 (D7).
- NOT arithmetic-over-multiple-variables in v1 (D6 — `skipped_unsupported`).
- NOT a second adversarial-LLM formalization verifier in v1 (D8 — v2).
- NOT matching Kiro feature-for-feature (no PBT/fuzz layer).
- NOT forcing z3 on every consumer install (D10).

---

## Provenance / supporting material from the origin session

- Comparison artifact: `https://claude.ai/code/artifact/0aaaca15-bdc8-4a5a-b9f8-6ca2819708e5` — "AIDevTeamForge vs AWS Kiro — Quality & Stability Dossier."
- Verified Kiro sources (survived 3-vote adversarial verification):
  - `https://kiro.dev/blog/deep-spec-analysis/` (Refinement → Auto-Formalization → Logical Analysis)
  - `https://kiro.dev/docs/specs/analyze-requirements`
  - `https://www.geekwire.com/2026/aws-targets-ai-slop-with-new-spec-check-in-kiro-coding-tool-amid-scrutiny-of-agent-reliability/`
  - `https://theoutpost.ai/news-story/aws-kiro-tackles-ai-agent-reliability-with-math-based-bug-detection-before-code-is-written-26215/`
  - `https://kiro.dev/docs/specs/correctness/` (Kiro's PBT layer — out of scope here, context only)
- AWS data point: ~60% of first-draft requirements across 35 projects / 1,400+ ACs needed refinement after their spec-check — evidence requirement-logic defects are common and worth checking.
- Caveat carried from the research: **no head-to-head output-quality benchmark between Forge and Kiro exists.** Motivated by an architectural gap, not a measured deficiency.

---

## Phase-0 grounding (verified this session, cite before building)

- ACs are **EARS-notation** checkbox bullets (`- [ ] **AC-N**: <statement>`), 5 variants with regexes in `src/devforge/lib/_specify/_schema.py` (`EARS_VARIANT_ENUM`/`EARS_REGEX`), rendered by `_specify/_render.py:21-50` under §5's 7 fixed subsections; stored typed in the handoff as `SpecSeeds.acceptance_criteria: List[AcceptanceCriterion]` (`_specify/handoff_schema.py:130-165,332-378`) with an `ears_variant` field.
- AC parsers already exist downstream. Two return per-AC statement TEXT (viable for formalization) — `_verify/_ac.py parse_acs` (regex `_AC_LINE_RE`, `_ac.py:101`) and `breakdown_helper._parse_acs` (`breakdown_helper.py:722`, returns `[(ac_number, text)]`); Phase 2 picks one. `plan_helper._count_acs` (`plan_helper.py:225`) returns COUNTS only (no text) — not a candidate.
- Forcing-function family is **pure-static, no-LLM, no-subprocess** (`_constitute/_forcing_functions/`) — which is *why* `/spec-check` is NOT a forcing-function rule (it needs an LLM; the family contract is deterministic-only, runs in pre-commit where no LLM exists).
- `/grill` precedent for the helper-render→orchestrator-Task→helper-consume round-trip, the opt-in stance (`disable-model-invocation: true`), the disposition + human-gate + seed-write flow, and the `_shared/` engine — `src/commands/grill/main.md` + `src/devforge/lib/_grill/`.
- `ReEntrySeed` single-source gate + `/specify` Phase 0.5 source-agnostic consumer verified: `_grill/seed_schema.py:50,52,126`; `specify/main.md:123-137` (globs `specs/*/grill-seed.json`, filters `target_stage=="spec"`, ignores `source`, parses raw JSON inline).

**Do NOT trust any code/path claim without re-verifying at build** (framework sentence-level-hallucination discipline). Build behind the standard loops: `python-engineer → python-reviewer` (test-first) for helpers; `instruction-author → instruction-reviewer` + `claude-code-guide` for `main.md`/spec edits shipping into `.claude/`.
