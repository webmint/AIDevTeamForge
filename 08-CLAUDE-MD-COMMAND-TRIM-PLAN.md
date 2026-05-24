# CLAUDE-MD-COMMAND-TRIM-PLAN

**Status**: **SHIPPED 2026-05-24** on `develop-2.0-init` (working-tree only, not yet committed). `src/CLAUDE.md` 3383 → 2806 words (−17.1% always-on). Supersedes `06-CONDITIONAL-CONTEXT-PLAN.md` (ABORTED — see `done-plans/06-CONDITIONAL-CONTEXT-PLAN.md`). See Step 0/1/2 result blocks at end.
**Branch**: `develop-2.0-init`.
**Driver**: 06 set out to cut always-on token cost in spawned consumer projects via path-scoped `.claude/rules/`. Investigation killed 06 (premise false; wrong mechanism) but surfaced the *real* always-on cost: the deep per-command phase paragraphs in the consumer-overlay `src/CLAUDE.md`. This plan removes that cost by deletion.

## Context for next session

In a spawned consumer project, the only always-on per-turn surface is the emitted `CLAUDE.md` (copied verbatim from `src/CLAUDE.md` by `install.sh` ~line 145, with `{{PLACEHOLDER}}` substitution — there is no python emitter for it). `.claude/commands/*.md` bodies load **only on invocation**, not always-on.

**Load-bearing finding (verified 2026-05-24 via `claude-code-guide`, docs.claude.com — do NOT re-litigate):**
- Custom slash commands are **merged into skills** in current Claude Code (v2.x). The model normally sees each command's `description` frontmatter always-on so it can route — **EXCEPT** when `disable-model-invocation: true`, where the docs' context-loading table states *"Description not in context"* (code.claude.com/docs/en/skills).
- **Every forge command sets `disable-model-invocation: true`** (deliberate manual-only / full-user-control stance — confirmed by user 2026-05-24). Therefore the model has **zero native awareness** the forge commands exist.
- Consequence: the command **catalog** in `CLAUDE.md` (the flow diagram lines 39–42 + the bullet list lines 44–58 + the one-line purpose in each `#### Command Details` entry) is **load-bearing** — it is the only model-facing source of command awareness. It must NOT be deleted.
- What IS removable: the **deep phase-by-phase walkthroughs** inside three `#### Command Details` entries. They restate, lossily and always-on, the Phase 0/1/2/3 mechanics that already live authoritatively in the command **body** (e.g. `src/commands/research/main.md` ≈ 12.3K words) and load on invocation. They add nothing to awareness/routing.

**Measurement (Step 0 of the aborted 06, run 2026-05-24):** `src/CLAUDE.md` = 3383 words. The three bloated entries:

| `#### Command Details` entry | current words | has command file (body carries mechanics)? |
|---|---|---|
| `/specify` | 299 | yes — `src/commands/specify/main.md` |
| `/discover` | 268 | yes — `src/commands/discover/main.md` |
| `/research` | 170 | yes — `src/commands/research/main.md` |
| **subtotal** | **737** | |

Collapsing the three to purpose one-liners (≈ 20w each, matching the existing `/plan` 23w / `/constitute` 18w / `/onboard` 28w entries in the same block) drops ≈ **680 words ≈ 20% of the always-on file**, every consumer turn, with zero awareness loss.

**This plan does NOT touch:**
- The flow diagram (lines 39–42) or bullet list (lines 44–58) — load-bearing awareness/order.
- The 10 **phantom** command entries (`/execute-task`, `/breakdown`, `/review`, `/verify`, `/summarize`, `/finalize`, `/fix`, `/refactor`, `/security`, `/audit`) — they have **no command file yet**, so their `####` text is the current best documentation of intent. Trimming them is `07-EXECUTE-TASK-REDESIGN-PLAN.md`'s concern (when each command ships, its mechanics move into its body). Leave untouched here.
- The already-terse real-file entries (`/plan`, `/constitute`, `/onboard`) — already one-liners.
- `disable-model-invocation: true` on any command — manual-only is the framework's design intent, not a bug.

Cross-cutting discipline (apply to every step):
- **Sentence-level hallucination check** per `feedback_sentence_level_hallucination_check_specs.md` — each new one-liner must be verifiable now / mechanically true; no forward-refs to future phases.
- **Cross-check after every change** per `feedback_cross_check_after_every_change.md` — grep for any sentence elsewhere that points at the deleted phase detail ("see Command Details for /research", etc.) before deleting.
- **Spec-doc edits go through `instruction-author` + `instruction-reviewer`** per `feedback_dual_agent_verify_command_statements.md` (`src/CLAUDE.md` is a consumer-overlay spec doc).
- **No emitter change** — `CLAUDE.md` is `cp`-copied by `install.sh`, not python-emitted; no pytest surface. Verification is word-count delta + grep cross-check + install smoke.

---

## Step 0 — Cross-check before deleting

**Severity**: gate. **Owner**: orchestrator.

### Why

Before removing any always-on text, confirm (a) nothing else references the deep paragraphs, (b) the bullet-list one-liner for each of the three commands still exists (so awareness survives the trim), (c) the command files exist (so mechanics survive on invocation). Per `feedback_cross_check_after_every_change.md` a dangling reference left behind is part of the same change.

### Procedure

1. `grep -rn "Command Details" src/ docs/ scripts/` — confirm no cross-reference depends on the deep `/research|/discover|/specify` paragraphs.
2. Confirm the three command files exist and carry a `description:` frontmatter (the one-liner seed): `src/commands/{research,discover,specify}/main.md`.
3. Confirm bullet-list one-liners exist for all three (`src/CLAUDE.md` lines 44–58).
4. Record baseline: `wc -w src/CLAUDE.md`.

### Verify

```bash
grep -rn "Command Details" src/ docs/ scripts/   # expect: only the heading itself in src/CLAUDE.md
grep -n "^description:" src/commands/{research,discover,specify}/main.md  # 3 hits
wc -w src/CLAUDE.md   # baseline (expect 3383)
```

---

## Step 1 — Collapse the three deep paragraphs to one-liners

**Severity**: high. **Owner**: `instruction-author` + `instruction-reviewer` (iterative loop until clean).

### Why

Awareness needs only name + one-line purpose (the model's only command-awareness source, given `disable-model-invocation: true`). Phase mechanics are execution detail already in the command body. Collapse, don't delete the entry — keeps the `#### Command Details` block structurally uniform with the existing `/plan` / `/constitute` / `/onboard` one-liner entries.

### Files

- `src/CLAUDE.md` — rewrite the `#### \`/research ...\``, `#### \`/discover ...\``, `#### \`/specify ...\`` entries. Each new body = one to two lines: the command's purpose (seed from its `description:` frontmatter), preserving the `(optional)` marker for `/research` + `/discover` and the "requires approval" gate note for `/specify` if present in the bullet list. No Phase 0/1/2/3 enumeration. No "see §" / "see above" forward-refs.

### Verify

```bash
# Each of the three entries is now short (≤ ~30 words, like /plan's existing entry):
# (manual read of the three #### entries)
grep -n "Phase 0\|Phase 1\|Phase 2\|Phase 3" src/CLAUDE.md   # 0 matches inside the 3 trimmed entries
grep -n "see CLAUDE\|see §\|see above" src/CLAUDE.md          # 0 matches in the 3 entries
wc -w src/CLAUDE.md   # dropped ≈ 680 words from baseline (within ±10%)
```

### Argue

- **Why collapse to a one-liner rather than delete the `####` entry outright?** The bullet list already carries an awareness one-liner, so deletion would lose nothing functionally — but the `#### Command Details` block documents every real command uniformly, and three holes would invite a future session to "restore" them. A uniform terse block is the lower-hallucination state.
- **Why only these three?** They are the only entries that are both bloated AND backed by a real command file (mechanics live on invocation). The phantom entries are the only doc of not-yet-built commands; the short real entries cost nothing.
- **Why not also drop the bullet list (lines 44–58) since the `####` block exists?** The bullet list is the load-bearing awareness layer and is cheap (one line each). The cost driver is the deep paragraphs, not the one-liners. Removing the catalog entirely would blind the model to the commands (`disable-model-invocation: true`).

---

## Step 2 — Doc updates + close-out

**Severity**: low (housekeeping for future-session coherence). **Owner**: orchestrator.

### Why

Per `feedback_preempt_future_hallucination.md`: a fresh session must understand WHY the catalog is terse and must not "helpfully" re-expand the three paragraphs.

### Files

- `CHANGELOG.md` — entry under `develop-2.0-init`: trimmed three per-command phase paragraphs in consumer-overlay `src/CLAUDE.md` (~20% always-on reduction); rationale = `disable-model-invocation: true` makes the catalog load-bearing but the phase detail redundant with the on-invocation command body.
- This plan — append `## Step N result` blocks (Step 0 baseline + Step 1 word delta).
- Memory `project_command_awareness_disable_model_invocation.md` — the load-bearing finding (forge commands set `disable-model-invocation: true` → descriptions not in model context → `CLAUDE.md` catalog is the only awareness source → keep purpose one-liners, never delete the catalog).

### Verify

```bash
grep -n "command.*trim\|disable-model-invocation" CHANGELOG.md   # entry present
ls .claude/projects/-Users-mykolakudlyk-Projects-ai-dev-team-forge/memory/project_command_awareness_disable_model_invocation.md
```

---

## When resuming work

1. Read *Context for next session* — especially the load-bearing finding (do not re-litigate `disable-model-invocation`).
2. Read the most recent `## Step N result` block for the resume point.
3. `git log --grep "CLAUDE-MD-COMMAND-TRIM"` for landed commits.

The catalog (flow diagram + bullet list + one-line `####` purposes) is **load-bearing** because every forge command sets `disable-model-invocation: true`. Never delete it; only the phase-detail walkthroughs are removable.

## Out of scope

- Phantom-command `####` entries — owned by `07-EXECUTE-TASK-REDESIGN-PLAN.md`.
- Any change to `disable-model-invocation: true` — manual-only is the framework's design intent.
- Path-scoped `.claude/rules/` — wrong mechanism (see aborted `06`).

---

## Step 0 result (2026-05-24)

Gate PASSED. `grep "Command Details"` across `src/ docs/ scripts/` → only the heading itself in `src/CLAUDE.md` (no inbound cross-refs). All three command files carry a `description:` frontmatter seed. Bullet-list one-liners (lines 44–58) exist for all three (awareness survives the trim). Baseline `wc -w src/CLAUDE.md` = **3383**.

## Step 1 result (2026-05-24) — SHIPPED

Collapsed the three `#### Command Details` entries to purpose one-liners (seeded from each command's `description:` frontmatter + the load-bearing gate/handoff/branch facts). `wc -w src/CLAUDE.md` = **2806** → dropped **577 words (−17.1%)**. Verify gates clean: 0 `Phase N` enumeration in the trimmed entries, 0 forward-refs.

Authored orchestrator-direct (authoritative `description` seeds + full-file context on hand), then `instruction-reviewer` verified — 3 findings, all applied: (1) medium — `/research` handoff block is conditional on an actionable verdict (added "when the verdict is actionable"); (2) low — `/discover` "with no existing related code" was a false restriction (removed; the internal-prior-art survey exists precisely for when related code may exist); (3) nit — "2-3 design options" → "design options (typically 2-3)" (enforced min is 1). Orchestrator also extended fix (1) to `/discover`'s handoff clause for consistency (the pre-trim text gated it on verdict too). Re-verify clean at 2806 words.

## Step 2 result (2026-05-24) — DONE

`CHANGELOG.md` `[Unreleased] → Changed` entry added (trim + the `disable-model-invocation` rationale). Memory `project_command_awareness_disable_model_invocation.md` saved + indexed in `MEMORY.md`. Plan status → SHIPPED.

**Plan SHIPPED 2026-05-24 on `develop-2.0-init`. Not yet committed** (working-tree only). Manual testForge20 install smoke (confirm trimmed `CLAUDE.md` still emits + reads coherently) optional — `CLAUDE.md` is `cp`-copied so no emitter risk.
