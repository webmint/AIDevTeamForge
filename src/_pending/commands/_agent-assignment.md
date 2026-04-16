# Agent Assignment: File-Layer Mapping

This file is the single source of truth for assigning agents based on the files being changed. Referenced by `/breakdown`, `/fix`, and `/refactor`.

Each command reads this table and selects the agent whose row best matches the files involved. If the specific agent doesn't exist in `.claude/agents/` (not all projects generate all agents), fall back to `architect`.

## Assignment Table

| Files in... | Agent |
|-------------|-------|
| Domain models, interfaces, contracts, type definitions, architectural decisions | architect |
| State management with orchestration logic (BLoC, Redux reducers with business rules, Pinia stores with computed logic) | architect |
| API endpoints, controllers, middleware, services, server-side logic | backend-engineer |
| UI components, styles, routes, composables, stores | frontend-engineer |
| Mobile screens, navigation, native modules, platform-specific code, app lifecycle | mobile-engineer |
| Both core + UI (tightly coupled change) | architect first, then frontend-engineer |
| Bug investigation with runtime symptoms | runtime-debugger |
| Performance-critical path or optimization task | performance-analyst |
| Auth, secrets, input validation, security hardening | security-reviewer |
| Database schemas, migrations, queries, seed data | db-engineer |
| API contract design, OpenAPI specs, endpoint structure | api-designer |
| CI/CD, Docker, deployment config, infrastructure | devops-engineer |
| Data migration scripts, backward compatibility layers | migration-engineer |
| Accessibility, design system compliance, UI audit | design-auditor |
| Shared utilities, type definitions, cross-cutting concerns | architect |
| Unclear or mixed | architect (safe default) |
