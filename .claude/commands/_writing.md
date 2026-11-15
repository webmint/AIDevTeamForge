---
disable-model-invocation: true
user-invocable: false
---
# Writing: Documents a Person Can Read

Referenced by the commands that write specs, plans, tasks and reports. Labels and their forms: `.claude/storage-rules.md` → "Labels".

## Rules

- Each fact is written once.
- The spec says WHAT; the plan says HOW.
- A decision gets one sentence of why.
- A document refers to another document instead of retelling it.

## Specs

A spec with the header line `**Format**: 2` holds in each section only what the section names.
- **1. Summary**: for people, 5–10 plain lines: what is built and why it is needed, what is not built, and what the user decides. No labels, paths or quotes.
- **2. Current State**: only the facts the criteria and the plan depend on, with `file:line`; for the rest, a link to `research-report.md` when there is one, never a retelling of it. `/plan` reads this section and Affected Areas instead of `docs/`, so the docs facts it needs are here.
- **3. Behaviour and Acceptance Criteria**: one `### 3.N <name>` group per behaviour. Each group has at most a few lines of behaviour (who acts, when, on what), then its criteria, numbered across the spec. A rule is stated once, in its criterion; the behaviour lines do not repeat it.
- **5. Out of Scope**: one line per entry.
- **6. Technical Constraints**: what `constitution.md` and `CLAUDE.md` do not already say (a rule they hold is named, not copied): the external systems the change depends on and the existing features it must not break.
- **7. Decisions**: one sentence of why each; numbered after the highest `DEC` in the spec and its plan, so a revision after the plan does not reuse a number.
- **8. Open Questions**: numbered as `_intent-check.md` → "The Request Record" says. Once answered, the answer goes to `history.md` and the line goes.
- **9. Risks**: numbered after the highest `RISK` in the spec and its plan.

The spec states what holds, not who said or found it: the request, answers, gate findings and amendments live in `research-report.md`, `history.md` and `gates/`, and the spec does not copy them. The header's `**Status**:` and `Self-approved …` lines stay.

## Plans

In a plan with the header line `**Format**: 2`:
- **Summary**: in words, as `CLAUDE.md` → "Talking to the User" says: the approach in 1–2 sentences, how many files are new and changed, the key decisions and the high risks.
- **Key Design Decisions**: each row opens with `DEC-N`, continuing the spec's Decisions (the highest `DEC` in the spec and the plan, plus one). The answer to a question `/plan` asks is a row here, never a `Q` entry.
- **Risk Assessment**: each row opens with `RISK-N`, continuing the spec's Risks (the highest `RISK` in the spec and the plan, plus one).

An older spec's plan has no Format line and no Id columns, and its Summary is 2–3 sentences on what it implements and how.
