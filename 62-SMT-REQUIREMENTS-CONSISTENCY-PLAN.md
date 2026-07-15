# 62 — `/spec-check`: SMT Requirements-Consistency Command

**Status:** RATIFIED (Phase 0 complete 2026-07-15) / build phases NOT started / no code yet.
**Branch:** `develop-2.0-init`
**Origin:** Surfaced 2026-07-15 during a Forge-vs-AWS-Kiro capability-gap research session. The one capability where Kiro's architecture is genuinely ahead of Forge, and it fits Forge's own "every gate is mechanical, not prose" philosophy. Phase-0 brainstorm + maintainer ratification completed this session.

---

## What this is

A new **standalone, opt-in `/spec-check` command** that reads a completed feature spec's acceptance criteria (ACs), uses an LLM to translate each AC into formal logic, and runs the **Z3 SMT solver** to *deterministically prove* whether the AC set is self-consistent. When two+ ACs cannot all hold, the solver returns the exact conflicting subset. It is the **first requirement-tier consistency check** in the framework.

Neurosymbolic — two parts, one soft, one hard:
1. **Auto-formalization (soft, LLM):** each AC → a typed constraint IR (helper owns the IR schema; the LLM fills values). E.g. "response < 100ms" → `response_ms < 100`.
2. **Logical analysis (hard, Z3):** the conjunction of formalized constraints is checked. `unsat` → contradiction; `unsat_core()` → the minimal conflicting AC set.

**Sound only over the subset the LLM formalized** — it proves the *formalized logic* is consistent, NOT the whole natural-language spec, and NOT semantic correctness. Do not frame it as "proves the spec is correct."

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
- **Schema RELOCATED to `_shared/`, not edited in place:** move `seed_schema.py` (and `ReEntrySeed`) from `src/devforge/lib/_grill/seed_schema.py` → `src/devforge/lib/_shared/seed_schema.py`, and re-point `_grill`'s imports at `_shared` (byte-behaviorally identical; `_grill`'s test suite is the regression net). This mirrors exactly how plan 20 Phase 0 / plan 22 Phase 0 extracted the refutation engine + feature-scope resolver into `_shared/` so no command depends on another command's package. Without this, `_smt/` would import `_grill/` internals — breaking the independence the `_shared/` pattern guarantees and contradicting D10's "normal command helper" claim. `_smt/` and `_grill/` both import the seed schema from `_shared/` (which already ships as a cross-cutting always-copy — `/audit`/`/review`/`/grill`/`/verify` depend on it).
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

### D9 — Reachability assumption for implications (the deep formalization risk)
Pure-implication ACs rarely contradict alone — the solver satisfies them by making the `IF` false. "Only admins can delete" ∧ "non-admins can delete" only clashes once the non-admin-delete situation is asserted reachable. **v1 rule: a formalized EARS trigger is assumed reachable** (its antecedent CAN be true), and that assumption is surfaced to the human. v1 is strong on numeric/state invariants, careful on conditional-permission clashes — stated honestly, not over-claimed.

### D10 — Z3 dependency: presence-gate, require pip, exit clean (OQ-7)
- `z3-solver` (PyPI, MIT, ~30MB, prebuilt per-OS wheel with bundled native lib, no system package). Pin a floor (e.g. `z3-solver>=4.12`).
- **`install.sh` does NOT install z3** — the install stays stdlib-clean. The stdlib-only discipline protects the *always-on* substrate (pre-commit hooks, setup-chain helpers); `/spec-check` is opt-in, so its dependency burdens only users who invoke it.
- `/spec-check` preflight does `import z3`; if missing → clean message (`pip install z3-solver`, one-time) and exit. NO vendoring, NO forced install, NO partial "show IR without solving" fallback (the solver IS the value).
- `_smt/` ships as a normal command helper (like `_grill/`, `_audit/`) — normal install copy + launcher promotion. NOT a cross-cutting always-copy like `_design/` (only `/spec-check` uses it).

### D11 — Scope boundary (fold into user-facing copy — under-promise)
`/spec-check` compares ACs *against each other* — it catches self-contradiction in the requirement set. It does **NOT** catch a single coherent-but-wrong AC (asking for the opposite of what you meant, when nothing else contradicts it) — that is semantic/intent correctness, which no solver can judge. Intent-checking stays with the soft-LLM stages that already exist: `/research`'s rubric, `/grill`'s devils-advocate, and human approval gates. Every user-facing description says "consistency prover, not mind-reader."

### D12 — The formalization step uses a dedicated read-only `spec-formalizer` agent
The one LLM-in-the-loop step (`Task(formalize)`, the soft half of the neurosymbolic design) dispatches a **new dedicated `spec-formalizer` agent** with `subagent_type: spec-formalizer` — NOT an unnamed `general-purpose` dispatch.
- **Why dedicated:** (a) forge convention — every existing command `Task` dispatch names a roster agent (`/grill` → `devils-advocate`); (b) tool-scoping — the formalizer is a **read-only** translation step (`tools:` allowlist = `Read, Grep, Glob` — NO `Edit`/`Write`, so it physically cannot wander into editing the spec it is translating).
- **Roster/gate implications:** the new agent follows the plan-15 agent skeleton (`src/agents/spec-formalizer.md`, authored via `src/agents-AUTHORING.md`); it is reachable by construction (the `/spec-check` command dispatches it via a literal `subagent_type:` in `src/commands/**`, satisfying plan 41's `scripts/verify-agent-reachability.py` gate); roster grows 18 → 19.

---

## Honest scope

| Catches | Cannot touch |
|---|---|
| Numeric/threshold conflicts on a shared variable (`<100` ∧ `>200`) | Whether the requirement is what the user *meant* (semantic correctness) |
| Permission/role logic (`can_delete ⇒ is_admin` ∧ a permitted non-admin delete) | Vague prose ACs ("feels responsive") — marked `skipped_prose` |
| State/enum clashes (`order_state = shipped` ∧ `order_state = pending`) | Anything the LLM didn't/couldn't formalize (`skipped_unsupported`) |
| Transitive inconsistency (A→B, B→C, C→¬A) over formalized atoms | Vacuity + gaps (deferred past v1) |

Strong for numeric/state/permission logic; weak for prose-heavy product specs. Under-promise everywhere.

---

## Command structure (mirrors `/grill`)

- `src/commands/spec-check/main.md` — thin orchestrator.
- `src/commands/spec-check/references/` — report-format + formalization-guidance references.
- `src/devforge/lib/_smt/` — helper subpackage (the heavy Python).
- `src/devforge/lib/spec_check_helper{,.py}` — launcher (mirrors `grill_helper`/`audit_helper`).
- `src/agents/spec-formalizer.md` — new dedicated read-only formalization agent (D12; roster 18 → 19).
- Emitter `_PROMOTED += spec-check` (`scripts/emitters/claude.py`).

The LLM formalization reuses grill's round-trip **shape** — **helper-render → orchestrator-Task → helper-consume** (a Python helper cannot dispatch an LLM; the orchestrator mediates). It does NOT reuse grill's agent: the `Task` dispatches the dedicated read-only `spec-formalizer` (D12), not `devils-advocate`.

**Planned `_smt/` verbs** (settle exact set at build): `preflight` (setup-chain + z3 presence-gate + feature/spec resolution), `resolve-scope` (extract ACs from `spec.md`), `render-formalize-brief` (emit ACs + IR schema for the Task), `consume-ir` (parse + validate LLM IR: declared vars, atom-refs, coverage completeness), `solve` (deterministic Z3: build vars → assert `ac_id`-labeled constraints → `check()` → `unsat_core()`), `render-report` (write `spec-check.md`), `write-seed` (emit `spec-check-seed.json` on REVISE-SPEC match). **No state verb — `/spec-check` is stateless and idempotent** (mirrors `/summarize` D8: a re-run overwrites `spec-check.md`; it gates on the setup chain + the presence of `spec.md`, not a run-state file).

---

## Build phases

**Phase 0 — Ratification.** ✅ DONE 2026-07-15 (this session). Decisions D1–D11 locked.

**Build-env precondition (applies from Phase 1 on):** the maintainer's build/dev/CI environment running `python-engineer`/`python-reviewer` tests must have `z3-solver` pip-installed locally — a one-time manual `pip install z3-solver`, distinct from the consumer-install question D10 settles (this repo tracks no `requirements.txt`/`pyproject.toml`, so there is nothing for it to ride on; `z3-solver` is the first third-party pip dep in the helper layer). Without it, Phase 1's test-first requirement hits `ModuleNotFoundError: z3` on the very first function.

**Phase 1 — IR schema + deterministic Z3 solver core.** `_smt/ir_schema.py` (the D6 dataclasses) + `_smt/_solve.py` (build sorts/vars, assert `ac_id`-labeled constraints, `check()`, extract `unsat_core()` → `ac_id` list). Pure — no LLM, no command. Build + test FIRST in isolation. `python-engineer → python-reviewer`, test-first.
- **Verify:** hand-authored IR fixtures → assert `sat` on a consistent set, `unsat` + the exact `{AC-3, AC-8}` core on a numeric clash, a role clash (with D9 reachability), and an enum clash. Every function has a test run the same turn.

**Phase 2 — AC extraction + IR validation.** `_smt/_consume.py`: parse `spec.md` ACs and validate LLM-produced IR (every atom references a declared var; coverage covers every AC; sorts/domains well-formed). For the AC parser, reuse ONE of the two functions that return per-AC statement text — `_verify/_ac.py parse_acs` (`_ac.py:101`) or `breakdown_helper._parse_acs` (`breakdown_helper.py:722`, returns `[(ac_number, text)]`); **`plan_helper._count_acs` is NOT a candidate — it returns counts only, no AC text.** Pick one and cite it at build. `python-engineer → python-reviewer`.
- **Verify:** round-trip via a REAL `/specify` `spec.md` fixture (e.g. `tests/lib/fixtures/specify-sample-migration.md`) — extract its ACs, feed a valid + an invalid IR, assert the validator accepts/rejects with precise errors (undeclared var, missing coverage entry).

**Phase 3 — Formalization brief + report renderer.** `_smt/_brief.py` (`render-formalize-brief` — emits the ACs + the IR schema instructions for the Task) + `_smt/_report.py` (`render-report` — writes `spec-check.md`: the two-layer formalization surface (D4), coverage ledger, unsat-core headline, recommended disposition, and the D11 "consistency prover, not mind-reader" scope-boundary line). `python-engineer → python-reviewer`.
- **Verify:** given a solved-IR fixture, the rendered `spec-check.md` shows both layers, names the conflicting ACs, lists the coverage ledger, states "checked N of M," and carries the D11 scope-boundary line.

**Phase 4 — Seed schema (to `_shared/`, multi-source) + preflight + seed writer.** (a) Relocate `seed_schema.py` → `src/devforge/lib/_shared/seed_schema.py`, make `SEED_SOURCE` a source enum `("grill","spec-check")` (relax `__post_init__` equality → membership), and re-point `_grill`'s imports at `_shared` (per D5). (b) `_smt/_preflight.py` (setup-chain gate + `import z3` presence-gate with the D10 clean message + feature/`spec.md` resolution). (c) `_smt/_seed.py` (`write-seed` → `spec-check-seed.json`, importing `ReEntrySeed` from `_shared`, verdict-gated per D5/plan-39). No state module — stateless/idempotent, see Command Structure above; mirrors `/summarize` D8. `python-engineer → python-reviewer`.
- **Verify:** `_grill`'s `tests/lib/_grill/` suite stays green after the relocation (byte-behavioral). Preflight exits clean with the install message when z3 is absent (simulate ImportError); passes when present. `write-seed` emits a valid `source="spec-check"` `ReEntrySeed` only on REVISE-SPEC, nothing on DISMISS/CONSISTENT.

**Phase 5 — `/specify` glob widen (the D5 consumer wiring).** `/specify` `main.md:125`: widen the Phase 0.5 glob `specs/*/grill-seed.json` → `specs/*/*-seed.json` (the consumer already filters `target_stage == "spec"` and ignores `source`, so this is the only change). `instruction-author → instruction-reviewer` + `claude-code-guide` (ships into `.claude/`).
- **Verify:** `/specify` still consumes `grill-seed.json` byte-behaviorally; a `spec-check-seed.json` with `target_stage="spec"` is now also matched by `/specify`'s glob. Confirm the other three seed consumers (`/research`/`/discover`/`/plan`) are untouched (they never match a spec-targeted seed).

**Phase 6 — CLI launcher + emitter.** `_smt/_cli.py` verb registry + `spec_check_helper{,.py}` launcher + `scripts/emitters/claude.py` `_PROMOTED += spec-check`. `python-engineer → python-reviewer`.
- **Verify:** install ride — `spec-check command: yes`, 0 `{{` leaks, executable installed `spec_check_helper`, every verb dispatches (`--help`).

**Phase 7 — The `spec-formalizer` agent + command spec.** (a) `src/agents/spec-formalizer.md` — new read-only agent per the plan-15 skeleton (`tools:` = `Read, Grep, Glob`; NO `Edit`/`Write`), per D12. (b) `src/commands/spec-check/main.md` + `references/`. Wires: preflight → resolve-scope → render-formalize-brief → **`Task(subagent_type: spec-formalizer)`** → consume-ir → solve → render-report → human gate (AskUserQuestion, D3 disposition) → write-seed. `disable-model-invocation: true`. `instruction-author → instruction-reviewer` + `claude-code-guide`.
- **Verify:** instruction-reviewer clean; every sentence verifiable-now / mechanically-true / explicit-forward-ref; the human-gate surfaces the formalization (D4); every user-facing string (command `description`, report header, catalog entry) states the D11 scope boundary; `scripts/verify-agent-reachability.py` passes (the new agent is reached by the `/spec-check` literal `subagent_type:`).

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
