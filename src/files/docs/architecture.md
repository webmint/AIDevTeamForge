# Architecture — {{PROJECT_NAME}}

- **Type**: {{PROJECT_TYPE}}
- **Language(s)**: {{LANGUAGE}}
- **Framework(s)**: {{FRAMEWORK}}
- **Workspace Mode**: {{WORKSPACE_MODE}}
- **Source Root**: {{SOURCE_ROOT}}

> For multi-package projects, per-package details (path, language, framework, architecture pattern, error-handling convention, API layer, testing framework, build/lint/typecheck commands) live in the `## Packages` section of `CLAUDE.md` / `AGENTS.md`. This file captures project-wide architectural decisions, not per-package stack tables.

---

## Architectural Decisions

_Populated by `/constitute` — records WHY decisions were made, not just what. Format: **Decision** — rationale + tradeoffs considered._

## Layer Boundaries & Dependency Rules

_Populated by `/constitute` (for new/greenfield projects — chosen patterns) or `/onboard` (for brownfield projects — extracted from existing code). Documents which layers exist, what imports from what, and which directions are forbidden._

## Data Flow

_Populated by `/onboard` (for brownfield — scan findings) or by tech-writer as features are built. Captures how data moves through the system end-to-end._

## Cross-cutting Concerns

_Populated as relevant: authentication/authorization approach, error propagation strategy, logging/observability, transaction boundaries, caching strategy, feature flagging. Filled in by `/constitute` or discovered by `/onboard`._
