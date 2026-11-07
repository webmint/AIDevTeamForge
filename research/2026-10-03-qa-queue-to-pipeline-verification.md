# Research: Replacing the QA queue with pipeline verification

**Date**: 2026-10-03
**Subject**: A team wants to remove the QA bottleneck (simple tickets wait one to two days for a manual check) by making e2e tests mandatory, letting an LLM verify locally and on the branch URL, and leaving the final human look to the product manager who wrote or read the ticket. This note assesses that intent, records the remarks, and proposes a process shape and a ticket form.
**Status**: Process note for a stakeholder discussion. Not a plan, nothing ratified. Companion to `2026-10-03-enterprise-gates-plain-language.md`.
**Guard**: no consumer project, team, path, package or spec number is named. Observations from consumer installations are described generically.

---

## 1. What the QA step actually does today

In the team under discussion the dedicated QA step is an acceptance check at ticket level: read the ticket, open the browser, confirm the change is done as described, or that the reported defect no longer reproduces. There is no regression pass, no exploratory testing, no e2e authorship, and QA will not write e2e tests. Defect absence currently rests on careful developers and on a product manager who notices business-logic slips. QA also produces its own written artifacts that nobody downstream consumes.

That matters for the comparison. The question is not "LLM versus a full QA function" but "LLM versus a shallow check delivered two days late".

## 2. The intent under assessment

1. e2e tests are mandatory for every ticket, including edge cases.
2. An LLM verifies the result locally and on the deployed branch URL.
3. No dedicated QA step; the product manager who wrote or read the ticket looks it over.

## 3. Assessment

**Direction right, conclusion overstated.** Shifting verification left and automating the acceptance check is correct. "No QA needed" is the wrong headline; what is removable is the QA *queue* for low-risk tickets, not the verification *function*. Against the actual baseline, the LLM-driven process is at least as reliable, for concrete reasons:

- What QA does today is exactly what a pipeline AC verifier does: acceptance criteria exercised against a live URL. The verifier does it the same day, leaves evidence per step, and does not skip items.
- Regression and exploratory testing do not exist today, so nothing is lost there. The process adds a verification layer where there was effectively none.
- Nobody writes e2e tests today; the pipeline will. An imperfect suite beats none, provided every new test fails on the pre-change code.
- The two controls that actually hold today, careful developers and the product manager's business-logic eye, both stay.

**What the current step provides that must be preserved.** Occasionally a second human reads the ticket differently and catches an ambiguity. An LLM verifier in the same chain as the LLM implementer will not: when a ticket is ambiguous, code and tests from the same reading agree and go green. The fix is to move the human minute from after implementation to before it (section 5).

## 4. Remarks

1. **Shared blind spot.** Tests generated from the ticket encode the model's reading of the ticket. Edge cases it invents are the ones it thought of. Minimum: tests authored by a different agent or model with an adversarial brief, and a negative control: each new test must fail on the code before the change.
2. **Foundation before mandate.** Consumer installations show baselines with failing and flaky tests and at least one test that checks its own copy of the subject. A mandatory e2e gate on that foundation produces red merges for no reason, and the team routes around the gate. Clear the test debt first; the pipeline itself can do it as a dedicated spec.
3. **The test pyramid still applies.** Logic in unit and integration tests; e2e only for the user path and the chartered edge cases, a few per ticket, not dozens.
4. **Evidence, not verdicts.** An LLM verifier is good at running a given AC list against a URL and collecting evidence; poor at exploratory testing, cross-feature regression, role and data permutations, visual judgment, accessibility. Consumer installations recorded three review agents unanimously approving a wrong construct and a gate agent arguing a failed criterion into PASS. So the verifier emits per-AC status, screenshots, console and network errors, and a short recording of the walkthrough; the verdict is computed from evidence by fixed rules.
5. **The product manager's step must be explicit and recorded.** A product manager answers "is this what I asked for", not "did this break something else" or "does it work for the other role with the other currency". A thirty-second nod presented as a gate is a stated human gate that does not exist, the thing auditors reject first. Keep the step small and formal: a checklist from the ACs, links to evidence, a one-minute recording, a recorded approval.
6. **Suite ownership.** A mandatory e2e suite grows; flaky tests need quarantine, test data needs an owner, CI runtime needs a budget. In this team the owner is the tech lead or the developer who holds the repository, not QA. Flake quarantine and debt cleanup are pipeline work.
7. **Escape rate is mandatory from day one.** If nobody counts defects found after merge today, nothing can be compared after the change, and every later incident will be blamed on the new process.

**A new risk the old process did not have.** Everyone understands the current check as shallow and behaves accordingly. The pipeline process looks rigorous: reports, tables, green marks. It earns trust the verification may not deserve, and people stop looking. Remedies: the verdict is computed from evidence by rules, never written as prose; the escape rate is counted from the first pilot ticket.

## 5. Recommended process shape

Risk tier is decided by rules (which directories, domains and roles a change touches), never by model judgment.

```
ticket (form, section 6)
→ ACs + test charter generated; product manager approves the list (5 min, async)
→ implementation with unit/integration tests; a few e2e for the user path
   and the chartered edge cases; each new test shown red on pre-change code
→ CI builds the branch, deploys the preview URL
→ verifier runs the charter against the URL; evidence pack: per-AC status,
   screenshots, console/network errors, one-minute recording
→ human step by tier:
     low    : product manager acceptance from checklist + recording
     medium : asynchronous review of the evidence pack (15–30 min)
     high   : full exploratory session by a human
→ approvals and checks recorded on the PR → squash-merge on the host
```

The human approval before implementation is the real control: it catches the interpretation, which is where the shared blind spot lives. After merge the human looks at a recording, not at a browser.

Low tier: copy changes, UI without logic, configuration. High tier: pricing, orders, permissions, data migrations. The medium tier is where a remaining QA person, if any, spends fifteen minutes on evidence instead of two days on a branch.

## 6. The ticket form

Tickets will be written to a form and are required to be unambiguous, because they become the base the pipeline works from. Two things to say plainly to the people writing them.

**A rule "be unambiguous" does not enforce itself.** What enforces: a form the pipeline can lint, plus a recorded step where residual ambiguity is removed by questions before work starts. The base for the pipeline is then the ticket together with the answers.

**What the form can check, and what only the confirmation step catches.**

- Checkable: every criterion names a role, a starting state, an action and an observable outcome; no "correctly", "properly", "as expected"; roles and data variants are listed; out-of-scope is present; a defect ticket has steps, expected, actual, environment, role.
- Not checkable by form: whether the author meant *this*. The only working mechanism is the model restating the ticket as ACs and edge cases and the author confirming or correcting. That is the five-minute step above, and it turns the ticket into a contract.

**Minimal form.**

1. Who and why: the user role and the business outcome in one sentence.
2. Acceptance criteria, one line each: "when role X in state Y does Z, the system shows or does W".
3. Roles and data: for whom exactly this must work; user types, countries, currencies, empty and boundary values. "Only role X" is also unambiguous.
4. Known edge cases: what the author has seen or fears; the model adds more, the author confirms.
5. Out of scope: what must not be touched.
6. For defects additionally: reproduction steps, expected, actual, environment, role, data reference.

**Two traps to name up front.** Unambiguous does not mean long; half a page with five criteria beats two pages of prose. And a ticket is not silently edited after work starts: a changed criterion is a new version that passes the same confirmation step. (Implementation detail in tickets is not an issue for this team; tickets describe outcomes.)

**Forge 2.0 already carries the matching surfaces**, so the form should feed them rather than duplicate them: a pure ticket-capture lane, spec authoring with EARS-validated ACs and mandatory clarifying questions, a spec consistency prover, an adversarial design review, a scope rule that tracks what a change covers, and in-place spec revision. A ticket does not need to be perfect; it needs to be sufficient for the spec stage to ask few questions rather than many.

**A measurable side effect.** The number of clarifying questions the spec stage asks per ticket is an objective ticket-quality metric and should trend down.

## 7. How to phrase it for stakeholders

Not "QA is no longer needed" but: **"we replace a two-day shallow check with a same-day deeper check that leaves evidence, and we move human control of business logic from the end of the process to its start."** True, measurable, and it does not promise more than it delivers.

Metrics for the slide:

| Metric | Why |
|---|---|
| Lead time from "dev done" to merged | the bottleneck being removed |
| Human touch time per ticket | what the pipeline saves |
| Defects found after merge, before and after | the only honest safety signal |
| Flaky-test share | foundation health |
| False-halt share | gate precision |
| Clarifying questions per ticket | ticket quality trend |

Pilot: one month, low tier only. Expand to the medium tier if the escape rate does not rise.

## 8. Prerequisites, in order

1. Fix or quarantine the failing and flaky tests in the baseline.
2. A branch preview environment with reachable test data.
3. The verifier runs against the branch URL, not a local build, because the URL's build is what merges.
4. The product manager's approval of the AC list as a recorded step.
5. The post-merge defect counter running from the first pilot ticket.

Two things to check before presenting: whether any contract requires an independent QA sign-off, which a product-manager approval does not replace; and what share of tickets is genuinely low tier, because the queue saving is proportional to it.

## 9. Relation to the enterprise gates note

The product manager's recorded approval is a human checkpoint in the sense of that note's section 3; the verifier's evidence pack is its advisory and mechanical layers; the branch-URL run is the single server-side run per feature of section 1; the escape rate and false-halt share feed the gate-health metrics of sections 4 and 5.
