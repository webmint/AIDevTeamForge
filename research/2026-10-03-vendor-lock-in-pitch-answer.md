# Research: Vendor lock-in — the honest answer for the corporate pitch

**Date**: 2026-10-03
**Subject**: Forge is tuned to one model family and one harness (Claude, Claude Code). The maintainer intends to present Forge to a corporation, run a pilot that adapts it to that corporation's processes, and expects the repository to be forked and modified. The lock-in question will be asked. This note records why Forge is single-family, what a GPT-grade equivalent or a hybrid would cost, which lock-in risks are real, and the answer to give, in the order the questions come.
**Status**: Assessment note for a stakeholder discussion. Not a plan, nothing ratified. Section 7 holds measured facts with the command that produced them; everything else is reasoning. Companion to `2026-10-03-enterprise-gates-plain-language.md` and `2026-10-03-qa-queue-to-pipeline-verification.md`.
**Guard**: no consumer project, team, path, package or spec number is named. Statements about other vendors' documentation and products are marked **[verify before quoting]** where they rest on the author's recollection rather than on this repository.

---

## 0. Why this note exists

The deployment model is pilot, then fork. The corporation will own a modified copy of this repository and run it on its own processes. Two questions hide behind "are we locked in": lock-in to the framework author, and lock-in to the model vendor. The fork kills the first. The second is real, bounded, and deliberately chosen. The pitch needs that said plainly, with numbers, before someone else says it with suspicion.

## 1. What happened on GPT, and why

The maintainer attempted a comparable framework for the GPT family, separately and also by letting a GPT model build it. Two failures recurred:

1. **Procedure compression.** Multi-step procedures written in prose were shortened; gates the model judged unnecessary were skipped; literal prompts were paraphrased.
2. **Documentation quality.** At the generate-docs stage the output stayed far below what Claude produces from the same instructions: outline-shaped, terse, missing cross-references.

The folk diagnosis is "GPT is disobedient". The actual causes are structural:

- **Harness, not model.** Forge compiles into the Claude Code harness: `CLAUDE.md`, commands, agents, hooks, subagents. The model was trained with that harness in the loop, so a project instruction file is treated as near-system guidance. The GPT ecosystem has a different harness with a different feature set; an attempt through a raw API or a third-party editor rebuilds the harness from scratch, and the harness is what fails first.
- **Instruction hierarchy.** OpenAI trains an explicit system > developer > user priority. Instructions arriving as file content in context sit low in that hierarchy, so a long procedural command file loses weight. **[verify before quoting]**
- **Contradiction sensitivity.** OpenAI's own prompting guides for GPT-4.1 and GPT-5 warn that contradictory or ambiguous instructions degrade output more sharply than in prior generations. A framework of this size always carries some inconsistency; Forge's sentence-level hallucination check exists to catch it, and GPT punishes what slips through harder. **[verify before quoting]**
- **Priors, not disobedience.** GPT is rewarded for task completion with few tokens; compression is the trained default. Claude is rewarded more heavily for process adherence; its failure mode is finding an escape hatch and complying superficially. Forge's zero-escape-hatch and default-argue rules are evidence that Claude drifts too, differently. Over a hundred plans calibrated Forge to Claude's drift profile. The GPT attempt never received that iteration budget.
- **Asymmetry of correction.** A verbose model can be bounded ("at most N lines per section") and complies. A terse model told "at least N lines" produces padding, because it decided at planning time that the content was unnecessary. Length can be forced; quality cannot.
- **Reflexivity trap.** A model building a framework to steer itself will not write rules against its own tendencies, because it does not perceive them as problems. The zero-escape-hatch rule exists because a human observed the escape hatches and forced the rule.

## 2. The principle: interchangeability costs the lowest common denominator

The mediocrity of multi-model frameworks is not the price of using several models. It is the price of requiring that the same prose instruction work on several models as interchangeable executors. A prompt tuned for all is tuned for none. Models doing *different* jobs (see section 4) pay no such price.

The real axis is **where the intelligence lives**:

| Architecture | Intelligence lives in | Ceiling on judgment phases | Iteration cost | Portability of the pipeline |
|---|---|---|---|---|
| Prose-driven (Forge today) | the model's reading of `main.md` | high | low: edit markdown, rerun | low: prose is tuned to one prior profile |
| Code-driven | orchestration code with schemas and outcome gates; model as a function | lower on `/grill`, `/audit`, `/constitute` | high: every change is code | high |

Forge chose prose-driven for the ceiling and the iteration loop. Single-family tuning is a consequence of that choice, not a goal. The trade is the same one as Kubernetes-native versus cloud-agnostic, or Postgres-specific SQL versus ORM-agnostic SQL: abstraction over heterogeneous backends costs the lowest common denominator.

## 3. Could a GPT-grade Forge exist?

Yes, as a different product, not a port.

- **Capability versus steering.** The generate-docs failure was a steering failure, not a capability ceiling. GPT-5-class models produce long, high-quality documents when generation is decomposed per section with a strict output schema and exemplars. The system, not the model, has to produce Claude-grade artifacts with GPT as a component.
- **Shape.** Orchestration in code: each phase a program step with a narrow prompt, a JSON schema on the output, a mechanical gate, and a regeneration loop on rejection. Exemplar library of Claude-produced documents as few-shot. This is a runtime of its own, not an emitter of markdown into someone else's harness.
- **What ports.** Handoff schemas, constitution format, storage rules, helper scripts, forcing functions, verify-detectors: roughly the mechanical layer, in the region of 40% by effort. Zero lines of the prose phases port, and none of the calibration experience.
- **Where GPT is genuinely stronger.** Strict structured outputs guarantee the schema, which suits an outcome-gated design. Compression is cheaper on implementation phases. Lower tendency to claim a verification it did not perform.
- **Where parity is doubtful.** Judgment phases hold a large body of rules in context and argue against their own output across a long transcript. Decomposed into many bounded calls, the holistic view is lost. Parity is plausible on mechanical phases; on adversarial phases it should not be assumed without evidence.
- **Cost.** Forge reached its current state through over a hundred tuning plans. The equivalent loop on a code-driven runtime is slower per iteration, so an eval harness is needed from day one or regressions stay invisible. For one person it is a second product of comparable effort, and running both halves the velocity of each.
- **Who builds it.** Not GPT (section 1, reflexivity trap). Built with Claude, tested on GPT.

## 4. Hybrid routing per phase

A per-phase model switch (Claude for judgment, GPT for mechanical work) is often proposed as the compromise. It answers a different question than lock-in.

- **Lock-in doubles.** Two vendors, two contracts, two compliance reviews, two outage profiles; pipeline reliability is the product of both. "Do you depend on Anthropic?" becomes "do you depend on both and can drop neither?". The only honest way to present a hybrid node to a corporation is as a *demonstration* that the artifact layer is model-agnostic in practice, not as a hedge.
- **Harness lock-in is unchanged.** The orchestrator stays Claude Code; the other model is called as a tool on a designated step. Forge's file-based handoff design is what makes that call possible at all: the external node sees serialized artifacts, never the transcript.
- **Where a hybrid genuinely wins: decorrelated review.** GPT as the sole executor of a long adversarial procedure is weak; GPT as a reviewer of a bounded artifact with an output schema is strong and, more importantly, *different*: its blind spots do not coincide with Claude's. The refutation stage of `/audit`, the devils-advocate role in `/grill`, and finding verification are where a second model family adds signal. Claude reviewing Claude shares Claude's priors.
- **Where it loses: cost.** If the goal is cheaper implementation, intra-vendor tiering is available with zero new infrastructure through the `model` field in subagent frontmatter. Measure that first.
- **Per-node price.** Each external node needs its own prompt with schema and exemplars, its own eval, its own drift detector, and API-key handling in the consumer installation. Mixed authorship inside generated docs needs a harmonization pass. Routing must be deterministic per node; "fall back to Claude if GPT fails" is the OR clause the meta-discipline forbids.
- **Bounded experiment, if ever.** One node: refutation in `/audit`. The external model receives finding, evidence and schema, returns a verdict JSON. The metric is whether it catches what the Claude refutation missed. Plan-sized scope, not product-sized.

## 5. What vendor lock-in actually risks

"The vendor will not die" is the weakest argument and should not be voiced: unfalsifiable, and vendor death is the least likely scenario. The realistic risks, each with the answer:

| Risk | Likelihood | Answer |
|---|---|---|
| Pricing and usage-limit changes | high; has happened to Claude Code before | enterprise contract through the corporation's cloud (Bedrock, Vertex AI, Microsoft Foundry) with fixed terms **[verify current provider list before quoting]** |
| Model generations retired, tuned behavior shifts | certain, recurring | already paid regularly; forcing functions, verify-detectors and the drift check are the collection mechanism; plan 104 is a worked example of drift caught mechanically and fixed |
| Harness churn (command formats, frontmatter, new native features) | high, monthly | the output format is isolated in the emitter under `scripts/emitters/`; a convention change is an emitter edit, not a framework edit; the `claude-code-guide` verification rule exists for this reason |
| Platform absorption (native spec-to-plan-to-tasks, native memory) | medium, rising | Forge becomes a thinner layer over the native feature; constitution, forcing functions and adversarial phases remain value the platform does not provide |
| Vendor disappears | low | artifacts and the Python layer survive untouched; the pipeline is re-tuned, not rewritten |

Claude Code itself is closed-source as of this note. Its conventions are documented markdown, and at least one open-source harness reads `CLAUDE.md` and offers analogous commands and agents. **[verify before quoting; do not promise compatibility]**

## 6. The fork model splits the question

- **Lock-in to the author: none after the fork.** Source code, Python and markdown, no runtime dependency, no SaaS, no license key. This distinguishes Forge from any commercial tool evaluated alongside it. Say it first, before being asked.
- **Lock-in to the vendor: bounded.** Section 7 gives the proportions.
- **The pilot legitimately defers the scale question.** Lock-in is a production-adoption question, not a pilot question. The pilot produces the data to answer it: how much prose actually changed for the corporation's processes, what one re-tuning costs, where drift shows up. State what will be measured.
- **The fork inherits the drift tax.** The corporation will own re-tuning. The pilot is a transfer of competence, not only of code. The methodology is in the repository: plans, `FINDINGS.md`, the discipline rules in `CLAUDE.md`. The fork carries the decision history, not just the state.

## 7. Measured facts

Measured on 2026-10-03 against the working tree:

| Layer | Lines | Dependency |
|---|---|---|
| Python helpers, `src/devforge/lib` + `scripts` (tests excluded) | ~120 000 | no model or vendor SDK; zero imports of `anthropic` or `openai` |
| Command and agent prose, `src/commands` + `src/agents` | ~16 000 | tuned to Claude |
| Harness-format emitter, `scripts/emitters` | 158 | Claude Code |

Reproduce with:

```sh
grep -rlE '^\s*(import|from)\s+(anthropic|openai)' src scripts --include='*.py' | wc -l
find src/devforge scripts -name '*.py' -not -path '*/tests/*' | xargs cat | wc -l
find src/commands src/agents -name '*.md' | xargs cat | wc -l
cat scripts/emitters/*.py | wc -l
```

Re-run before the pitch; the numbers drift with the tree.

## 8. The answer, in the order the questions come

- *"Are we locked into Anthropic?"* Yes, at the production-line layer, by design. Sixteen thousand lines of prose are tuned to Claude. A hundred and twenty thousand lines of Python and every artifact in git are tied to nothing.
- *"Why not multi-model?"* Interchangeable models cost the lowest common denominator. We chose the quality ceiling over prose portability, because prose gets rewritten and the knowledge in the artifacts stays.
- *"Pricing, terms, compliance?"* Claude through your cloud provider under your existing contract. For procurement, the vendor is your cloud.
- *"If we later want another model?"* Artifacts and Python move unchanged. Prose is rewritten for the new model's profile: a re-tuning by a known procedure, not a rewrite of the product. We run that procedure on every major Claude release.
- *"Claude Code is closed. And?"* Yes. The output format is isolated in a 158-line emitter. A convention change is an emitter edit.
- *"Who maintains the tuning after the fork?"* You. The pilot transfers the competence. The methodology is recorded in the repository.

## 9. What not to say

- "It is portable." One follow-up question and credibility is gone. Say: artifacts are portable, prose is not, and here is why that was chosen.
- "Anthropic will not die." Unfalsifiable, reads as naive.
- "We plan a GPT port." There is no such plan, and the promise would hang on the maintainer.

## 10. Proposed follow-up (not built)

A `DEPENDENCIES.md` at the repository root, or a section in `DEVELOPMENT-STATUS.md`, extending the section 7 table per component: moves unchanged / needs adaptation / is rewritten, plus a short exit-cost statement. Because the repository will be forked, the document travels with the fork and answers the question without the maintainer present. Hours of work. It is the only code-side change this note recommends before the pitch.
