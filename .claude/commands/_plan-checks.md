---
disable-model-invocation: true
user-invocable: false
---
# Plan Checks: What Every Plan Asks Before It Is Written

Referenced by `/plan` (Phase 2, before it writes the plan) and `_independent-gate.md` → "Reviewer Prompt", which pastes these sections verbatim into the plan-gate lenses' prompts: "Precedents" and "Runtime" into the architect lens's, "CI-unrun tests" into the QA lens's. A lens reads only its own checklist section, so a rule here reaches it only through that paste.

## Precedents

_Filled by piece 5 of release 1.41.0 (the Precedents table); pasted into the architect lens's prompt._

## Runtime

_Filled by piece 4 of release 1.41.0 (the runtime questions); pasted into the architect lens's prompt._

## CI-unrun tests

_Filled by piece 6 of release 1.41.0 (tests CI never runs); pasted into the QA lens's prompt._
