---
name: Research efficiency over thoroughness by default
description: Web search in /plan should be signal-based, not automatic — avoid overhead on simple features
type: feedback
---

Prefer "always evaluate" over "always run" for expensive operations like web search.
Not every feature needs internet research — adding a field to a form doesn't need web search, but integrating a payment system does.

**Why:** Unnecessary web searches waste tokens and add latency on simple features where the codebase already has all needed context.

**How to apply:** When designing workflow steps, use signal-based triage (detect complexity signals first, then decide depth) rather than blanket "always do everything". This applies beyond just /plan — any phase that involves external lookups should justify the cost.