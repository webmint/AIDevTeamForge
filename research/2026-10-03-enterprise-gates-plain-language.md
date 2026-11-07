# Research: The five enterprise gaps, explained from the operator's chair

**Date**: 2026-10-03
**Subject**: Plans 57–61 (`ENTERPRISE-READINESS-ROADMAP.md`) explained in plain language, each from the point of view of an operator sitting at a terminal and driving Forge, on the example of one command, with a rough time-and-money estimate.
**Status**: Explanatory note, not a plan. Nothing here is ratified. Plan 57's text may be stale; section 1 describes the general mechanism, not that plan's current wording.
**Assumed deployment**: corporate, **standalone mode** (Forge lives in the product repo; wrapper mode is out of scope). Team flow: push feature branch → CI builds → preview URL → QA tests on the URL → approvals from other developers and QA → merge to the default branch.
**Guard**: this note names no consumer project, path, package or spec number. Examples from consumer installations are described generically.

---

## 0. How the five fit together

The roadmap orders them 59 → 61 → 57 → 58 → 60, and the order is the argument:

1. **Honest framing first** (59): say precisely what the machine decides, what the model advises, and what a human decides.
2. **Precise gates with a legal exit** (61): a gate that halts on correct work gets routed around; a gate with no exit is operationally unacceptable.
3. **Only then move gates to the server** (57): a merge-blocking gate with a false-halt rate above zero stops the release train.
4. **Evidence from the server and from bypasses lands in an immutable trail** (58).
5. **Owners for all of it** (60).

In one sentence each:

| # | Gap | One sentence |
|---|---|---|
| 1 | Server-side CI enforcement | The checks the agent runs on its own machine are run again by a machine nobody at the keyboard controls, and the merge button depends on that machine's verdict. |
| 2 | Compliance audit trail | Proof that every control ran on every merged change, stored where nobody can edit it afterwards and where it survives branch deletion. |
| 3 | LLM-verdict reproducibility | Same evidence, same verdict, today and in six months; and the docs say honestly which layer is machine, model, or human. |
| 4 | Gate governance at scale | Every gate has a class, an owner and a change log; changing a gate goes through the same process as changing code. |
| 5 | False-halt hardening + audited bypass | A gate halts only when something is really wrong; when it is wrong itself, there is a recorded way past it. |

---

## 1. Server-side CI enforcement

### What it is

Today every gate runs inside the agent's own loop: the agent runs the type-check, reads the result, decides what to do next, and reports. Everything the operator sees is the agent's account of its own checks. Consumer installations have recorded how that ends: a cached build reported as success, a tool proxy rewriting command output, a gate agent arguing that a failed criterion "was only cited for its exit code". Server-side enforcement means the same checks run on a CI server on push, the result is posted as a status check, and the merge is blocked without a green check. The agent can neither persuade the server nor skip the step.

### Operator view, on `/implement` for one task

**Today.** The operator types the command. The agent edits code, runs type-check, lint and build locally, self-repairs up to three times, passes a code-review agent, makes a WIP commit and prints "task complete, all gates green".

**With enforcement.** Same first steps. After the WIP commit the branch is pushed. CI runs a fixed script: install, build, type-check, lint, tests, plus Forge's mechanical gates (AC coverage, task contracts). The result appears as a status next to the commit with a link to the log. The command does not say "complete" until the status is green. On red, the agent receives the server log as input, not its own local output. At the end of the feature the PR can be merged only with the required check green; the button is grey for everyone, admins included if so configured. The only way past is an explicit, recorded bypass (section 5).

What changes in the chair:

- Waiting time per task grows by the CI duration.
- "Done" cites a link to a CI run, not the agent's words.
- When the server is red and local was green, the operator learns something real: environment drift, a cache, a tool artifact.
- Nobody, including an operator in a hurry, can skip it.

### Wrapper vs standalone

Enforcement requires owning the repo's branch protection. In wrapper mode Forge does not own the product repo, so the best it can do is an advisory check in the install repo. In standalone mode the required check sits on the product PR and the gate is unbypassable. This note assumes standalone.

### Cadence: running CI on every commit is overkill

The team flow already has the three things that matter: a server build, a human QA pass on a deployed URL, and human approvals. The only question is where one independent check sits between "the agent says done" and "humans spend their time".

Why per-commit is harmful here: WIP commits disappear at squash, so verifying intermediate states that will not exist is pointless; a pipeline that couples verification with deployment makes a per-commit deploy wasteful and noisy for QA; a 10–15 minute wait per task kills the agent loop.

| Tier | Where | Checks | Duration | Typical status |
|---|---|---|---|---|
| Per task | local, in the agent | type-check, lint, build | seconds to minutes | exists (Forge) |
| Per push | server, light job | type-check, lint, unit tests, no deploy | 3–5 min | optional |
| Per PR | server, full | build, deploy to preview URL, QA, approvals | once per feature | exists (team CI) |

One server run per feature is enough. What changes in Forge is not the frequency but the direction of reading: `/verify` consumes the server's result and run URL as input instead of writing its own "gates green" from a local run.

Two cheap details if the agent ever pushes mid-feature: put `[skip ci]` in WIP commit messages so intermediate pushes do not trigger the pipeline; if an intermediate signal is still wanted, give the light job a `concurrency` group with `cancel-in-progress` so five quick pushes cost one completed run.

### Squash ordering

If `/verify` reads the CI result of the pushed branch, the thing verified must be the thing merged. Two consistent orderings exist. Note first that `/finalize` today skips the squash when WIP commits were already pushed, and the team flow pushes before merge, so `/finalize` changes in either case. The 2.0 line inherits the same model (squash via `merge-base` as the last step before the PR).

**Variant A (recommended): the server squashes.**

```
tasks (WIP) → review → push → CI → preview URL
→ verify: reads the CI status, ac-verifier exercises the same URL QA will use,
          records SHA, tree hash and run URL
→ finalize: docs + summary as one commit, push, opens the PR
            with the title in the team's single-commit convention
→ QA on the URL → approvals → "Squash and merge" on the host
```

One commit lands on the default branch, produced by the server. CI and QA tested exactly the head that merged. WIP history stays visible in the PR, which is the audit trail a local squash erases. The docs commit after verify does not invalidate the verdict: `/finalize` asserts the code subtree hash equals the one recorded at verify, and a path filter keeps a docs-only push from rebuilding. Forge's local squash is disabled by configuration. One ask of the repo admins: allow squash-merge and disable the other merge buttons.

**Variant B: the team requires one local commit before push.** Then the proposal "squash before verify" must be completed: everything that changes the tree moves before verify.

```
tasks (WIP) → review → docs + summary → squash → push → CI → preview URL
→ verify: the last gate; reads CI, exercises the URL
→ QA → approvals → merge
```

Any fix after verify or QA means amend, force-push with lease, a new CI run and a re-verify. Re-verify is cheap through the tree hash: unchanged parts carry over on evidence, only the delta is re-checked. `/finalize` shrinks to opening the PR and flipping the spec status. Cost of B: WIP granularity is gone before a verdict exists, so crash recovery and diff-based ACs work only from `merge-base`, and the audit trail must come from CI logs and the PR rather than from commits.

Common to both: `/verify` stops being the author of the build verdict and becomes its reader; its own work narrows to what the server cannot do, exercising ACs against the live URL and folding in review reports. In standalone mode CI can also run Forge's mechanical gates because the specs sit beside the code; in A those gates see the full PR history, in B a single commit.

### Is this standard?

Yes, for about ten years: protected branches, required status checks, required reviews, CI on every PR, per-branch preview deploys, merge queues. Regulated organizations treat it as a baseline change-management control. The new part is only who is being constrained: CI used to catch a human's mistakes; now it is the independent oracle for code a model wrote and marked PASS itself. Forge's local gates are the "works on my machine" level the industry left behind; relocating them is catching up, not inventing.

### Time and money

Reference timings from a 20-package Vite monorepo, measured locally: one package build about 30 s, app type-check about 3 min, the full verify set about 15 min of builds.

| Item | Estimate |
|---|---|
| Full monorepo run, 2-core hosted runner, no cache | 10–20 min |
| Same with dependency cache and a remote build cache | 4–8 min |
| GitHub-hosted Linux, 2 cores | about $0.008 per minute |
| 4 cores / 8 cores | about $0.016 / $0.032 per minute |
| Included minutes per month, Enterprise plan | 50,000 per organization |
| One 15-minute run on 2 cores | about $0.12 |
| A 10-task feature, about 13 runs | about 200 min, $1.6 |
| A team shipping 20 features a month | about 4,000 min, $32, inside the included minutes |
| Self-hosted runner, 4 vCPU / 16 GB | $50–120 per month, no per-minute cost, warm caches |

Rates are the standard GitHub Actions prices known at the time of writing; re-check before any rollout. Money is not the constraint. Time is: 10–15 minutes per task is why gates get split into a fast per-push tier and a full per-PR tier. The hidden cost is false halts: flaky or baseline-failing tests become red merges for no reason on day one (section 5).

What pays off long before any framework work: fix or quarantine failing and flaky tests, enable a remote build cache in CI, separate the fast and full gates, separate verification from deployment in the pipeline, and ask the repo owners to make the verification job a required status check on the default branch. Then Forge only has to read a status that already exists.

---

## 2. Compliance audit trail

### What it is

Proof that each control (build, tests, review, AC verification, QA, approvals) actually ran on each change that reached the default branch, kept where it cannot be edited after the fact and where it does not vanish with the branch.

### Why it does not exist today

Forge writes `review.md`, `verification.md` and `summary.md` into the feature directory. These are written by different agents (review agents, the verify stage with ac-verifier, not the implementing agent), so role separation exists. But all of them live in one trust domain: the same machine, the same operator, the same session with the same write rights to the tree, the same orchestrator composing their prompts and reading their answers. One consumer installation recorded a gate agent marking a criterion PASS while the orchestrator failed to check it against the criterion's literal words: two agents, one wrong result. Independence for an auditor means a different execution environment and a medium none of the participants can change. Markdown in the working tree is both the evidence and the thing under examination, and the squash erases the WIP commits where much of the evidence lived. An auditor's question "for change X merged on date Y, show that tests and verification ran and who approved" cannot be answered with "open the markdown file". Another consumer installation passed every gate green and still received NEEDS WORK because the evidence, not the behaviour, was missing.

### Operator view, on `/finalize`

Almost nothing changes in the chair.

- `/verify` prints the same report and also writes `verification.json`: what was checked, on which SHA and tree hash, when, by which Forge version and model, the result per AC, the CI run URL.
- A CI job takes that file and publishes it as a check next to the commit, for example "forge/verify: PASS, 12 AC, tree abc123". The check lives on the server, not in the tree.
- `/finalize`, instead of squashing, builds the PR, and its description carries an evidence table: CI run, verification check, review check, the requirement of an approval from the QA group.
- At merge an evidence bundle is exported to write-once storage so it survives branch deletion and repository changes.

Where the operator feels it: when evidence is missing. `/verify` ran locally but no server record exists for that SHA, and `/finalize` refuses to open the PR. Or someone edits `verification.md` after the record exists, and that is a new record with a new date, not an edit. The second change is for people: QA approval becomes a formal recorded step (a review from the QA group via rulesets or CODEOWNERS), not "said OK in chat".

### Is this standard?

In regulated organizations, yes. SOC 2, ISO 27001 and PCI DSS require change control with evidence, and the industry's usual answer is exactly this: PR, required checks, recorded approvals, retained logs. Tooling exists: host audit logs, check runs, build-provenance attestations (SLSA-style, e.g. `actions/attest-build-provenance`), compliance platforms that pull PR evidence automatically. The new part is one line: verification performed by an agent becomes one more recorded control beside the human ones.

### Time and money

| Item | Estimate |
|---|---|
| CI log retention | 90 days by default, configurable up to 400 days on private repos |
| Evidence export to object storage with object lock | a few KB–MB per feature; 1,000 features under 1 GB; cents per month |
| Runtime per run | seconds, one job step |
| Engineering | record schema, emission from gates, a CI step, the export: a few weeks once |
| Process | QA as a formal reviewer, retention rules, who may delete |

The cost is discipline, not hardware: agree the record schema and the rule that a record without a server copy is not evidence.

---

## 3. LLM-verdict reproducibility

### What it is

Given the same evidence, the verdict comes out the same, today, in six months, on another model; and the documentation says honestly where the machine computes, where the model advises, and where a human decides.

### The problem

A model is irreproducible by nature: the same prompt yields different text, models update, context order changes conclusions. Consumer installations recorded three reviewers unanimously approving a construct that was wrong, and re-runs producing different findings. If the `/verify` verdict is a paragraph the orchestrator writes after reading agents, it cannot be repeated and there is nothing to show an auditor. Plan 59 says explicitly: this is not a plan to make the LLM deterministic, it is a plan for honest separation. It also records the uncomfortable fact that the framework somewhere claimed "a human owns the `/verify` verdict" while the code shows otherwise. Auditors test claims against code; one false claim poisons the rest.

### The scheme auditors accept

| Layer | Who | Reproducible? |
|---|---|---|
| Mechanical | commands with exit codes and numbers: types, build, tests, measured ACs | fully, by tree hash |
| Advisory | review agents with evidence quotes, inside a fixed rubric | no, and this is admitted; stored as input, never as decision |
| Verdict function | a pure function: AC status table and mechanical results in, PASS or NEEDS WORK out by fixed rules | fully; anyone can recompute |
| Human checkpoints | spec approval, PR review, QA on the URL | as facts (who, when), not as judgments |

Accepted: "advisory, bounded AI panel; deterministic gate function; recorded human checkpoints upstream and downstream". Rejected: "AI decides, trust it", and equally a stated human gate that does not exist.

### Operator view, on `/verify`

Today the report ends with APPROVED or NEEDS WORK written by the orchestrator. With reproducibility the report has three clearly labelled blocks:

- A table of mechanical checks: command, number, run link. Anyone can repeat it on the same SHA.
- An advisory block labelled "advisory, non-binding, model X, run Y". Useful, but the gate does not depend on it.
- One verdict line with the rule that produced it: "NEEDS WORK because AC-7 FAIL". And an honest footer: "No human has approved this verdict. Human checkpoints: spec approved on date by role; PR review pending".

The behavioural change: you cannot argue with the verdict. A gate agent's argument for PASS is connected to nothing. To change the verdict you change the input: fix the code, or formally waive an AC with a recorded reason, which is the audited bypass of section 5.

### Where the LLM stays inside

Behavioural ACs that ac-verifier checks in a browser. Their status comes from a model and cannot be removed. Mitigation: the status is binary, the steps are recorded, a screenshot or DOM snapshot is stored, so a human can check the status from the evidence without re-running the model. In the assumed team flow the same ACs are then exercised by QA by hand, so the human checkpoint there is real.

### Is this standard?

The pattern is old under other names: a quality gate in SonarQube or a policy engine such as OPA. Metrics in, pass or fail by fixed thresholds out, with history. Every current AI code-review product positions itself as advisory comments, not a blocking decision. The new part is only that the advisory layer is written by an AI panel instead of a human reviewer.

### Time and money

Runtime: none; the verdict function is instant, replaying the mechanical layer costs one CI run. Engineering: mostly a document and a record schema, plus a replay command of the form "recompute the verdict for SHA". The roadmap believes the pure verdict function already exists in 2.0 and only its limits need stating and the text fixing. Days, not months. Pinning a model per agent (which 2.0 has) helps stability but is not reproducibility, and the document must not conflate the two.

---

## 4. Gate governance at scale

### What it is

Every check has a class, an owner and a change log, and only those permitted may change a gate, through the same process as a code change.

### The problem

Forge was designed around one sophisticated maintainer who decides which gates exist, what they check and when to relax them. A company has dozens of gates and many teams, and a control everyone depends on but nobody owns rots. Consumer installations supplied three clean examples: a package's `check` script was an empty string and passed as a no-op gate for months; a git hook everyone assumed was active was never wired; a lint baseline of several hundred warnings made every "lint with zero findings" criterion a fantasy. None of those gates had an owner, so nobody noticed.

The second side: the agent can change the gate itself. When self-repair hits a rule, the cheapest "fix" is to edit the constitution or the criterion. One installation recorded an agent correctly refusing to "fix" an out-of-scope file, but that was goodwill, not a prohibition.

### Three gate classes

The roadmap calls this the taxonomy and treats it as a governance decision, not engineering.

| Class | Behaviour | Example |
|---|---|---|
| HARD | blocks, no bypass | build fails, tests red, a measured AC does not match |
| ADVISORY | warns, does not block | review-agent findings, performance hints |
| OVERRIDABLE | blocks, but can be waived with a recorded reason and the owner's approval | a hygiene AC, a constitution rule on a legacy file |

The class is printed in the `/verify` report next to every AC, so the operator sees not just FAIL but "FAIL, HARD" or "FAIL, OVERRIDABLE, owner platform-team".

### Operator view, on `/implement`

A task edits code and also touches `constitution.md` because a rule is in the way. Today that is just another changed file in the commit. With governance a hook stops the agent: "Gate files are owned by platform-team. Open a separate gate-change PR". Gate files (the constitution, the enabled-checks config, the CI workflows) sit under CODEOWNERS, and a PR to them needs the owning team's approval. A gate change has its own template (why, risk, which features are affected) and enters the audit trail of section 2 as its own event type. For the operator this means one thing: relaxing a rule in five minutes mid-task is no longer possible, on purpose.

### Scale

With many repositories, gates live in a central versioned catalogue and each repository picks from the permitted set. Who may add a gate, who may retire one, how long a gate lives without review. Above all, gate health is measured: how many halts, how many false, how many bypasses per gate per month. Those numbers come from the audit trail, and they, not arguments, decide what to tighten and what to drop. A gate with a high bypass share either dies or gets more precise.

One warning from plan 60: do not invent a role system. Host rulesets, CODEOWNERS, required reviewers and environments already are one. The framework only needs to put gate definitions in files those mechanisms can protect, and print the gate class in its reports.

### Is this standard?

Yes. Protecting pipeline configuration and quality policy under a separate owner is the norm: CODEOWNERS on workflow directories, quality-gate administration permissions in SonarQube, policy-as-code repositories owned by platform teams, centrally owned rules in cloud governance. The new part is only that agents now author and consume the gates, and an agent may try to rewrite one.

### Time and money

The technical part is cheap: CODEOWNERS entries, rulesets, a hook on gate paths, a class field in config and report, a monthly gate-health report from trail data. Days of work. The slow part is organizational: naming owners, agreeing the taxonomy, agreeing that nobody edits a gate outside the process. Weeks of meetings, not code, and no cost beyond people's time. The roadmap puts this last because it organizes what the other four produce.

---

## 5. False-halt hardening and audited bypass

### What it is

A gate halts only when something is really wrong; when the gate itself is wrong, a legal exit exists that leaves a record: who, when, why, and who allowed it.

### The problem

A mechanical gate trades missed defects for false alarms. A hard gate that halts on correct but unpredicted work blocks correct work. Two such incidents are already root-caused in consumer installations. The consequence is always the same and worse than no gate: after a few false halts the team routes around the gate entirely, quietly and without records. This is why plan 61 precedes server-side enforcement: a merge-blocking gate with a false-halt rate above zero stops the release train on day one.

False halts collected from consumer installations:

| False halt | Why the gate lied |
|---|---|
| A grep criterion unpassable by construction | the pattern matched the fixed code |
| A count of 4 where 3 was expected | a test's JSDoc quoted the pattern |
| "Lint with zero findings" | a standing baseline of several hundred warnings |
| "Tests pass" | the suite exits 1 unconditionally at baseline |
| "Zero matches under the framework directory" | the session-state file echoed the string |
| A criterion from a predecessor spec | its branch was not merged yet |
| Two flaky tests | random red |

And the dangerous reflex this breeds is recorded too: a false halt "invites a fix to correct code". One agent refused to fix an out-of-scope file and reported the mismatch; another time it would have ended worse.

### Part one: precision

Most of the table is cured by discipline one installation evolved on its own: measure the gate at baseline before it becomes a criterion; phrase it as a delta ("unchanged from baseline"), not an absolute; anchor on the broken form, not a shared substring; scope the check to the PR diff, not the whole repository; skip a gate whose artifact is absent; quarantine flaky tests; add a negative control proving the gate can fail. And count the false-positive share per gate. A gate becomes HARD only after several features passed with zero bypasses on it. The 2.0 line has taken the spec-time baseline run into a plan: a hygiene command that already passes at baseline is refused at authoring time.

### Part two: the emergency button under glass

When the gate still errs on a legitimate case, the exit must be neither editing the AC, nor editing the gate, nor re-running until green, nor the agent arguing. It is a formal waiver: which gate, which SHA, the reason, who requested, who approved, until when. The record goes into `verification.json`, into a check on the PR, into the audit trail of section 2 and into the gate-health metric of section 4.

### Operator view, on `/verify`

AC-12 FAIL: "count 4, expected 3". Today the operator either argues with the agent, edits the spec, or someone "fixes" correct code. With this scheme the report shows the gate class. If HARD (build, tests), there is no exit, only a fix. If OVERRIDABLE, the report offers one action: waive AC-12 with the reason "a test's JSDoc quotes the pattern; the production count is 3" and name an approver from the gate's owning team. Until the approval exists the verdict stays NEEDS WORK. After approval the verdict is recomputed by the function of section 3, because the input changed, and the waiver is visible to QA and reviewers on the PR. What the operator feels: no more dead ends, but no more quiet workarounds either. Every exit is visible. The key rule: whoever hit the gate cannot lift it. The agent never approves a waiver; the operator only for advisory gates; the rest is lifted by the owner.

### Is this standard?

Yes, under different names. SonarQube has "false positive" and "won't fix" marks with justification. Security scanners have ignore-with-reason-and-expiry. Host rulesets have bypass actors with an audit log. ITIL has the emergency change via a break-glass procedure. SRE has flaky-test quarantine. The one new thing: the party hitting the gate is an agent, so the authority to lift it must belong to a human role, or the agent will lift gates as easily as it argues with criteria.

### Time and money

Runtime: none. Code: a waiver command, a record schema, a PR annotation, bypass configuration in rulesets, test quarantine. One to two weeks. Process: a table of who approves what per gate class, the same one as in section 4. The main investment is the baseline-measurement discipline a consumer installation has already paid for.

---

## 6. Closing

Together the five form one chain: an honest statement of what the machine judges and what a human does; precise gates with a legal exit; then gates moved to the server; then evidence from the server and from bypasses in an immutable trail; and finally owners for all of it. None of the mechanisms is new to the industry. What is new is the party on the other side of the gate.
