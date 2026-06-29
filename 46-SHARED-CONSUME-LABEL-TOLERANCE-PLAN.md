# 46 — Shared `_consume` Label-Tolerance & Backtick-Strip Plan

**Status:** ✅ BUILD DONE 2026-06-29 on `develop-2.0-init` (working tree, not yet committed). Steps 1–3 shipped + reviewed; 139 `test_consume.py` tests (37 new), full `_shared`+`_audit`+`_review`+`_grill` suite **1914 passed, zero regressions** (independently re-run). See `## Outcome` at the foot.
**Owner module:** `src/devforge/lib/_shared/_consume.py` (the shared refutation/finding-parse engine — feeds `/review`, `/audit`, `/grill`).

## Problem

A consumer install (mintEnvoy, feature `010-request-bar-fidelity`) hit `/review` rendering a **false findings-empty report** across three rounds. Real, confirmed findings from `qa-reviewer` and `design-auditor` were silently dropped to 0 until the orchestrator manually normalized the agent tmp files before re-running `consume-tmp` / `validate-findings`.

Impact chain: `/review` renders empty → `/verify` folds the empty review into a wrongly-**APPROVED** verdict. Silent correctness failure, not a crash.

### Reproduced (2026-06-29)

```
dash -> status complete count 0      # qa-reviewer used "- Severity:" dash bullets
bold -> status complete count 0      # design-auditor used "**Severity**:" + backtick File path
validate backtick File -> discard_counts {'file_missing': 1, ...}  passed 0
```

### Two root causes — both in `_shared/_consume.py`

**RC1 — label decoration drops the whole finding.** Finding-field regexes anchor a *bare* label at line start:

```python
_RE_SEVERITY = re.compile(r'^Severity:\s*(.+)$', re.MULTILINE)   # + File/Line/Pattern/Confidence/Category
_RE_EVIDENCE_BLOCK = re.compile(r'Evidence:\s*\n```+[^\n]*\n(.*?)```+', re.DOTALL)
```

When an LLM finder writes `- Severity: High` (dash bullet) or `**Severity**: High` (bold), the `^Severity:` anchor misses → `_parse_finding_block` returns `None` on the first missing **required** field (severity/file/line/pattern/confidence) → the block is silently discarded. The `## Finding N` header still matches, so `parse_agent_tmp` reports `status=complete, finding_count=0`. The same decoration on `**Evidence:**` empties the evidence → the finding survives consume but is later dropped at `_validate` check 3 (`quote_mismatch`) — same silent-drop class.

**RC2 — backtick-wrapped File/Line value.** `_RE_FILE` captures `` `src/.../RequestBar.css` `` verbatim (backticks included); `_validate._resolve_path` joins the backticked literal → no file on disk → `REASON_FILE_MISSING`. A backtick-wrapped `Line:` value fails earlier: `_RE_LINE` is `^Line:\s*(\d+)$` (digits-only group), so `` Line: `12` `` produces **no regex match** → the `if not m: return None` guard in `_parse_finding_block` fires → the block is dropped at consume. (The `try/except ValueError` around `int()` is unreachable for this case — the regex never matches a backticked value to begin with.)

## Decisions

- **D1 — fix at the single chokepoint `_consume.py`, NOT `_validate.py`.** `consume-tmp` is the sole producer feeding `validate-findings` in every flow (`/review`, `/audit`, `/grill`). Cleaning the value once at parse time makes validate's `file_missing` symptom disappear with zero `_validate` change. Lower blast radius, single source of truth.
- **D2 — tolerance covers ALL finding labels, not only the fatal inline fields.** Bold/dash on `Evidence:`/`Why it's wrong:`/`Remediation:` is the same silent-drop class (empties evidence → validate check-3 drop). Normalize the full known-label set so the failure mode is closed, not narrowed.
- **D3 — fence-aware normalization.** The normalization pass that strips bullet/bold decoration from label lines MUST skip lines inside fenced code blocks, because evidence code bodies legitimately begin with `-`/`*` or contain `**` and must not be rewritten.
- **D4 — strip surrounding backticks from single-line field VALUES only** (File, Line, Severity, Pattern, Confidence, Category). NOT from Evidence/Why/Remediation prose — those legitimately contain backticks.
- **D5 — scope guard (leave untouched):** the `# Agent:` / `# Status:` / `# Finding count:` header regexes (non-fatal — they fall back to defaults), the `## Finding N` block-header decoration, and `_verify.py`'s verdict parser (`consume_verdicts` / `_parse_verdict_block` — parses `## Verdict N` blocks, NOT `## Finding N`; a structurally separate parser for a different output format). **Note:** `_verify.py` is left untouched for lack of evidence, NOT because it is immune — it copies the same bare-label-anchored regex style (`_verify.py` `_RE_FILE`/`_RE_LINE`/`_RE_PATTERN` are identical in anchor form to `_consume.py`), so it carries the same latent decoration risk. It is out of scope here only because refuter output has not been observed to fail; if it does, this plan's mechanism is the template to extend there. Expanding to any of these without evidence violates minimal-change discipline.

## Mechanism

1. **`_normalize_label_lines(block_text)`** — new private helper in `_consume.py`. Walks the block line-by-line, toggling an `in_fence` flag on any line whose stripped form starts with ` ``` `. For lines OUTSIDE a fence that match a decorated known-label pattern, rewrite to the bare `Label: value` form. Known labels: `Severity`, `File`, `Line`, `Pattern`, `Confidence`, `Category`, `Evidence`, `Why it's wrong`, `Remediation`. Decoration tolerated: leading indent, one list bullet (`-`/`*`/`+` + whitespace), and bold (`**`) around the label and/or colon. Called once at the top of `_parse_finding_block`, before any existing regex/`startswith`/`_extract_section` logic runs — so that logic is unchanged.
2. **`_strip_inline_code(value)`** — new private helper. Strips matched surrounding backtick run(s) from a single-line value. Applied **inside `_normalize_label_lines`** to the rewritten value of the single-line fields (File, Line, Severity, Pattern, Confidence, Category) — i.e. `` Line: `12` `` is normalized to `Line: 12` and `` File: `src/x.css` `` to `File: src/x.css` BEFORE the existing field regexes run. This is the reason `_RE_LINE` can stay `^Line:\s*(\d+)$` unchanged — the backtick is gone by the time the regex matches. Value-stripping is applied ONLY to those six single-line fields, NOT to the `Evidence` / `Why it's wrong` / `Remediation` label lines (their values are fenced code or prose that may contain legitimate backticks).

The existing field regexes, `_extract_section`, and the evidence-block logic are NOT modified — they run unchanged on the already-normalized block.

The `## Finding N` header itself (`#` prefix, not a bullet) does not match the label pattern, so it is preserved. The decorated-label regex requires a `:` immediately after the (optionally bolded) label, so prose like `Severity is high` does not false-match.

## Steps

### Step 1 — implement + test (`python-engineer`)

Add `_normalize_label_lines` + `_strip_inline_code` to `_shared/_consume.py`; wire both into `_parse_finding_block`. Add regression tests to `tests/lib/_shared/test_consume.py`:

- dash-bullet labels (`- Severity:` …) → finding parses, `finding_count == 1`
- bold labels (`**Severity**:` …, incl. `**Severity:**` colon-inside variant) → parses
- combined `- **Severity**: High` → parses
- backtick File value → `finding.file == "src/.../RequestBar.css"` (no backticks)
- backtick Line value (`Line: \`12\``) → `finding.line == 12` (value backtick stripped during normalization → `\d+` matches; no drop)
- bold `**Evidence:**` header → evidence captured non-empty
- **fence-safety:** a finding whose evidence code body contains lines starting with `-`/`*` and containing `**` → those lines pass through verbatim (NOT rewritten)
- **non-regression:** an existing bare-label finding parses byte-identically (golden)
- prose `Severity is high` (no colon) in a Why paragraph → not mis-detected as a field

**Verify:** `python3 -m pytest tests/lib/_shared/test_consume.py -q` green; the two reproductions from this plan now yield `finding_count == 1`.

### Step 2 — review loop (`python-reviewer`)

Review Step 1's diff + tests for logic correctness, fence-tracking edge cases, regex false-match risk, and non-regression. Apply findings, re-run, loop until clean.

**Verify:** reviewer returns no High/Medium findings; tests green.

### Step 3 — cross-check consumers + full suites

Grep consumers (`_audit/_cli.py`, `_review/_cli.py`, `_grill/_cli.py`, `_review/_brief.py`, `_grill/_brief.py`) for any reliance on the OLD bare-label-only behavior — there should be none (they call `parse_agent_tmp` / `validate_findings` as opaque). Run `_shared` + `_audit` + `_review` + `_grill` suites.

**Verify:** `python3 -m pytest tests/lib/_shared tests/lib/_audit tests/lib/_review tests/lib/_grill -q` green, zero regressions.

## When resuming work

Read this plan in full. Check `git log` for the implementing commit. If Steps 1–2 are done but Step 3 not, run the consumer cross-check + full suites. The fix is purely additive to `_consume.py` — no consumer-side or `_validate.py` edits are expected.

## Outcome (2026-06-29)

Shipped to `src/devforge/lib/_shared/_consume.py`:
- `_strip_inline_code(value)` — strips a balanced surrounding backtick run from a single-line value.
- `_normalize_label_lines(block_text)` — fence-aware pass at the top of `_parse_finding_block`; rewrites decorated known-label lines (indent / one `-`/`*`/`+` bullet / `**` bold around label and/or colon) to bare `Label: value`, and backtick-strips the value for the six single-line fields. The boolean `in_fence` toggle is the markdown-correct fence model (a fence opens at ` ``` ` and closes at the next ` ``` `).
- `_parse_finding_block` extracts `why` / `remediation` from the **post-evidence tail** (`block_text[m_ev.end():]`) so a field-looking line inside a well-formed evidence block is no longer mis-picked.

Empirically verified (clean file-based repro, not shell heredoc — shell apostrophe-mangling produced a false `why=''` mid-review; the corrected repro shows full extraction): both the dash-bullet and bold+backtick reproductions parse to `finding_count == 1` with `file`/`line`/`severity`/`why`/`remediation` all correct, and the backtick `File`/`Line` values are stripped.

**Reviewer findings (4) all applied:** F1 (low) why/remediation tail-scoping; F2 (nit) removed dead `re.DOTALL`; F3 (nit) non-regression test now asserts `why`/`remediation`/`category`; F4 (nit) added `*`/`+` bullet tests. The reviewer's suggested fence-depth-counter for F1 was **rejected** — traced to produce the identical mis-pick (the inside-evidence label sits at even depth → still treated as outside); tail-scoping is the correct mechanism.

### Known residual limitation (NOT a regression vs the goal; documented so a future session does not mistake it for fully closed)

The tail-scoping fixes the **representable** case (a `Why it's wrong:`-looking line inside a single well-formed evidence fence). It does **NOT** fix the adversarial **malformed-markdown** case the reviewer constructed: an evidence body containing a *bare* ` ``` ` line (which markdown treats as the closing fence) followed by a decorated `**Why it's wrong**: …` line — that line lands *after* `m_ev.end()` (the non-greedy evidence regex closes at the first ` ``` `), so it is in the tail and `_extract_section` still picks it before the real field. This input is non-representable markdown (a code block cannot contain an unescaped ` ``` `), the structure is genuinely ambiguous, and the harm is **cosmetic only** — `why`/`remediation` prose, never the finding's `severity`/`file`/`line`/`evidence` and never a drop or a wrong gate verdict. Closing it would require contradicting the one-evidence-block output contract or a fragile last-occurrence heuristic; judged not worth the complexity for a malformed-input cosmetic edge.

### Follow-ups (not done here)
- **Commit** — working-tree only; commit when the maintainer asks.
- **REGRESSION-ANCHORS.md** — pin the dash / bold / backtick-File / backtick-Line reproductions to the new `test_consume.py` classes once committed (the plan's own anchor-candidate note).
- **`_verify.py`** — carries the same bare-label regex style (D5); extend this mechanism there IF refuter output is ever observed to fail. No evidence yet.

## Context for next session

This is a parser-robustness fix for LLM-authored markdown in the shared finding-parse engine. The class of bug (a parser silently dropping decorated-but-valid LLM output, yielding a false-empty result a downstream gate trusts) is a regression-anchor candidate — consider pinning the dash/bold/backtick reproductions to `REGRESSION-ANCHORS.md` once shipped. Related project memory: `review-finder-dash-prefix-parse`.
