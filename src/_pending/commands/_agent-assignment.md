# Agent Assignment: File-Layer Mapping

This file is the single source of truth for assigning agents based on the files being changed. Referenced by `/breakdown`, `/fix`, and `/refactor`.

Each command reads this table and selects the agent whose row best matches the files involved by the file's owning package/stack (see `## Packages` / `PACKAGE_STACKS` in `CLAUDE.md`). A type, interface, domain model, contract, or state store is **not its own layer with its own agent** — it belongs to the stack that owns the file, and that stack's implementer writes it. The architect never appears in this table: it shapes at `/plan` and only *VALIDATES* the decomposition — it does not write code.

## Assignment Table

| Files in... | Agent |
|-------------|-------|
| API endpoints, controllers, middleware, services, server-side logic — and the backend stack's domain models, types, interfaces, contracts, and business/state logic | backend-engineer |
| UI components, styles, routes, composables, stores — and the frontend stack's domain models, types, interfaces, and state management (BLoC / Redux / Pinia) | frontend-engineer |
| Mobile screens, navigation, native modules, platform-specific code, app lifecycle — and the mobile stack's domain models, types, and state | mobile-engineer |
| Bug investigation with runtime symptoms | runtime-debugger |
| Performance-critical path or optimization task | owning stack engineer (backend/frontend/mobile-engineer, per the file's layer) — `performance-analyst` diagnoses and recommends during `/review`, it never implements |
| Auth, secrets, input validation, security hardening | owning stack engineer (backend-engineer for server-side auth/secrets/validation; frontend-engineer for client-side) — `security-reviewer` reviews during `/review`, it never implements |
| Database schemas, migrations, queries, seed data | db-engineer |
| API contract design, OpenAPI specs, endpoint structure | api-designer |
| CI/CD, Docker, deployment config, infrastructure | devops-engineer |
| Data migration scripts, backward compatibility layers | migration-engineer |
| Accessibility, design system compliance, UI audit | design-auditor |
| Unclear or mixed | split per the rule below — never `architect` |

A mixed or unclear task is a decomposition smell, not a routing problem: split it until each piece maps to exactly one stack's implementer; if a piece genuinely spans stacks (e.g. a backend API plus its frontend consumer), break it into per-stack tasks joined by a dependency edge. If splitting is genuinely impossible, escalate to the human. If the owning stack's implementer doesn't exist in `.claude/agents/` (not all projects generate all agents), split or escalate to the human — never fall back to `architect` (the architect cannot write code). `performance-analyst` and `security-reviewer` are READ-ONLY reviewers — they run during `/review` (and `/audit`) on the changed files and are never assigned an implementation task. For a genuinely perf- or security-focused investigation, the diagnosis still routes to the owning stack engineer to implement the fix; the reviewer recommends, the engineer changes the code.
