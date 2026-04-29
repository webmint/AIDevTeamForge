# Phase 2 — Questions

This reference defines the interactive Q&A phase of `/setup-wizard`. Read `.devforge/detection_report.yaml` first — many questions confirm or override values stored there. Walk through all questions in order. As each answer is determined, save it immediately via the appropriate `.devforge/lib/wizard_render` setter subcommand before issuing the next question.

## Q1: Project Name (REQUIRED)

The project's display name.

**If `packages_detected[0]` exists in `.devforge/detection_report.yaml` and a non-empty name can be extracted from its manifest:** read the manifest file `packages_detected[0].manifest` from directory `packages_detected[0].path` and extract the project name using ecosystem knowledge (e.g. `name` in `package.json`, `[package].name` in `Cargo.toml`, `module` in `go.mod`, `app` in `mix.exs`). Normalize the extracted value: if it's a path-shaped identifier (Go's `github.com/acme/backend`), take the last path segment; if it's an atom with a leading `:` (Elixir), drop the colon; otherwise pass through unchanged. Then use AskUserQuestion: "I found the project name `<detected-name>` in `<manifest-path>`. Confirm or override?"
- `Confirm` (Recommended)
- `Override` — let me type a different name

On `Confirm`, the detected name is the answer. On `Override`, follow up with a plain free-text prompt: "What is this project called?". The user's reply is the answer.

**Otherwise** (no `packages_detected[0]`, or no name could be extracted): use a plain free-text prompt: "What is this project called?". The user's reply is the answer.

Once the answer is determined, save it: `.devforge/lib/wizard_render set-project-name <answer>`.

## Q2: Project Description (REQUIRED)

A 1-3 sentence description of what the project does and who it's for.

**If a README file exists at the `project_root` recorded in `.devforge/detection_report.yaml` and contains a meaningful description (not just a placeholder heading or scaffolded boilerplate from `npm init`-style defaults):** read the README and extract the first paragraph or summary section, capped at roughly three sentences. Then issue a plain prose prompt that includes the extracted text:

"I found this in `<readme-path>`:

> <extracted-text>

Reply 'yes' to use this as the project description, or write a 1-3 sentence replacement."

If the user's reply is exactly 'yes' (case-insensitive), the extracted README text is the answer. Otherwise, the user's reply is the answer.

**Otherwise** (no README at `project_root`, or the README is empty or boilerplate-only): use a plain free-text prompt: "Describe this project in 1-3 sentences — what does it do, who is it for?". The user's reply is the answer.

Once the answer is determined, save it: `.devforge/lib/wizard_render set-project-description <answer>`.

## Q3: Project Type (REQUIRED)

The project's primary category from a closed 13-item taxonomy.

**If `.devforge/detection_report.yaml` fields support a confident mapping to one of the 13 categories in the taxonomy:** apply ecosystem knowledge to pick the best-fit category and identify the 1-3 most representative signals that justified the call. Then use AskUserQuestion: "Based on detected `<key-signals>`, this looks like a `<proposed-type>`. Confirm, or browse the full list?"
- `Confirm` (Recommended)
- `Browse the full list` — see all categories or describe your own

On `Confirm`, the proposed type is the answer. On `Browse the full list`, follow up with this prose prompt:

**Otherwise** (no clear signal in `detection_report.yaml` — empty project, no matching framework patterns): skip the AskUserQuestion and issue this prose prompt directly:

"Which category fits this project? Pick a name from the list, or describe your own (e.g., 'firmware', 'browser extension', 'Slack bot'):

- Frontend / web application
- Backend API / service
- Full-stack web application
- Mobile application (native or cross-platform)
- Desktop application (Electron, Tauri, native)
- CLI tool / script
- Library / package / SDK
- Plugin / extension / add-on
- Data pipeline / ETL / batch job
- ML / data science / AI model
- Game
- Infrastructure-as-code / config management
- Documentation / static site"

The user's reply is the answer (verbatim — whether they typed a canonical category name or a custom description).

Once the answer is determined, save it: `.devforge/lib/wizard_render set-project-type <answer>`.

## Q4: Architecture (REQUIRED)

The project's overall architectural pattern.

**If `architecture_shape` is set to a non-null, non-`"N/A"` value in `.devforge/detection_report.yaml`:** use AskUserQuestion: "Detected architecture: `<architecture_shape>`. Confirm or override?"
- `Confirm` (Recommended)
- `Override` — let me describe differently

On `Confirm`, the detected `architecture_shape` is the answer. On `Override`, follow up with a plain free-text prompt: "Describe your project's architecture (e.g., 'Clean Architecture', 'Hexagonal', 'feature-modular-monorepo'):". The user's reply is the answer.

**Otherwise** (`architecture_shape` is null or `"N/A"` in `.devforge/detection_report.yaml`): use a plain free-text prompt: "What architecture pattern does this project follow? (e.g., 'Clean Architecture', 'Hexagonal', 'MVC')". The user's reply is the answer.

Once the answer is determined, save it: `.devforge/lib/wizard_render set-architecture <answer>`.

## Q5: Error Handling (REQUIRED)

The project's error handling library and pattern.

**If `error_handling_library` is set to a non-null, non-`"N/A"` value in `.devforge/detection_report.yaml`:** use AskUserQuestion: "Detected error handling library: `<error_handling_library>`. Confirm or describe differently?"
- `Confirm` (Recommended)
- `Override` — let me describe differently

On `Confirm`, the detected `error_handling_library` is the answer. On `Override`, follow up with a plain free-text prompt: "Describe your project's error handling (e.g., 'purify-ts Either', 'try/catch', 'neverthrow Result'):". The user's reply is the answer.

**Otherwise** (`error_handling_library` is null or `"N/A"` in `.devforge/detection_report.yaml`): use a plain free-text prompt: "How does this project handle errors? (e.g., 'try/catch', 'Result type', 'language default')". The user's reply is the answer.

Once the answer is determined, save it: `.devforge/lib/wizard_render set-error-handling <answer>`.

## Q6: Runtime URL (OPTIONAL)

The URL where the project runs (dev server, staging, etc.).

**If `runtime_url_value` is set to a non-null, non-`"N/A"` value in `.devforge/detection_report.yaml`:** use AskUserQuestion: "Detected runtime URL: `<runtime_url_value>`. Confirm or override?"
- `Confirm` (Recommended)
- `Override` — let me enter a different URL

On `Confirm`, the detected `runtime_url_value` is the answer. On `Override`, follow up with a plain free-text prompt: "What's the project's runtime URL? (e.g., 'http://localhost:3000', 'https://staging.example.com'):". The user's reply is the answer.

**Otherwise** (`runtime_url_value` is null or `"N/A"` in `.devforge/detection_report.yaml` — backend service, library, CLI, etc.): use a plain free-text prompt: "What's the project's runtime URL? Or 'N/A' if this project has no runtime URL (backend service, library, CLI).". The user's reply is the answer. If the user replies `'N/A'`, save it verbatim — the setter accepts the sentinel string.

Once the answer is determined, save it: `.devforge/lib/wizard_render set-runtime-url <answer>`.

## Q7: API Layer (OPTIONAL)

The project's API style.

**If `frameworks[]` or `packages_detected[].manifest` dev/prod dependencies in `.devforge/detection_report.yaml` contain signals that map to a clear API style (apply ecosystem knowledge: FastAPI/Express/Rails/Django/Flask → REST; apollo-server/@apollo/client/urql/relay → GraphQL; @trpc/server/@trpc/client → tRPC; @grpc/grpc-js/grpcio → gRPC; socket.io/ws → WebSocket; etc.):** use AskUserQuestion: "Detected API layer: `<detected-api>`. Confirm or override?"
- `Confirm` (Recommended)
- `Override` — let me name a different style

On `Confirm`, the detected API style is the answer. On `Override`, follow up with a plain free-text prompt: "What's the project's API layer? (e.g., 'REST', 'GraphQL', 'tRPC', 'gRPC', 'WebSocket', 'SOAP', 'N/A'):". The user's reply is the answer.

**Otherwise** (no API framework signals in `frameworks[]` or `packages_detected[].manifest`): use a plain free-text prompt: "What's the project's API layer? (e.g., 'REST', 'GraphQL', 'tRPC', 'gRPC', 'WebSocket', 'SOAP', or 'N/A' if no API layer):". The user's reply is the answer.

Once the answer is determined, save it: `.devforge/lib/wizard_render set-api-layer <answer>`.

## Q8: Testing Framework (OPTIONAL)

The project's testing framework.

**If `primary_language` alone determines the test runner (Go → `go test`; Rust → `cargo test`) OR `packages_detected[].manifest` dev-dependencies in `.devforge/detection_report.yaml` contain a recognized test framework (apply ecosystem knowledge: pytest in pyproject.toml [tool.pytest] or dev-deps → pytest; vitest/jest in dev-dependencies → that framework; JUnit in Maven/Gradle → JUnit; RSpec in Gemfile → RSpec; etc.):** use AskUserQuestion: "Detected testing framework: `<detected-framework>`. Confirm or override?"
- `Confirm` (Recommended)
- `Override` — let me name a different framework

On `Confirm`, the detected framework is the answer. On `Override`, follow up with a plain free-text prompt: "What's the project's testing framework? (e.g., 'pytest', 'vitest', 'jest', 'go test', 'cargo test', 'JUnit', 'RSpec'):". The user's reply is the answer.

**Otherwise** (no test framework detectable — no test deps in dev-dependencies, project has no test setup): use a plain free-text prompt: "What's the project's testing framework? (e.g., 'pytest', 'vitest', 'jest', 'go test', 'cargo test', 'JUnit', 'RSpec', or 'N/A' if no tests):". The user's reply is the answer.

Once the answer is determined, save it: `.devforge/lib/wizard_render set-testing <answer>`.

## Q9: Workflow Enforcement (REQUIRED)

The strictness of approval gates and verification across the project's workflow.

Use AskUserQuestion: "How strict should workflow enforcement be?"
- `Strict` (Recommended) — approval required at every phase gate; verification runs after every code-writing step
- `Moderate` — approval at spec and task-breakdown gates; verification runs automatically after code-writing steps
- `Light` — approval only at the initial spec; verification runs after code-writing steps, no other interactive gates

The selected option's label is the answer (verbatim). On the auto-injected Other affordance, the user's typed text is the answer.

Once the answer is determined, save it: `.devforge/lib/wizard_render set-workflow-enforcement <answer>`.

## Q10: AI Attribution (REQUIRED)

Whether commits include AI co-author attribution.

Use AskUserQuestion: "Should commits include AI co-author attribution?"
- `No` (Recommended) — commits have no AI attribution
- `Yes` — commits include a `Co-Authored-By:` trailer attributing the AI assistant

The selected option's label is the answer (verbatim). On the auto-injected Other affordance, the user's typed text is the answer.

Once the answer is determined, save it: `.devforge/lib/wizard_render set-ai-attribution <answer>`.
