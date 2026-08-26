---
name: spec-check
description: Spec-tier SMT consistency prover — the requirement-level mirror of `/devforge:grill`. Runs by user invocation between `/devforge:specify` and `/devforge:plan` to prove whether a feature's acceptance criteria are mutually consistent BEFORE the plan is built. It formalizes each AC into a constraint IR (a fixed 2-pass quorum, so the verdict is reproducible, not a one-off), runs the Z3 SMT solver, and recommends CONSISTENT / REVISE-SPEC / DISMISS. It is a consistency prover, NOT a mind-reader — it checks whether ACs contradict EACH OTHER, not whether they are what you MEANT; a single coherent-but-wrong AC passes. It is STRONG on numeric/state/enum invariants; it catches a permission clash ONLY when a permitting case is asserted reachable (it does NOT check permission/role logic in general). The proof is a deterministic proof over a human-checked, quorum-stable formalization — never a bare "deterministic proof of your spec"; the human checks the TRANSLATION and owns every verdict the run raises, while a clean result is accepted without a question. Runs only when the USER invokes it — never auto-invoked — and `/devforge:plan` requires a fresh report from it: that gate reads the report's presence and freshness only, never its verdict.
argument-hint: "[feature-or-spec]"
disable-model-invocation: true
---

# /devforge:spec-check — SMT Requirements-Consistency Prover

`/devforge:spec-check` is a standalone pipeline stage positioned BETWEEN `/devforge:specify` and `/devforge:plan`. It is the requirement-level mirror of `/devforge:grill`: `/devforge:grill` attacks the finished PLAN (the HOW), and `/devforge:spec-check` proves the finished SPEC's acceptance criteria (the WHAT) are mutually consistent before `/devforge:plan` spends effort designing against a self-contradictory requirement set. Mental model: **`/devforge:spec-check` is to `/devforge:specify` what `/devforge:grill` is to `/devforge:plan`** — an adversarial check, each guarding its own artifact, one tier apart. The two now share an invocation shape: each is typed by the user, never auto-runs, and is a precondition of the stage below it — a fresh `/devforge:spec-check` report before `/devforge:plan`, a `/devforge:grill` run before `/devforge:breakdown`. They differ on the PREDICATE their gate reads: `/devforge:plan`'s reads presence AND freshness, so editing `spec.md` re-blocks it; `/devforge:breakdown`'s reads presence and the recorded adversary run only, so a `grill.md` written against a since-edited `plan.md` still passes.

It is neurosymbolic — two parts, one soft, one hard. **Auto-formalization (soft, LLM):** the `spec-formalizer` agent translates each AC into a typed constraint IR (the helper owns the IR schema; the LLM fills the values). **Logical analysis (hard, Z3):** the deterministic Z3 SMT solver checks the conjunction of the formalized constraints — `unsat` means the ACs cannot all hold, and the solver's `unsat_core` returns the exact conflicting AC subset. `/devforge:spec-check` writes `specs/[feature]/spec-check.md` and recommends a 3-way disposition. Read-only on the spec — it never modifies `spec.md`; it WIP-commits only its OWN artifacts (the report + any re-entry seed) in an install-repo-only, fail-soft `[WIP]` commit that folds into `/devforge:finalize`'s squash. State-free file structure + render shape are owned by `.devforge/lib/spec_check_helper`; the orchestrator composes values via verb subcommands.

**MANDATORY under-promise — do not oversell this command.** Three boundaries are load-bearing and appear in every user-facing string:

- **Consistency prover, NOT a mind-reader (D11).** `/devforge:spec-check` checks whether ACs contradict EACH OTHER — it catches self-contradiction in the requirement set. It does NOT catch a single coherent-but-wrong AC (one that asks for the opposite of what you meant, when nothing else contradicts it); that is semantic/intent correctness, which no solver can judge, and it stays with the soft-LLM stages (`/devforge:research`'s rubric, `/devforge:grill`'s devils-advocate, human approval gates).
- **Honest permission boundary (D9).** It is STRONG on numeric/state/enum invariants. Conditional-permission clashes are caught ONLY when a permitting case is asserted reachable (an AC that asserts the reachable scenario, e.g. "a non-admin CAN delete"). Do NOT claim "permission/role logic" is caught in general — a set of pure IF/THEN rules is genuinely consistent until a permitted case is asserted, and the solver correctly reports that.
- **Determinism is honest, not bare (D13).** The Z3 proof is deterministic GIVEN a formalization, but the English→logic formalization is a soft LLM step that can differ run-to-run. So the command formalizes a fixed 2 times (a quorum) and surfaces a contradiction as CONFIRMED only when the same conflicting AC set reproduces across a majority of passes; the human checks the translation. Never bare-claim "a deterministic proof of your spec" — say "a deterministic proof over a human-checked, quorum-stable formalization."

**`/devforge:spec-check` produces FINDINGS PLUS a recommended DISPOSITION — but the disposition is a RECOMMENDATION, not a binding verdict.** The human owns every call the run actually raises — and the run raises one only when there is something to decide. A CLEAN result (no contradiction reproduced across the formalization passes, every acceptance criterion's subject resolved, no citation miss) is accepted without asking: the report is still rendered, written, and committed, but no question is put to the human, because nothing has been alleged. Anything else surfaces the report and asks. The three dispositions are CONSISTENT (proceed to `/devforge:plan`), REVISE-SPEC (back to `/devforge:specify` to fix the named conflicting ACs — the translation is confirmed correct), and DISMISS (the human judges the translation wrong; proceed anyway). Because the softness lives in the translation, the report surfaces the full formalization so the human can check THAT before a proven contradiction is treated as real — DISMISS is the escape hatch when the translation is wrong.

**User-invoked, and a fresh report is REQUIRED before `/devforge:plan` (D14, as amended).** `/devforge:spec-check` runs because the USER invoked it (like `/devforge:audit` and `/devforge:grill`) — it NEVER auto-runs, and no `/devforge:specify` run starts it. What is mandatory is that it RAN: `/devforge:plan` blocks until a `spec-check.md` sits beside the resolved spec AND the spec hash that report recorded still matches that spec, and its blocked message names `/devforge:spec-check` for the user to run. **That gate reads PRESENCE and FRESHNESS only, never the verdict** — a REVISE-SPEC report satisfies it exactly as a CONSISTENT one does, because the human owns the disposition. The verdict must never gate: blocking on a recommendation derived from a stochastic formalization would hard-stop a correct specification on every mistranslation, which is why verdict-blocking stays with the DETERMINISTIC forcing-functions family (no stochastic link). Run it as soon as the spec is written; it earns the most on specs with many interacting numeric/threshold, state/enum, or conditional-permission acceptance criteria over shared quantities, where a hidden contradiction is most likely and most costly to discover only after `/devforge:plan` has designed against it.

Usage: `/devforge:spec-check` (auto-resolve the most-recently-modified feature under `specs/` that has a `spec.md`) · `/devforge:spec-check specs/001-auth` or `/devforge:spec-check specs/001-auth/spec.md` (an explicit feature dir or a `spec.md` path inside it).

## Maintainer note

This file lives at `src/commands/spec-check/main.md` in the AIDevTeamForge template repo and is the SSOT for the `/devforge:spec-check` command. Do NOT inject project-specifics — this spec is substituted + emitted into target projects by the build. Helper paths use the installed `.devforge/lib/...` location because that's where they resolve at runtime in the target project. Reference-file paths are written author-relative (`references/<file>.md`); the emitter rewrites them to `.devforge/command-refs/spec-check/<file>.md` at install time.

## Outputs of this command

The files this command writes under the repo are:

- `specs/[feature]/spec-check.md` — the rendered consistency report. Produced by the helper's `render-report` verb in PHASE 4; carries the two-layer surface (how the ACs were read as logic, then the proof over that reading) AND the recommended 3-way disposition. Its header also carries a `**Spec hash**` line — the sha256 of the `spec.md` this run checked, so a later reader can re-hash that file and tell whether the report still describes it — and, when at least one acceptance criterion's subject went unresolved across EVERY formalization pass, an `## UNRESOLVED SUBJECTS` section naming those variables (absent when there are none). Idempotent: re-running `/devforge:spec-check` on the same feature OVERWRITES `spec-check.md` (the helper does an atomic write).
- `specs/[feature]/spec-check-seed.json` — written in PHASE 6 ONLY when the user chooses `Revise spec` at the human gate AND that matches the recommended REVISE-SPEC disposition. Produced by the helper's `write-seed` verb (`source="spec-check"`, `target_stage="spec"`); the structured BACKWARD handoff `/devforge:specify` consumes on re-entry so the re-run is directed at the conflicting ACs, not a repeat. Not written for `Consistent`, `Dismiss`, or a cross-pick (the user picking `Revise spec` when the recommendation was not REVISE-SPEC) — and not written on a clean run, where PHASE 5 raises no gate at all, so there is no pick to match.

**`/devforge:spec-check` is STATELESS** — it writes NO run-state file. It gates on the setup chain + the presence of `spec.md` (PHASE 0), and a re-run simply overwrites `spec-check.md`. File-idempotency is not verdict-determinism: the formalization is a soft LLM step, so the VERDICT can differ run-to-run — the PHASE-2 quorum (D13) is the mitigation, not statelessness.

At the end of PHASE 7, `/devforge:spec-check` WIP-commits its own artifacts — `spec-check.md`, plus `spec-check-seed.json` when PHASE 6 wrote one — via `.devforge/lib/artifact_helper commit-artifacts`. The commit lands in the INSTALL repo only (never the wrapper-mode source/product repo) and is fail-soft (a git failure warns and `/devforge:spec-check` continues — the report is already written). The `[WIP]` commit folds into `/devforge:finalize`'s squash, so the final PR is unchanged.

### Intermediate scratch files (orchestrator-written, helper-consumed) — all under `$WORKDIR`

The helper cannot dispatch agents (a subprocess has no Task tool), so the orchestrator captures each verb's stdout to an intermediate scratch file that the next verb reads (each consuming verb takes a `--<name> <path>` flag, not stdin). All live under `$WORKDIR` (`${TMPDIR:-/tmp}/forge-spec-check`) and are scratch state for one run — the whole directory is removed at the end (the single PHASE-7 `rm -rf`). Because `$WORKDIR` is outside the work tree, the files need no leading dot and no gitignore handling.

- `$WORKDIR/preflight.json` — the `preflight` stdout (the setup-chain / constitution / feature-gate / z3 context block). Written in PHASE 0.
- `$WORKDIR/acs.json` — the `resolve-scope` stdout (`{"acs": [...], "count": N}`, the extracted acceptance criteria). Written in PHASE 1, read by `render-formalize-brief --acs-file`, `consume-ir --acs-file`, and `render-report --acs-file`.
- `$WORKDIR/ir-pass-<i>.json` — the RAW IR JSON returned by the `spec-formalizer` Task on pass `i` (the fenced ```json block extracted from the agent's final message). Written + read per pass in PHASE 2, consumed by `consume-ir --ir-file`.
- `$WORKDIR/ir-canon-<i>.json` — the CANONICAL (parsed + validated) IR for pass `i`, from `consume-ir` stdout, carrying that pass's `citation_errors` list. Written per pass in PHASE 2; in PHASE 4 ALL of them are assembled into `ir-files.json`, and ONE of them becomes the representative IR passed to `render-report --ir-file`.
- `$WORKDIR/solve-pass-<i>.json` — the `solve` stdout for pass `i` (`{"status", "unsat_core"}`). Written per pass in PHASE 2.
- `$WORKDIR/passes.json` — the bare JSON array of the successful passes' solve-results, assembled from the `solve-pass-<i>.json` files. Written in PHASE 3, read by `quorum-core --passes-file`.
- `$WORKDIR/quorum.json` — the `quorum-core` stdout (the D13 verdict + `confirmed_core` + `stability` + `all_cores` + `declared_k`). Written in PHASE 3, read by `render-report --stability-file`.
- `$WORKDIR/solve-final.json` — the synthesized `{"status", "unsat_core"}` the report renders from (derived from the quorum verdict: `confirmed_unsat` → `unsat` + the confirmed core, else `sat` + `[]`). Written in PHASE 4, read by `render-report --solve-file`.
- `$WORKDIR/ir-files.json` — the bare JSON array of the successful passes' canonical IRs — the IR OBJECTS themselves, each one `consume-ir`'s stdout including its `citation_errors` key, NOT their file paths — assembled from the `ir-canon-<i>.json` files. Written in PHASE 4, read by `render-report --ir-files-file`.

## Reference files

- `references/report-format.md` — the report skeleton `render-report` produces (orientation for PHASE 4; the helper owns the actual render).
- `references/formalization-guidance.md` — the worked NL→IR examples the orchestrator injects into the `spec-formalizer` Task prompt in PHASE 2. Read it in full at PHASE 2 and append its content to the rendered brief. The agent's own body (`.claude/agents/spec-formalizer.md`) carries the translation RULES; this reference carries concrete examples that ground them.

## Helper interaction model

Every mechanical step is a normal Bash tool call to `.devforge/lib/spec_check_helper <verb> ...`. Each verb prints JSON (or a rendered block) to stdout. Each consuming verb takes a `--<name> <path>` flag (not stdin), so capture stdout to the named `$WORKDIR/*` scratch file with `>` and pass that path into the next call — the per-phase fences below show the exact redirects. Re-establish `WORKDIR="${TMPDIR:-/tmp}/forge-spec-check"` at the top of every Bash block that touches scratch (the variable does not survive across Bash calls — see PHASE 0). On any non-zero exit, copy the helper's stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), then follow the recovery note for that phase. The helper owns file structure, validation, and atomic writes; the orchestrator owns the `spec-formalizer` dispatch, the verbatim prompt text, user-facing prose, and phase pacing.

## PHASE 0 — Preflight + feature resolution

Cheapest guards first; preflight before any formalization. `/devforge:spec-check` runs only when the user invokes it — nothing starts it automatically; this preflight confirms the setup chain completed and the target feature has a `spec.md`, and that the Z3 solver is installed.

### 0.1 — Resolve the feature directory

Resolve the feature dir from `$ARGUMENTS`:

- When `$ARGUMENTS` names a feature directory (`specs/NNN-<slug>`) or a `spec.md` inside one (e.g. `specs/001-auth/spec.md`), use that feature directory (strip a trailing `spec.md` filename to the `specs/NNN-<slug>` dir).
- When `$ARGUMENTS` is empty, select the `specs/NNN-*` directory whose `spec.md` was modified most recently — the feature most likely just finished `/devforge:specify` (matching how `/devforge:plan` and `/devforge:verify` auto-resolve). The `resolve-scope` verb does NOT auto-detect — it requires a `--feature-dir` or `--spec-file` — so resolve it here:

```bash
newest=$(ls -t specs/[0-9]*/spec.md 2>/dev/null | head -1); [ -n "$newest" ] && dirname "$newest"
```

Carry TWO values forward from the resolved result: `<feature-dir>` — the full path (e.g. `specs/001-auth`), taken by every `--feature-dir` flag and used as the `specs/<feature-dir>/...` artifact-path root; and `<feature>` — the SLUG, the directory's basename (e.g. `001-auth`, from `basename` of that resolved `<feature-dir>` path), taken by `--feature` (the report-header / seed label). Keep the two distinct: `<feature-dir>` always carries the `specs/` prefix, `<feature>` never does. If no `specs/NNN-*` directory has a `spec.md`, tell the user to run `/devforge:specify` first and end the turn.

### 0.2 — Preflight gate

```bash
.devforge/lib/spec_check_helper preflight --workspace-root . --feature-dir <feature-dir> > /tmp/spec-check-preflight.json
```

`preflight` checks, in order (first failure wins): (1) Z3 is importable (`import z3`), (2) the 4-command setup chain (`/devforge:init-forge → /devforge:generate-docs → /devforge:configure → /devforge:constitute`) completed, (3) `constitution.md` is populated (no unpopulated sentinel), and (4) the feature gate — the target `<feature-dir>` has a `spec.md` (NOT `plan.md`; `/devforge:spec-check` runs BEFORE `/devforge:plan`). It ALWAYS writes its JSON context block to stdout BEFORE any gate check, then exits **2** with a user-facing stderr message on the first failing gate. On exit 2, copy the helper's stderr VERBATIM as a fenced code block and end the turn:

- Z3 absent → the stderr carries the clean one-time install instruction (`pip install z3-solver`). `install.sh` does not install Z3 (the install stays stdlib-clean), so installing it is a one-time user step; `/devforge:plan`'s spec-check gate appends the same instruction when the package is missing, so the same message reaches the user from either command.
- Setup chain incomplete → the user runs the named missing setup command first.
- Constitution unpopulated → the user runs `/devforge:constitute`.
- Feature missing `spec.md` → the user runs `/devforge:specify` first.

### 0.3 — Initialize the scratch dir

Establish + clear the scratch working directory:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-spec-check"
rm -rf "$WORKDIR" && mkdir -p "$WORKDIR"
```

**All intermediate scratch for this run lives in `$WORKDIR` (the fixed literal `${TMPDIR:-/tmp}/forge-spec-check`), OUTSIDE the repo.** The literal is `forge-spec-check`, NOT `forge-grill` or `forge-audit` — another command may run concurrently, and a shared workdir would corrupt both runs. The `rm -rf "$WORKDIR" && mkdir -p "$WORKDIR"` clears any stale scratch from a prior crashed run.

**CRITICAL — `$WORKDIR` is a FIXED LITERAL you re-derive in every Bash block; it does NOT persist across calls.** The orchestrator runs each Bash tool call in a FRESH shell, so shell variables (including `$WORKDIR`) do NOT carry from one Bash call to the next. So every Bash block that touches scratch MUST begin by re-establishing `WORKDIR="${TMPDIR:-/tmp}/forge-spec-check"` and then reference `"$WORKDIR/..."`. The literal is identical in every block, so each block reconstructs the same directory.

Now re-capture the preflight context into `$WORKDIR` (the gate already passed in 0.2; this just persists the context to the scratch dir):

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-spec-check"
.devforge/lib/spec_check_helper preflight --workspace-root . --feature-dir <feature-dir> > "$WORKDIR/preflight.json"
```

## PHASE 1 — Resolve scope (extract the ACs)

Extract the feature's acceptance criteria from `spec.md`:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-spec-check"
.devforge/lib/spec_check_helper resolve-scope --feature-dir <feature-dir> > "$WORKDIR/acs.json"
```

`resolve-scope` reads `<feature-dir>/spec.md`, parses its EARS-notation acceptance criteria, and emits `{"acs": [...], "count": N}` to stdout; the `>` redirect captures it to `$WORKDIR/acs.json`. Each AC dict carries at least `id` and `text`. On a non-zero exit — no spec file, or zero acceptance criteria found (exit 2) — copy the helper's stderr VERBATIM and end the turn (a spec with no ACs has nothing to prove consistent).

## PHASE 2 — Quorum formalization loop (fixed K=2)

This is the neurosymbolic core. Because the English→IR formalization is a soft LLM step (D13), run the sub-chain below **a fixed K=2 times**, each pass INDEPENDENT — every pass gets a FRESH `Task` dispatch, which is what makes the quorum meaningful: two independent formalizations that agree on a contradiction give a reproducible verdict; a one-off that appears in only one pass is treated as unstable, not confirmed.

K is fixed at `2` (v1 has no override). For each pass `i` in `1..K`, run these four steps.

### 2.1 — Render the formalization brief

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-spec-check"
.devforge/lib/spec_check_helper render-formalize-brief --acs-file "$WORKDIR/acs.json"
```

`render-formalize-brief` prints the brief TEXT (not JSON) to stdout: the numbered AC list plus the machine OUTPUT CONTRACT (the IR's `variables` / `constraints` / `coverage` shape). Capture that text — it is the first half of the Task prompt.

### 2.2 — Dispatch the `spec-formalizer` agent

Read `references/formalization-guidance.md` in full (installed at `.devforge/command-refs/spec-check/formalization-guidance.md`). Dispatch ONE Task call with `subagent_type: spec-formalizer` and a prompt = the PHASE-2.1 brief text followed by the full content of `formalization-guidance.md` (the worked examples that ground the brief's rules). Instruct the agent to return ONLY the fenced ```json IR block, no prose. Dispatching with `subagent_type: spec-formalizer` already loads the agent's persona (`.claude/agents/spec-formalizer.md`, a read-only agent whose `tools:` allowlist is `Read, Grep, Glob` — it physically cannot edit the spec it translates), so do NOT re-inline the persona; the brief + guidance carry only the per-run instructions on top of it.

Extract the fenced ```json block from the agent's final message and write it to `$WORKDIR/ir-pass-<i>.json`.

### 2.3 — Consume + validate the IR

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-spec-check"
.devforge/lib/spec_check_helper consume-ir --ir-file "$WORKDIR/ir-pass-<i>.json" --acs-file "$WORKDIR/acs.json" --workspace-root . > "$WORKDIR/ir-canon-<i>.json"
```

`consume-ir` parses the raw IR and cross-validates it against the ACs (every atom references a declared variable, coverage covers every AC exactly once, atom values match their variable's sort). `--workspace-root .` additionally resolves every `arm="code"` subject-resolution citation the formalizer claimed against the repo and records each miss in the canonical IR's `citation_errors` list — a citation miss is neither a shape problem nor an inconsistency with the ACs, so it leaves this verb's exit code at 0, consumes NONE of the retry budget below, and needs no recovery arm here; it simply rides forward in the IR for PHASE 4 to fold into the report. On success it prints the canonical IR to stdout, captured to `$WORKDIR/ir-canon-<i>.json`. Two failure modes, both meaning "re-prompt the formalizer for THIS pass":

- **exit 2** — the IR is shape-malformed (bad JSON, missing key). Re-dispatch the formalizer for this pass with the helper's stderr appended to the prompt so it can fix the syntax.
- **exit 3** — the IR parses but is logically inconsistent with the ACs (undeclared variable, missing coverage entry, sort mismatch). Re-dispatch with the helper's stderr (the validation errors) appended so it can fix the translation.

Bound the retry to a small cap — at most 2 re-dispatches for this pass. If it still fails after the cap, record this pass as a formalization FAILURE (it produced no valid IR), note it, and continue to the next pass — a failed pass contributes no solve-result to the quorum.

### 2.4 — Solve

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-spec-check"
.devforge/lib/spec_check_helper solve --ir-file "$WORKDIR/ir-canon-<i>.json" > "$WORKDIR/solve-pass-<i>.json"
```

`solve` runs the deterministic Z3 solver over the canonical IR — builds the sorts/variables, asserts each `ac_id`-labeled constraint, checks satisfiability, and maps `unsat_core()` to the conflicting `ac_id` list — printing `{"status": "sat"|"unsat"|"unknown", "unsat_core": [...]}` to stdout, captured to `$WORKDIR/solve-pass-<i>.json`. On a non-zero exit, copy the helper's stderr VERBATIM and end the turn.

## PHASE 3 — Quorum analysis

Assemble the successful passes' solve-results into one bare JSON array, then analyze the quorum:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-spec-check"
python3 -c "import json,glob; print(json.dumps([json.load(open(p)) for p in sorted(glob.glob('$WORKDIR/solve-pass-*.json'))]))" > "$WORKDIR/passes.json"
.devforge/lib/spec_check_helper quorum-core --passes-file "$WORKDIR/passes.json" --k 2 > "$WORKDIR/quorum.json"
```

`quorum-core` analyzes the k solve-results for cross-pass reproducibility and prints `{"verdict", "confirmed_core", "stability", "all_cores", "declared_k"}` to stdout, captured to `$WORKDIR/quorum.json`. The verdict is one of:

- `confirmed_unsat` — the SAME conflicting AC set (by `ac_id`) reproduced across a strict majority of passes; `confirmed_core` names it.
- `unstable` — at least one pass was `unsat` but no single conflicting set reached a majority (the passes disagree); `confirmed_core` is `null`. Per the D13 cry-wolf rule this is NOT a REVISE-SPEC recommendation — a non-reproducing one-off is surfaced as unstable, not confirmed.
- `consistent` — no pass proved a contradiction.

Pass `--k 2` (the declared pass count). If a PHASE-2 pass failed and exactly one solve-result reached `passes.json`, `quorum-core` emits a NON-FATAL stderr warning that the declared `--k` does not match the actual pass count and continues (exit 0) — carry that warning into your user-facing summary; it does not stop the run. But if BOTH passes failed (every formalization pass hit its PHASE-2.3 retry cap), `passes.json` is the empty array `[]` and `quorum-core` exits **2** ("--passes-file must decode to a non-empty JSON array…") — this run produced no solvable IR at all. On that exit 2, copy the helper's stderr VERBATIM into your next user-facing message as a fenced code block and END the turn; the recovery is to re-run `/devforge:spec-check` for a fresh formalization attempt.

## PHASE 4 — Render report

Synthesize the report's solve-result from the quorum verdict, then render:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-spec-check"
python3 -c "import json; q=json.load(open('$WORKDIR/quorum.json')); print(json.dumps({'status':'unsat','unsat_core':q.get('confirmed_core') or []} if q.get('verdict')=='confirmed_unsat' else {'status':'sat','unsat_core':[]}))" > "$WORKDIR/solve-final.json"
```

This mirrors the helper's own quorum→solve-result synthesis: `confirmed_unsat` → `unsat` + the confirmed core; `unstable` and `consistent` both → `sat` + `[]` (the D13 cry-wolf rule — an unstable one-off must not recommend REVISE-SPEC; the instability is surfaced as a report caveat via the stability file, never folded into the disposition).

Assemble EVERY successful pass's canonical IR into one bare JSON array, so the report speaks for the whole quorum's subject resolution rather than for the representative pass alone:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-spec-check"
python3 -c "
import json, glob
out = []
for p in sorted(glob.glob('$WORKDIR/ir-canon-*.json')):
    try:
        out.append(json.load(open(p)))
    except ValueError:
        pass
print(json.dumps(out))" > "$WORKDIR/ir-files.json"
```

The array holds the IR OBJECTS, not their paths. The `try`/`except` skips an `ir-canon-<i>.json` left EMPTY by a pass that exhausted its PHASE-2.3 retry cap — the `>` redirect creates that file even when `consume-ir` exits non-zero, so a failed pass leaves a zero-byte file behind that must not abort the assembly. At least one entry always survives: reaching PHASE 4 means PHASE 3's `quorum-core` accepted a non-empty `passes.json`, and a pass only reaches `solve` after its `consume-ir` succeeded.

Pick the REPRESENTATIVE IR for the report — for `confirmed_unsat`, the `ir-canon-<i>.json` of the FIRST pass whose `solve-pass-<i>.json` core equals `confirmed_core` (so the Contradiction section renders the constraints that produced the confirmed core); for `unstable` / `consistent`, pass 1's `ir-canon-1.json`:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-spec-check"
python3 -c "import json,glob,os; q=json.load(open('$WORKDIR/quorum.json')); core=q.get('confirmed_core'); rep=os.path.join('$WORKDIR','ir-canon-1.json')
if core is not None:
    t=sorted(core)
    for p in sorted(glob.glob('$WORKDIR/solve-pass-*.json')):
        if sorted(json.load(open(p)).get('unsat_core') or [])==t:
            i=os.path.basename(p).split('-')[-1].split('.')[0]; rep=os.path.join('$WORKDIR','ir-canon-%s.json'%i); break
print(rep)"
```

Capture the printed path as `<representative-ir>`, then render the report:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-spec-check"
.devforge/lib/spec_check_helper render-report --ir-file <representative-ir> --solve-file "$WORKDIR/solve-final.json" --acs-file "$WORKDIR/acs.json" --feature <feature> --feature-dir <feature-dir> --stability-file "$WORKDIR/quorum.json" --ir-files-file "$WORKDIR/ir-files.json" --spec-file <feature-dir>/spec.md
```

`render-report` reads the representative IR, the synthesized solve-result, the ACs, the quorum stability, every pass's IR, and the spec file, then renders the full report (skeleton documented in `references/report-format.md`) and writes it to `<feature-dir>/spec-check.md` via an atomic write, OVERWRITING any prior `spec-check.md` (idempotent). It computes the date itself (`--date` is not a flag). The `--stability-file` adds the "contradiction core reproduced in j/k passes" line for a stable verdict, or the prominent "Formalization unstable" caveat for an `unstable` verdict. `--ir-files-file` merges the passes' subject resolutions — a variable resolved in ANY pass counts as resolved — and renders the `## UNRESOLVED SUBJECTS` section naming every variable NO pass resolved (the section is absent when there are none). `--spec-file` content-hashes the spec into the report's `**Spec hash**` header line; it is `<feature-dir>/spec.md`, the same file PHASE 1 extracted the ACs from.

Stdout is a JSON ack `{"report_path", "recommended_disposition", "unsat_core", "status", "clean", "unresolved_subject_count", "citation_failure_count", "spec_sha256"}`. Read `clean` from that stdout — it is the signal PHASE 5 branches on, and the helper computes it: `true` ONLY when the quorum verdict was `consistent` AND the cross-pass merge found zero unresolved subjects AND zero citation failures; `false` when any of the three fails; `null` when the verb could not compute it because `--stability-file` or `--ir-files-file` was absent. The invocation above passes both flags, so a `null` should not occur — if one does, treat it as NOT clean; an uncomputed signal is never a clean one. `unresolved_subject_count` and `citation_failure_count` report two of the three inputs to that signal (the third is the quorum verdict itself) — quote them when you tell the user why the gate fired. Carry `recommended_disposition` and `clean` forward to PHASE 5, and carry the ack's `report_path` forward to PHASE 5 and PHASE 7 (it is the exact `<feature-dir>/spec-check.md` path to surface and to commit). On a non-zero exit, copy the helper's stderr VERBATIM and end the turn.

## PHASE 5 — Surface + human gate (the gate fires only on a non-clean result)

Branch on `clean` from the PHASE-4 ack. Do NOT re-derive it by reading the report text: one of the three inputs is not rendered at all — a citation failure in a pass whose variable a DIFFERENT pass resolved fails `clean` without producing any `## UNRESOLVED SUBJECTS` entry — so a report that looks clean can still carry a `false`.

### 5.1 — Clean arm (`"clean": true`)

Nothing has been alleged, so there is nothing for the human to confirm: fire NO AskUserQuestion, capture NO pick, and proceed to PHASE 6. The report is still rendered, still written to `<feature-dir>/spec-check.md`, and still WIP-committed in PHASE 7 — an accepted result is a recorded one.

Tell the user, in your next message: the report path (the ack's `report_path`); the report's Coverage headline, quoting the bold `**Checked N of M acceptance criteria**` prefix verbatim; and one sentence stating that no contradiction reproduced across the formalization passes and that every acceptance criterion's subject resolved — `unresolved_subject_count` 0 and `citation_failure_count` 0 in the ack — so `/devforge:spec-check` accepted the result without asking. Take the resolution claim from those two ack fields, NEVER from the headline's parenthetical: the parenthetical counts unresolved subjects in the REPRESENTATIVE pass alone, while `clean` is computed over the merge of every pass. If that parenthetical names unresolved subjects even though `clean` is `true`, say that the count reflects only the representative pass and a later pass resolved those subjects — that is why no `## UNRESOLVED SUBJECTS` section appears — and do NOT present it as the cross-pass result. Keep the scope boundary in view while you say it: a clean result means the ACs did not contradict EACH OTHER, never that they say what you MEANT.

### 5.2 — Non-clean arm (`"clean": false` or `null`)

Something has been alleged — a reproduced contradiction, an unresolved subject, a failed citation, or a signal the helper could not compute — so the human decides. Treat `null` exactly as `false`.

The disposition is a RECOMMENDATION; the human makes the final call, and the thing the human is asked to check is the TRANSLATION, not the proof. First display the rendered report so the human can check it: copy the contents of `<feature-dir>/spec-check.md` (the ack's `report_path` from PHASE 4) VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase) — the `## How your ACs were read as logic` section IS the human's check against a mistranslation. When the report carries an `## UNRESOLVED SUBJECTS` section, name it explicitly in your surrounding prose: those ACs were never formalized, so nothing the solver reports covers them.

Then capture the user's choice via AskUserQuestion so the next step is explicit:

> `/devforge:spec-check` recommends **<recommended_disposition>** for this spec — check the TRANSLATION shown above, not the proof. What do you want to do?

Options (2–4; AskUserQuestion auto-injects "Other"):

- `Consistent` — the ACs are mutually consistent (or nothing formalizable contradicted); proceed to `/devforge:plan`.
- `Revise spec` — the translation is correct and the contradiction is real; re-run `/devforge:specify` to fix the named conflicting ACs.
- `Dismiss` — the translation is WRONG (you misread an AC); this is a false positive, proceed to `/devforge:plan` anyway.

Frame the choice as "check the TRANSLATION, not the proof": `Revise spec` means "the reading is right and the ACs genuinely conflict"; `Dismiss` means "the reading is wrong, so the proof does not apply." If the quorum verdict was `unstable`, the recommendation is CONSISTENT (not REVISE-SPEC) — present the instability honestly (a contradiction appeared in some but not a majority of passes; it is not confirmed) rather than steering the user toward `Revise spec`. The same honesty applies when this arm fired on unresolved subjects or citation failures alone: the recommendation is still CONSISTENT, because what is not clean is the COVERAGE, not the proof.

Carry the user's pick forward to PHASE 6.

## PHASE 6 — Verdict-gated seed (matching REVISE-SPEC pick only)

When PHASE 5 captured NO pick — the clean arm, where no gate was raised — write NO seed and go straight to PHASE 7. A seed exists to redirect a `/devforge:specify` re-run at a confirmed problem, and a clean run confirmed none; the enumeration below is over picks, and on that arm there is no pick to enumerate.

Otherwise the user made a pick. Write the backward re-entry seed ONLY when that PHASE-5 pick is `Revise spec` AND the recommended disposition was REVISE-SPEC. On any other pick — `Consistent`, `Dismiss`, or a cross-pick (`Revise spec` when the recommendation was NOT REVISE-SPEC) — write NO seed and skip to PHASE 7. This verdict-gating stops an overridden or false-positive seed from becoming an orphan a later `/devforge:specify` run silently obeys.

In the matching arm, compose the seed inputs from the report's confirmed contradiction and write the seed:

```bash
.devforge/lib/spec_check_helper write-seed --feature <feature> --feature-dir <feature-dir> --prior-conclusion "<the conflicting ACs as authored>" --invalidating-evidence "<the proven contradiction — the unsat-core ac_ids plus the logic reading that derives it>" --must-satisfy "resolve the conflict between <named ACs>" --provenance "<feature-dir>/spec-check.md"
```

`write-seed` builds a `ReEntrySeed` (`source="spec-check"`, `target_stage="spec"`, both fixed internally) and writes `<feature-dir>/spec-check-seed.json` via an atomic write. `--prior-conclusion`, `--invalidating-evidence`, `--must-satisfy`, and `--provenance` are all REQUIRED and non-empty (the schema rejects an empty value with exit 2); `--cycle-count` (int ≥ 1) and `--carried-findings` (a JSON array string) default to `1` and `[]` and need not be passed for a first spec-check. Stdout is a JSON ack `{"seed_path"}`. On a non-zero exit, copy the helper's stderr VERBATIM and end the turn. `/devforge:specify` detects and consumes this `spec-check-seed.json` (`target_stage="spec"`) on re-entry so the re-run is directed at the confirmed conflicting ACs, not a repeat.

## PHASE 7 — Commit artifacts + next step

WIP-commit `/devforge:spec-check`'s own artifacts so the work is git-safe at this step. Run this UNCONDITIONALLY (every `/devforge:spec-check` run reaches here with a written `spec-check.md`). Include `spec-check-seed.json` in the `--paths` array ONLY when PHASE 6 wrote it (a matching `Revise spec` pick); omit it otherwise:

```bash
.devforge/lib/artifact_helper commit-artifacts --paths '["<feature-dir>/spec-check.md"]' --label 'spec-check: <feature>'
```

Substitute `<feature-dir>` with the resolved feature-dir path (e.g. `specs/001-auth`) and `<feature>` with the slug (e.g. `001-auth`); when a seed was written, use `--paths '["<feature-dir>/spec-check.md", "<feature-dir>/spec-check-seed.json"]'`. `commit-artifacts` stages ONLY the named paths and makes a `[WIP] spec-check: <feature>` commit in the INSTALL repo (never the wrapper-mode source/product repo). It is FAIL-SOFT: a git staging or commit failure warns on stderr and exits 1 (non-fatal — the report is already written, so note the warning and CONTINUE; do NOT end the turn); "nothing to commit" exits 0 silently as a benign no-op. The `[WIP]` commit folds into `/devforge:finalize`'s squash, leaving the final PR unchanged.

Sweep the scratch directory — `render-report` was the last reader of the scratch chain, so nothing else needs it:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-spec-check"
rm -rf "$WORKDIR"
```

Then point the user at the next step:

- No PHASE-5 pick (the clean arm), or a `Consistent` / `Dismiss` pick → the next command is `/devforge:plan`.
- `Revise spec` → the next command is `/devforge:specify`; the emitted `spec-check-seed.json` directs the re-run at the conflicting ACs.

## Important rules

1. **User-invoked, never auto-invoked — and a fresh report is required before `/devforge:plan`** — `/devforge:spec-check` runs only when the user invokes it (like `/devforge:audit` and `/devforge:grill`); it never auto-runs, and no `/devforge:specify` run starts it. What is mandatory is that it RAN: `/devforge:plan` blocks until a `spec-check.md` sits beside the resolved spec and the spec hash it recorded still matches, and names this command for the user to run. That gate reads presence and freshness ONLY — a REVISE-SPEC report satisfies it exactly as a CONSISTENT one does. The verdict never gates: verdict-blocking belongs to the deterministic forcing-functions family, never to a recommendation derived from a stochastic formalization.
2. **Consistency prover, not a mind-reader** — it checks whether ACs contradict EACH OTHER, not whether they are what you MEANT; a single coherent-but-wrong AC passes. Intent-correctness stays with the soft-LLM stages (`/devforge:research`, `/devforge:grill`, human gates).
3. **Check the translation, not the proof** — the Z3 proof is hard, but the English→logic translation is soft. Whenever there is something to decide, PHASE 5 surfaces the full formalization so the human confirms the reading before a contradiction is treated as real; `Dismiss` is the escape when the reading is wrong.
4. **Quorum, not a single pass** — PHASE 2 formalizes a fixed 2 times and only a majority-reproduced contradiction is CONFIRMED. The honest claim is "a deterministic proof over a human-checked, quorum-stable formalization" — never a bare "deterministic proof of your spec."
5. **Honest permission boundary** — strong on numeric/state/enum invariants; a conditional-permission clash is caught ONLY when a permitting case is asserted reachable (an `assertion`, not a pure rule). Never claim "permission/role logic" is caught in general.
6. **The disposition is a RECOMMENDATION, and the gate fires only when it is not clean** — `/devforge:spec-check` recommends CONSISTENT / REVISE-SPEC / DISMISS, and the human owns every call the run raises. PHASE 5 raises one only when the PHASE-4 ack's `clean` is not `true`; a clean run is accepted without a question, and the report is written and committed either way. The backward re-entry seed is written ONLY on a matching `Revise spec` pick (PHASE 6), so a clean run — having no pick — never writes one.
7. **Read-only on the spec** — no modification of `spec.md`. `/devforge:spec-check` does WIP-commit its OWN artifacts (`spec-check.md`, and `spec-check-seed.json` when written) via `artifact_helper commit-artifacts` — install-repo-only, fail-soft `[WIP]` commits that fold into `/devforge:finalize`'s squash; it never commits source or modifies the spec.
8. **Cleanup is last** — all intermediate scratch lives in `$WORKDIR` (`${TMPDIR:-/tmp}/forge-spec-check`), outside the repo, and is swept by the single `rm -rf "$WORKDIR"` at the end of PHASE 7, never mid-run.
