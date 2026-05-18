# V3 Fresh Session Handoff

Single-page brief for starting `RESEARCH-FRAMING-REGRESSION-PLAN-V3.md` implementation in a fresh Claude Code session.

## What V3 does

Closes 2 gaps surfaced on 2026-05-18 splitOnSNA bug run:

- **Gap 8** — LLM never opens git blame on a hardcoded literal before recommending its replacement. Misses historical intent (placeholder / forgotten / inherited-refactor) that determines the correct fix layer.
- **Gap 9** — LLM produces fix that passes same identifier twice in single call (`f(x, y, x, z)`). Argument duplication signals default-source belongs at wrapper / state-init / use-case, not call site. No helper-side gate catches it.

V2 (Patches 6+7) closed Gaps 6+7 (adapter randomization). V3 stacks on top — does NOT roll Patches 1-7 back.

## Paste this into the fresh session

```
Read /Users/mykolakudlyk/Projects/ai-dev-team-forge/V3-FRESH-SESSION-HANDOFF.md, then RESEARCH-FRAMING-REGRESSION-PLAN-V3.md top-to-bottom.

Implementation order: PRE-FLIGHT (verify memory entry + baseline tests) → Patch 8 (literal archaeology gate, check 17, Phase 2.5b spec) → Patch 9 (argument-duplication shape-check, check 18; depends on Patch 8 literal-replacement regex). Each implementation patch = one commit on develop-2.0-init.

Per-patch flow:
  (a) python-engineer test-first (helper changes + tests in same turn; baseline pytest 267/267 before; +N new tests after).
  (b) python-reviewer; apply findings; re-loop until clean.
  (c) Orchestrator-direct spec edit in src/commands/research/main.md.
  (d) instruction-reviewer; apply findings; re-loop until clean.
  (e) Cross-check grep for affected identifiers / paths / check numbers.
  (f) Update V3 plan Status field.
  (g) Commit (stage only patched files: research_helper.py + research/main.md + test_research_helper.py + RESEARCH-FRAMING-REGRESSION-PLAN-V3.md).

After Patch 9 lands + tests green: run ~/Projects/ai-dev-team-forge/update.sh --force /Users/mykolakudlyk/Projects/testForge20, then in a fresh testForge20 session re-dispatch /research on the splitOnSNA topic (same phrasing as 2026-05-18 run). Empirical-verify acceptance: V3 must propose S3 wrapper-default in turn 1 AND record literal_archaeology row with --intent inherited-refactor for the false at OrderViewer.vue:290.

DO NOT roll back Patches 1-7. DO NOT skip the empirical-verify replay.
```

## Pre-flight verifications

Run these BEFORE writing any V3 code:

```bash
# 1. Memory entry exists
ls /Users/mykolakudlyk/.claude/projects/-Users-mykolakudlyk-Projects-ai-dev-team-forge/memory/feedback_literal_archaeology_and_argument_duplication.md

# 2. V3 plan exists at repo root
ls /Users/mykolakudlyk/Projects/ai-dev-team-forge/RESEARCH-FRAMING-REGRESSION-PLAN-V3.md

# 3. Patches 1-7 still landed (7 commits)
git -C /Users/mykolakudlyk/Projects/ai-dev-team-forge log --oneline develop-2.0-init -15 | grep -E "Patch [1-7]"
# Expected: 832aa4e (1), b8e6098 (2), c8a9ca3 (3), 5eaa704 (4), 4a6a519 (5), 7a82a87 (6), 73ef728 (7)

# 4. V2 artefacts present in helper
grep -nE "cmd_record_data_flow_chain|cmd_record_value_production_site|check 15|check 16|stable-across-calls" \
  /Users/mykolakudlyk/Projects/ai-dev-team-forge/src/devforge/lib/research_helper.py | head -8

# 5. V2 spec sections present
grep -nE "Phase 2.4d|record-value-production-site|check 16" \
  /Users/mykolakudlyk/Projects/ai-dev-team-forge/src/commands/research/main.md | head -8

# 6. Baseline tests green (267 expected)
/Users/mykolakudlyk/Projects/ai-dev-team-forge/.venv-test/bin/pytest \
  /Users/mykolakudlyk/Projects/ai-dev-team-forge/tests/lib/test_research_helper.py 2>&1 | tail -3

# 7. Empirical artefact for verify step still exists
ls -la /Users/mykolakudlyk/Projects/testForge20/research/2026-05-18-splitonsna-boolean-incorrect-on.md \
       /Users/mykolakudlyk/Projects/testForge20/db-cse-ui-strata/apps/app-web/src/components/order/OrderViewer.vue
```

Any failure → STOP. Resolve before proceeding.

## Patch 8 — quick spec

**Helper additions:**
- `default_report_state()` adds `"literal_archaeology": []`.
- New subparser `record-literal-archaeology` with 6 required args: `--literal`, `--file-line`, `--introduced-by` (commit sha 7-40 hex), `--introduced-when` (ISO date), `--commit-subject`, `--intent` (6-value enum: `placeholder | migrated | deliberate | forgotten | inherited-refactor | generated`).
- Literal-token validation regex covers: `true|false|True|False|null|undefined|None`, decimal `-?\d+(\.\d+)?`, hex `-?0x[0-9a-fA-F]+`, BigInt `-?\d+n`, scientific `-?\d+(\.\d+)?[eE][+-]?\d+`, double/single/backtick strings (no `${}` interpolation in templates). Array/object/regex/function literals OUT-OF-SCOPE.
- Dedupe on `(literal, file_line)`.
- New verify check 17: bug mode + recommended-approach text matches literal-replacement regex (`replace <X> with <Y>` / `change <X> to <Y>` / `<X> -> <Y>`) → require matching `literal_archaeology` row.

**Spec addition:** new Phase 2.5b section between Phase 2.5 and Phase 2.6 in `src/commands/research/main.md`. Mandates `git log -S "<literal>" -- <file>` + `git blame -L` before recommending literal replacement. Per-intent recovery rules (placeholder / forgotten / inherited-refactor → escalate one layer; migrated → check legacy; deliberate → cite commit msg; generated → fix at template).

**Cost:** ~2-5K tokens per archaeology dig (one `git log -S`, one `git show --stat`, one `git blame -L`).

## Patch 9 — quick spec

**Helper additions:**
- New optional arg `--proposed-call-shape "<post-fix call as string>"` on `set-recommended-approach`. REQUIRED when bug mode AND (`--single-layer-justification` set OR recommended-approach text matches Patch 8 literal-replacement regex).
- Helper parses call shape (regex `^[A-Za-z_][\w.]*\([^)]*\)$`, split on top-level commas). Identifier regex with optional chaining: `[A-Za-z_][\w]*(?:\??\.[A-Za-z_][\w]*)*`.
- Rejects if same identifier appears > 1 time in arg list.
- Fail-soft on parser failure (advisory, no block).
- New verify check 18 mirrors at verify time (catches state-mutation bypass).

**Spec addition:** Phase 3 recommended-approach drafting must simulate post-fix call shape literally + check for arg duplication; if duplicated, escalate default-source one layer up before drafting.

## Empirical-verify acceptance (after Patch 9 lands)

1. `update.sh --force /Users/mykolakudlyk/Projects/testForge20`
2. Open fresh Claude Code session in `~/Projects/testForge20`.
3. Run `/research "<splitOnSNA topic phrasing, same as 2026-05-18 run>"`.
4. Diff against `research/2026-05-18-splitonsna-boolean-incorrect-on.md`.

**Pass criteria (both must hold):**
- New run proposes S3 wrapper-default (`fetchOrder(split: boolean = isExternalUser.value)`) as Approach 1 WITHOUT requiring user iteration.
- New run records `literal_archaeology` row for `false` at `OrderViewer.vue:290` with `--intent inherited-refactor`.

**Fail mode:** if V3 also misses, surface new gap + draft V4. Do NOT silently revert.

## Out of scope (do NOT pull into V3)

- State-initialization audit (`orderInitialState.isSplit: false` defect) → /audit
- Dead-code sweep (orphaned `OrderBLoC.toggleSplit`) → /audit
- Backend defense-in-depth probe (H_B server-side coercion check) → too heavyweight for per-run gate
- Patches against /specify, /plan downstream — separate plans if regression class re-appears
- Recipe-split discussion (long-term concern) — V3 is short-term pragmatic recipe-quality improvement

## Cross-references

- Plan: `/Users/mykolakudlyk/Projects/ai-dev-team-forge/RESEARCH-FRAMING-REGRESSION-PLAN-V3.md`
- Memory: `feedback_literal_archaeology_and_argument_duplication.md`
- Predecessor: `RESEARCH-FRAMING-REGRESSION-PLAN-V2.md` (verified 3/3 on Strata duplicate-options)
- V1: `RESEARCH-FRAMING-REGRESSION-PLAN.md` (Patches 1-5, scored 1.5/3 empirically)
- Empirical artefact: `testForge20/research/2026-05-18-splitonsna-boolean-incorrect-on.md`
- Subject file: `testForge20/db-cse-ui-strata/apps/app-web/src/components/order/OrderViewer.vue:290`
