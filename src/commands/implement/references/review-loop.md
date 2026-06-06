# Autonomous review loop (`/implement` PHASE 6)

This reference defines the bounded autonomous code-review loop run in PHASE 6 of `main.md`. The loop mirrors the framework's own engineer→reviewer discipline: NO human sits between rounds. It converges the touched code to a clean verdict AND records each judgment-level call it made on the user's behalf as a structured decision item, which PHASE 7 Stage A surfaces one at a time. Most tasks record zero decision items — the loop clears reviewer findings mechanically and the hard gate is just the Stage B code read.

## The loop

1. Invoke `code-reviewer` (consumer `.claude/agents/code-reviewer.md`) via the Task tool with the `touched_files`, the constitution, and the task body. It returns a markdown verdict carrying a `### Verdict:` line.
2. Parse the verdict via `implement_helper review-loop-step --iteration N` (markdown on stdin or via `--verdict-file <path>`). The helper emits `{clean, escalate, iteration, verdict}`.
3. Branch:
   - `clean: true` → exit the loop; carry any warnings into Stage B.
   - `clean: false`, `escalate: false` → relaunch the implementing agent with the findings, re-review, re-call `review-loop-step` with `--iteration` incremented.
   - `clean: false`, `escalate: true` → exit the loop; record a `could-not-converge` decision item.

## Verdict → clean/escalate mapping

The helper (`_implement/_cmds_review_loop.py`) owns the mapping; this is its observable behavior:

- `### Verdict: APPROVE` → `clean: true`. An `APPROVE` with a parenthetical note (e.g. `APPROVE (with warnings)`) still parses as `APPROVE` → `clean: true`; the warnings are carried into Stage B, not blocked on.
- `### Verdict: REQUEST CHANGES` → `clean: false`.
- `### Verdict: BLOCK` → `clean: false`.
- The unfilled template line `### Verdict: APPROVE / REQUEST CHANGES / BLOCK` (or any slash-joined mix of the tokens), or a missing `### Verdict:` line → parse error (helper exit 2). Re-invoke `code-reviewer` for a properly-formed verdict; do not treat a parse error as a verdict.

`escalate` is `true` when the iteration count `N` passed to the helper is `>= 3` (the helper-owned `REVIEW_LOOP_CAP`, mirroring the PHASE 5 self-repair cap). The orchestrator cannot bypass the cap — the helper computes `escalate` from the counter it is handed.

## Mechanical vs judgment classification

During each repair leg, before relaunching the agent, classify what you (the orchestrator) are asking the agent to change to clear a reviewer finding:

- **Mechanical** — resolves silently, NOT recorded. The fix is fully determined by the finding with no shape choice: a missing docstring/JSDoc, an in-scope named type fix, a null guard the reviewer named, a lint/formatting fix, removing a left-behind debug artifact. There is one correct way to clear it.
- **Judgment** — recorded as a decision item. The fix changes the *shape* of the solution and a reasonable engineer could choose differently: a scope-creep call (include this or defer it), an abstraction/module-boundary choice, a constitution-rule interpretation where more than one reading is defensible, a contract change. These are calls the loop made on the user's behalf.

## Bias-toward-recording tie-breaker

When you are unsure whether a cleared finding was mechanical or a judgment call, **record it as a decision item.** A surplus decision question costs the user one click in Stage A; a missed one silently lands a contested decision the user never saw. The asymmetry favors recording.

## Decision-item shape

Each recorded judgment decision is a structured item:

- `finding` — the reviewer's objection, in one line (what was flagged).
- `agent_resolution` — what the loop did to clear it (becomes Stage A option 1, marked `(recommended)`).
- `alternative` — the named alternative the loop did NOT take (becomes Stage A option 2).

A `could-not-converge` escalation is recorded as its own item carrying the reviewer's unresolved objection text; Stage A surfaces it with the options `accept anyway / send back with direction / skip / stop` (per `main.md` PHASE 7 Stage A).

## The cap

The loop is bounded at 3 rounds (helper-owned `REVIEW_LOOP_CAP = 3`). At the cap, the loop stops relaunching and escalates: it records the `could-not-converge` item and exits to PHASE 7. The cap exists so the loop cannot spin indefinitely on a finding the agent and reviewer disagree on — that disagreement becomes a user decision, not an infinite loop.
