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
