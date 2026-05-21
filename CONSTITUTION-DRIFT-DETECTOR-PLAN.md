# CONSTITUTION-DRIFT-DETECTOR-PLAN

**Status**: Drafted 2026-05-17.
**Branch**: `develop-2.0-init`
**Driver**: Facts-first audit (see conversation 2026-05-17) identified the only template-level gap left after `CONSTITUTION-STRENGTHENING-PLAN.md` closed: there is currently no mechanical check that a consumer project's `.devforge/constitute.json` universal-rule bodies still match the framework's current canonical text in `src/constitution.md`. Sister-plan `CONSTITUTION-STRENGTHENING-PLAN.md:110-112` flagged this as "future work, not blocking, only build when a consumer hits the DI gap." This plan promotes it from future-work to now-work because the article's facts-first lens identifies it as the cheapest remaining template-level fact to add.

## Context for next session

`src/constitution.md` (271 lines, forge framework template) propagates to consumer projects via `/constitute`. The chain:

1. `install.sh:117-124` copies `src/constitution.md` → `<target>/constitution.md` ONCE on first install (brownfield safety guard).
2. `update.sh` does NOT overwrite the consumer's `constitution.md` on update (`manifest.json` lists it under `userOwned.patterns`).
3. For projects that have already run `/constitute`, the rendered `<install_root>/constitution.md` comes from `constitute_helper render` walking `.devforge/constitute.json` — NOT directly from `src/constitution.md`. Universal-section rule bodies in the state JSON were transcribed BY THE LLM at `/constitute` time.
4. Result: `src/constitution.md` edits do NOT auto-propagate to consumers. There is currently no mechanism to detect or close that drift.

`CONSTITUTION-STRENGTHENING-PLAN.md:84-112` documents this in detail (read it for the propagation analysis). The 6 patches landed 2026-05-16 are still only on `src/constitution.md`; consumer projects (testForge20, cse-strata-ws-forge wrapper) have their pre-patch universal text in their `.devforge/constitute.json` rule bodies.

The fact-style fix: a helper subcommand that diffs the two surfaces and reports drift. Read-only by design (this plan does NOT include the resync helper that would mutate state — that stays future-work).

## Design

### Scoping decision: forge-internal vs consumer-shipped

**This subcommand is forge-internal.** It runs in the forge dev repo against a path-to-consumer-project argument, not in the consumer's installed `.devforge/lib/`. Rationale:

- The drift check needs the **canonical** universal-rule bodies, which live only in `src/constitution.md` (the framework template). Consumer projects do not ship the template after install (see context step 1-2 above) — the rendered `<install_root>/constitution.md` is project-specific output, not a comparison source.
- Shipping the template alongside the consumer install (so the consumer-side helper could compare locally) adds a new artifact to `install.sh` / `update.sh` / `manifest.json` for a low-frequency check; YAGNI.
- Forge maintainers run this when triaging "should consumer X get re-synced?" — exactly the case `CONSTITUTION-STRENGTHENING-PLAN.md:103-107` describes.

The subcommand is registered under `constitute_helper` with a `forge-internal:` name prefix convention (matching the prefix `CONSTITUTION-STRENGTHENING-PLAN.md:112` proposes for the future resync helper). Not exposed in user-facing `/constitute` flow.

### Section coverage

`CONSTITUTION-STRENGTHENING-PLAN.md:189` lists universal sections: §3.5, §3.6, §3.7, §4.1, §4.2, §4.3, §6.1, §6.2, §6.3, §6.4. The diff walks all of these, but emits drift per-rule (sub-bullet granularity) when the helper schema supports it (the existing `constitute_helper` rule-keyed state JSON does — every rule has a `tag` + body text per `constitute_helper validate` Phase 6.2 in the constitute command spec).

### Boundary on what counts as "drift"

The helper compares **canonical universal-rule body text** (the post-strengthening 3-step concrete patterns added 2026-05-16). False positives risk: stylistic re-wording in the state JSON that doesn't change semantics (e.g., LLM paraphrase at `/constitute` time). Mitigation: exit-code semantics distinguish exact-match (exit 0), semantic-drift-likely (exit 2 — token-set divergence below threshold OR specific load-bearing phrases missing), full-drift (exit 2 — section absent or empty). The helper emits each finding individually so the maintainer can triage. No automated resync.

---

## Step 1 — Parse universal blocks from `src/constitution.md`

**Owner**: python-engineer.

### Files

- `src/devforge/lib/constitute_helper.py` — add internal parser function `_parse_universal_blocks(constitution_md_path: Path) -> dict[str, dict]` that returns a mapping `{section_number: {heading: str, rules: [{tag_or_label: str, body: str}, ...]}}`. Walk markdown headings; identify universal sections by the closed list (§3.5, §3.6, §3.7, §4.1, §4.2, §4.3, §6.1, §6.2, §6.3, §6.4 per CONSTITUTION-STRENGTHENING-PLAN.md:189). For §3.6 SOLID-block sub-rules (Open/Closed, LSP, ISP, DI), parse each sub-block separately. For §4.3 PREFER-block bullets, parse each PREFER-bullet separately.
- `tests/lib/test_constitute_helper.py` — add `test_parse_universal_blocks_happy_path` using the current on-disk `src/constitution.md` as the input fixture; assert the returned dict contains all 10 universal sections + the 4 §3.6 sub-rules.

### Verify

```bash
pytest tests/lib/test_constitute_helper.py::test_parse_universal_blocks_happy_path -v
python3 -c "
import sys; sys.path.insert(0, 'src/devforge/lib')
from constitute_helper import _parse_universal_blocks
from pathlib import Path
d = _parse_universal_blocks(Path('src/constitution.md'))
assert '§3.6' in d and len(d['§3.6']['rules']) == 4, d
print('OK')
"
```

---

## Step 2 — Parse universal-rule bodies from `.devforge/constitute.json`

**Owner**: python-engineer.

### Files

- `src/devforge/lib/constitute_helper.py` — add `_extract_universal_rules_from_state(constitute_json_path: Path) -> dict[str, dict]` returning the same shape as Step 1's parser. Walk the state JSON's section-keyed rules; filter by `tag == "universal"` (per the closed enum already enforced by `constitute_helper verify`); group by section number; emit per-rule bodies.
- `tests/lib/test_constitute_helper.py` — add `test_extract_universal_rules_happy_path` using a fixture `.devforge/constitute.json` (round-trip from `constitute_helper render-config` on a sample wizard run per `feedback_test_first_python_helpers.md`'s real-producer requirement). Assert universal sections present + rule bodies non-empty.

### Verify

```bash
pytest tests/lib/test_constitute_helper.py::test_extract_universal_rules_happy_path -v
```

---

## Step 3 — Add `forge-internal:verify-universal-defaults` subcommand

**Owner**: python-engineer + instruction-author.

### Files

- `src/devforge/lib/constitute_helper.py` — register subcommand `forge-internal:verify-universal-defaults` with flags:
  - `--consumer-path <dir>` (required) — path to the consumer project root.
  - `--canonical-path <constitution.md>` (default: `src/constitution.md` in the forge repo cwd) — for testability.

  Logic:
  1. Resolve canonical: `_parse_universal_blocks(canonical_path)`.
  2. Resolve consumer state: `_extract_universal_rules_from_state(consumer_path / '.devforge' / 'constitute.json')`.
  3. For each universal section in canonical:
     - If absent from consumer state → emit `MISSING <section>`.
     - If body byte-identical → no emission.
     - If body present but text-different → emit `DRIFT <section> [<rule-tag-or-label>]` + a 1-line summary (token-set Jaccard distance or "differs").
  4. Exit 0 if zero `MISSING` + zero `DRIFT`; exit 2 otherwise, with one finding per line on stderr.
  5. Stdout: a JSON report `{consumer: ..., canonical: ..., findings: [...]}` for downstream tooling (mirrors `constitute_helper validate` Phase 6.2 stdout-JSON contract).
- `tests/lib/test_constitute_helper.py` — add:
  - `test_verify_universal_defaults_in_sync` — fixture: state JSON whose universal bodies match canonical → exit 0, empty findings.
  - `test_verify_universal_defaults_missing_section` — fixture: state JSON missing §3.6 → exit 2, stderr cites `MISSING §3.6`.
  - `test_verify_universal_defaults_drift_one_rule` — fixture: state JSON with pre-patch generic DI rule body → exit 2, stderr cites `DRIFT §3.6 [Dependency Inversion]`.

### Verify

```bash
pytest tests/lib/test_constitute_helper.py -k "verify_universal_defaults" -v
./src/devforge/lib/constitute_helper "forge-internal:verify-universal-defaults" --help
# Real integration check against testForge20 consumer:
./src/devforge/lib/constitute_helper "forge-internal:verify-universal-defaults" \
    --consumer-path ~/Projects/testForge20 \
    --canonical-path src/constitution.md
# Expect exit 2 + DRIFT findings for §3.6 (DI, LSP, ISP, Open/Closed), §3.7, §4.3
# because testForge20 was /constitute'd before the 2026-05-16 patches landed.
```

---

## Step 4 — Document the subcommand in repo-root CLAUDE.md (forge-internal table)

**Owner**: instruction-author.

### Why

The repo-root `CLAUDE.md` (at `/Users/mykolakudlyk/Projects/ai-dev-team-forge/CLAUDE.md`) is the forge-internal guidance surface that documents maintainer tooling. Adding `forge-internal:verify-universal-defaults` to its "Where to find what" table (or a sibling maintainer-tools table) avoids the hallucination risk per `feedback_preempt_future_hallucination.md` ("a fresh future session needs to know this verb exists").

**Do NOT edit `src/CLAUDE.md`** — that path is the consumer-shipped template with `{{PROJECT_NAME}}` substitutions installed into target projects. Forge-internal maintainer verbs documented there would inject forge-internal references into every consumer install.

### Files

- Repo-root `CLAUDE.md` (at `/Users/mykolakudlyk/Projects/ai-dev-team-forge/CLAUDE.md`) — find the existing "Where to find what" table or the "Working process" section; add a row:
  | Command | Purpose |
  |---|---|
  | `constitute_helper forge-internal:verify-universal-defaults --consumer-path <dir>` | Diff consumer's `.devforge/constitute.json` universal sections vs `src/constitution.md` canonical text. Exit 0 = in sync; exit 2 = stderr enumerates `MISSING` / `DRIFT` findings. Maintainer-only; no consumer-side install. |
- `CHANGELOG.md` — single-line entry in the unreleased / current-branch section noting the new forge-internal verb. Cross-ref `feedback_release_docs.md` (release docs propagation).

### Verify

```bash
grep -n "forge-internal:verify-universal-defaults" CLAUDE.md
grep -n "verify-universal-defaults" CHANGELOG.md
```

---

## When resuming work

1. Read this plan top-to-bottom + cross-read `CONSTITUTION-STRENGTHENING-PLAN.md` (sister plan).
2. Verify state of each step on-disk:
   ```bash
   grep -nE "_parse_universal_blocks" src/devforge/lib/constitute_helper.py    # Step 1
   grep -nE "_extract_universal_rules_from_state" src/devforge/lib/constitute_helper.py  # Step 2
   grep -nE "forge-internal:verify-universal-defaults" src/devforge/lib/constitute_helper.py  # Step 3
   grep -nE "verify-universal-defaults" CLAUDE.md CHANGELOG.md  # Step 4
   ```
3. For each unfinished step, dispatch `python-engineer` (Steps 1-3) with brief + `instruction-author` (Step 4); follow each with the matching reviewer per `feedback_dual_agent_verify_command_statements.md`.
4. End-of-plan integration: run the Step 3 real integration check against `~/Projects/testForge20`. Expected: exit 2 with `DRIFT` findings for the strengthened sections (§3.6 DI, LSP, ISP, Open/Closed; §3.7 CBM-first; §4.3 Composition). Confirms the detector catches the exact gap `CONSTITUTION-STRENGTHENING-PLAN.md` documented.
5. **No automatic resync from this plan.** The resync helper that mutates `.devforge/constitute.json` to land patched canonical text in place stays future-work per `CONSTITUTION-STRENGTHENING-PLAN.md:110-112`. This plan delivers detection only.

## Out of scope (this plan)

- **`forge-internal:resync-universal-constitution-rules`** — the writer that would mutate consumer state JSON to align with canonical. Stays future-work; only build when a consumer hits the DI gap (per sister plan).
- **Per-language DI import-graph linter** — out of scope; sister plan explicitly defers this as consumer-side hook work, not template-level.
- **Re-running `/constitute` on testForge20 or cse-strata-ws-forge wrapper proactively** — sister plan recommendation stands: defer until natural re-run. This plan's deliverable replaces "by-eye drift inspection" with "shell-fact drift inspection", not "automatic sync."
- **Shipping the canonical template to consumers** — consumer install does not get a copy of `src/constitution.md` as a comparison reference. This plan keeps the check forge-internal exactly to avoid that shipping question.

## Related plans

- `CONSTITUTION-STRENGTHENING-PLAN.md` — closed; 6 strengthening patches applied 2026-05-16. This plan operationalizes the drift-detection gap that closed plan flagged as future-work.
- `COMMAND-VERIFY-GATES-PLAN.md` — sibling plan; command-level facts-first work (3 done-commands' Verify blocks converted from prose to shell).
