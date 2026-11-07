# Research: Published evidence of spec-driven and agent-gated development at corporate scale

**Date**: 2026-10-03
**Subject**: Is there public evidence that organisations have implemented what Forge-style pipelines propose: spec-first authoring, agents working under mechanical gates, and automated verification replacing parts of manual QA? Digest of a web survey made on 2026-10-03.
**Status**: Evidence digest for a stakeholder discussion. Companion to `2026-10-03-enterprise-gates-plain-language.md` and `2026-10-03-qa-queue-to-pipeline-verification.md`.
**Method**: Web search (extended mode) on four questions: spec-driven adoption, autonomous agents in production at enterprises, AI replacing manual QA, and independent research on outcomes. Every figure below is labelled by who reports it. Vendor and vendor-customer figures are not independently audited.

---

## 1. Short answer

Yes, on three layers:

1. **Spec-first with agents** is practised at scale inside Amazon/AWS and is productised by AWS (Kiro) and GitHub (Spec Kit). Thoughtworks still classifies the practice as emerging.
2. **Autonomous agents in production engineering** run at Goldman Sachs, Nubank and Rakuten, alongside human engineers, with human review and triage retained.
3. **Agent-authored and self-healing test suites** are a formed market (mabl, QA Wolf, Meticulous, agentic QA tools), with at least one published enterprise result (Tekion).

What has **no public precedent**: an organisation removing the QA function and leaving acceptance to the product manager alone. Published cases replace test authoring and maintenance, not the acceptance decision.

## 2. Cases

| Organisation | What they did | Reported results | Reported by |
|---|---|---|---|
| Amazon / AWS (Kiro) | Spec-first with EARS acceptance criteria, steering files, several agents critiquing in parallel, property-based tests generated from the spec, agents running for hours with build/test self-correction | An 18-month re-architecture scoped for 30 developers done by 6 people in 76 days; Kiro team's feature builds from two weeks to two days; an Amazon.com feature shipped two months early; one developer at 150 check-ins per week | AWS, via VentureBeat (2026-04-13) |
| GitHub (Spec Kit) | Spec-driven toolkit | 111,000 GitHub stars by June 2026; internal teams report roughly an order of magnitude fewer "regenerate from scratch" cycles than ad-hoc prompting | GitHub |
| Goldman Sachs (Devin) | Autonomous agents across the technology division, alongside about 12,000 engineers: scoping, coding, testing, debugging | "Three to four times better" than previous AI tools per the CIO; vulnerability-fix time from 30 minutes to 1.5 minutes per issue (one organisation using the tool) | Forbes (2026-08-06), Cognition |
| Nubank (Devin) | Agents fine-tuned on the codebase | 4x task speed | Cognition |
| Amazon Q Developer Transformation | Agent-driven application migrations (mechanical campaigns) | Tens of thousands of production applications migrated; over 4,500 developer-years saved; $260M annual savings | AWS |
| Rakuten (Claude Code, then Claude Managed Agents) | 7 hours of sustained autonomous refactoring; agents run multi-step workflows overnight; employees delegate goals, humans triage tickets and give feedback | 99.9% accuracy on complex code modifications; time to market from 24 to 5 days (−79%); 97% reduction in initial critical errors; major releases from quarterly to every two weeks; cost and latency down more than 30% | Anthropic customer stories |
| Tekion | Agent-based e2e testing | 1.1% flakiness after six months; 47 bugs caught that hand-written suites missed | QA tooling surveys, 2026 |
| Market | AI QA platforms | mabl positioned as the enterprise standard with SOC 2; QA Wolf as a managed service at $60k–250k+/year; Meticulous raised a $15M Series A in July 2026 on session-replay testing | Tooling surveys, 2026 |

A secondary source reports an 84% merge success rate for autonomously produced pull requests against an 85% human baseline; source quality is unverified and it should not be cited alone.

## 3. Independent sources

- **DORA 2025 (Google)**: 90% of practitioners use AI, a median of two hours a day. Only two of seven team archetypes gain throughput without a rise in change failure rate. Core finding: AI is a multiplier of existing engineering conditions; it strengthens disciplined organisations and exposes fragmented ones.
- **METR**: a 2025 randomised trial (16 experienced open-source developers, 246 tasks) measured developers 19% slower with AI tools while believing they were faster. A 2026 continuation changed the design and reports the new data as an unreliable signal of the current effect; the original page is marked out of date. The science is unsettled.
- **Thoughtworks Technology Radar**: spec-driven development in the Assess ring in Volume 33 (2025-11-05) and GitHub Spec Kit in Assess in Volume 34 (April 2026), with the caution that the workflows remain elaborate and opinionated and that substantial change is expected through 2026.
- **AWS's own cautions** (same VentureBeat piece): early "vibe coding" produced "a surplus of slop"; the practice currently needs deep expertise and is accessible mainly to top developers; orchestrating tools and infrastructure "is hard".

## 4. What matches a Forge-style pipeline

Directly matching, and citable as precedent:

- Spec-first with EARS criteria and the spec living in the repository, versioned and visible in PRs (Amazon/Kiro, GitHub).
- Tests derived from the spec rather than from the code, including property-based generation (AWS).
- Several agents critiquing a design in parallel before implementation (AWS), the equivalent of adversarial review stages.
- Long autonomous runs with build/test self-correction loops (AWS, Rakuten).
- Humans at the level of goals and triage rather than tasks (Rakuten); agents working beside engineers with human review (Goldman Sachs).
- Mechanical campaigns as the first class of work to run with minimal supervision (Amazon Q Transformation), consistent with the observation that autonomy holds where the goal is a number and the gate is deterministic.

## 5. What has no public precedent

- Removing the QA function and leaving acceptance to the product manager alone. Every published case keeps a human review or triage step; QA tooling replaces authoring and maintenance of tests, not the acceptance decision.
- Independent audit of the headline figures. "97%", "99.9%" and "4,500 developer-years" are vendor or vendor-customer statements.

Consequence for a proposal that includes a product-manager-only acceptance step: present it as a measured pilot, not as a reproduction of someone else's practice.

## 6. Reading the evidence together

Every organisation reporting wins has a strong engineering platform. Under DORA's multiplier finding this is not a coincidence: AI amplified discipline that already existed. For an organisation with shallow manual QA and a weak test baseline the multiplier can go either way, which is the argument for fixing the foundation before mandating gates (see the companion notes).

## 7. Suggested use in a stakeholder deck

Four anchors and one honest sentence:

1. Amazon/Kiro: spec-first works inside a very large engineering organisation.
2. Goldman Sachs: a regulated bank runs agents beside its engineers.
3. Rakuten: release cadence from quarterly to biweekly.
4. DORA 2025: why to start with the foundation and measure.

The sentence: "the product-manager-only acceptance step is ours to validate; there is no public precedent."

Label every vendor figure "as reported by the company".

## Sources

- [Agentic coding at enterprise scale demands spec-driven development, VentureBeat](https://venturebeat.com/orchestration/agentic-coding-at-enterprise-scale-demands-spec-driven-development)
- [Spec-Driven Development in 2026: What It Is, the Tooling, and How Teams Actually Use It](https://dev.to/krlz/spec-driven-development-in-2026-what-it-is-the-tooling-and-how-teams-actually-use-it-2fk2)
- [Spec-Driven Development is the New Default for AI Coding](https://alphasignalai.substack.com/p/spec-driven-development-is-the-new)
- [How Goldman Sachs Is Using Agentic AI For Software Engineering At Scale, Forbes](https://www.forbes.com/sites/bernardmarr/2026/08/06/how-goldman-sachs-is-using-agentic-ai-for-software-engineering-at-scale/)
- [Cognition Business Breakdown, Contrary Research](https://research.contrary.com/company/cognition)
- [Amazon Q Developer Transform, AWS](https://aws.amazon.com/q/developer/transform/)
- [Rakuten customer story, Anthropic](https://www.anthropic.com/customers/rakuten)
- [Rakuten Claude Managed Agents case study](https://claude.com/customers/rakuten-qa)
- [Best AI E2E Testing Tools 2026, Autosana](https://blog.autosana.ai/alternatives/best-ai-e2e-testing-tools-2026)
- [AI Testing Agents in 2026: Hype, Reality, and 5 Tools](https://wopee.io/blog/ai-testing-agents/)
- [How are developers using AI? Inside our 2025 DORA report, Google](https://blog.google/technology/developers/dora-report-2025/)
- [DORA 2025 AI assisted dev report: Some Benefit, Most Don't](https://blog.robbowley.net/2025/10/01/dora-2025-ai-assisted-dev-report-some-benefit-most-dont/)
- [Developers Using AI Take 19% Longer on Tasks, eWeek](https://eweek.com/news/news-ai-tools-slow-developer-productivity-study)
- [AI made developers slower, then December happened](https://urandom.io/blog/2026-03-01-ai-made-developers-slower-then-december-happened)
- [Claude Code 84% PR merge success rate (secondary, unverified)](https://www.getreadyforagents.com/news/claude-code-pr-merge-success-rate-84-percent/)
