# Q12 — AC verification mode

`/devforge:configure` Phase 4 asks one AskUserQuestion to pick the acceptance-criteria verification mode, then conditionally asks three follow-up questions (Q12.1 / Q12.2 / Q12.3) when the user selects `runtime-assisted`. Persist each answer via its setter before issuing the next question.

**When the user hands a follow-up back to you.** At a Q12.1 / Q12.2 / Q12.3 `Confirm` / `Override` question, treat a reply that hands the choice back to you ("you decide", "up to you", or the same in any language) as `Confirm`: save the detected value and name it in `/devforge:configure` Phase 7's delegated-values lines. At a plain free-text prompt in those three follow-ups, such a reply is not a URL or a command — never pass it to a setter; that prompt runs only when detection found nothing or the user overrode the detected value, so there is no value to apply on their behalf: ask the same prompt once more, and if the second reply again gives no value, end the turn without saving that field, telling the user to re-run `/devforge:configure` once they know it.

## Q12 — Mode selection

Use AskUserQuestion: "How should /devforge:verify check acceptance criteria?"
- `code-only` (Recommended) — read code; no test execution; no runtime probing
- `tests` — run tests; no runtime probing
- `runtime-assisted` — run app + probe via Chrome DevTools MCP / API calls
- `off` — skip behavioral AC verification; code-reading floor only (advisory, non-blocking)

Save via `.devforge/lib/configure_helper set-ac-verification-mode <choice>`.

If the user hands this choice back to you ("you decide", "up to you", or the same in any language — including one typed as free text instead of an option), save `code-only` and name it in `/devforge:configure` Phase 7's delegated-values lines.

### Mode taxonomy

- **`code-only`** — `/devforge:verify` reads task output files, source code, and the spec to check that acceptance criteria are mechanically satisfied. No subprocess execution, no runtime probing. Default for projects without a stable test suite or running app.
- **`tests`** — `/devforge:verify` runs the project's test suite (per-package, scope-aware) and checks that tests pass alongside reading code. Suitable for projects with reliable test coverage.
- **`runtime-assisted`** — `/devforge:verify` boots the app (or assumes it is already running) and probes via Chrome DevTools MCP and/or API calls to validate user-facing behavior. Suitable for web apps with a stable dev server.
- **`off`** — `/devforge:verify` skips behavioral AC verification (no browser/API probing, no test execution) but still applies a code-reading floor: it reads the changed files and produces per-AC code-only statuses, noted as code-verified in the verdict (advisory, not blocking). Pick this when the project has no running app and no test suite, or when behavioral AC verification is owned by an external pipeline.

If the user picks `code-only`, `tests`, or `off`, Q12.1 / Q12.2 / Q12.3 are NOT asked — Phase 4 advances directly to Q13.

If the user picks `runtime-assisted`, proceed to the conditional follow-up triple below.

## Q12.1 — Runtime URL (only when mode == `runtime-assisted`)

Phase 2 detection populated `AC_RUNTIME_URL` from matched config files (e.g., `vite.config.*` `server.host` + `server.port`). Pre-fill the prompt with that detected value.

If detection produced a non-empty value, use AskUserQuestion (substitute `<value>` with the Phase 2 composed URL): "Detected runtime URL: `<value>`. Confirm or override?"
- `Confirm` — use the detected URL
- `Override` — let me type a different URL

If the user picks `Confirm`, save via `.devforge/lib/configure_helper set-ac-runtime-url <value>` using the Phase 2 composed value. If the user picks `Override`, follow up with a plain free-text prompt: "What's the runtime URL?", then save via `.devforge/lib/configure_helper set-ac-runtime-url <answer>`.

If detection produced an empty value, skip the AskUserQuestion and ask plainly: "What's the runtime URL? (e.g., `http://localhost:5173`)", then save via `.devforge/lib/configure_helper set-ac-runtime-url <answer>`.

## Q12.2 — API base (only when mode == `runtime-assisted`)

Phase 2 detection populated `AC_RUNTIME_API_BASE` from matched `.env*` files (e.g., `VITE_API_URL`).

If detection produced a non-empty value, use AskUserQuestion (substitute `<value>` with the Phase 2 composed URL): "Detected API base: `<value>`. Confirm or override?"
- `Confirm` — use the detected API base
- `Override` — let me type a different URL

If the user picks `Confirm`, save via `.devforge/lib/configure_helper set-ac-runtime-api-base <value>` using the Phase 2 composed value. If the user picks `Override`, follow up with a plain free-text prompt: "What's the API base URL?", then save via `.devforge/lib/configure_helper set-ac-runtime-api-base <answer>`.

If detection produced an empty value, skip the AskUserQuestion and ask plainly: "What's the API base URL? (e.g., `http://localhost:3000/api`)", then save via `.devforge/lib/configure_helper set-ac-runtime-api-base <answer>`.

## Q12.3 — CLI command (only when mode == `runtime-assisted`)

Phase 2 detection populated `AC_RUNTIME_CLI_COMMAND` from manifest `scripts.dev` or `scripts.start`.

If detection produced a non-empty value, use AskUserQuestion (substitute `<value>` with the Phase 2 composed command): "Detected runtime CLI command: `<value>`. Confirm or override?"
- `Confirm` — use the detected command
- `Override` — let me type a different command

If the user picks `Confirm`, save via `.devforge/lib/configure_helper set-ac-runtime-cli-command <value>` using the Phase 2 composed value. If the user picks `Override`, follow up with a plain free-text prompt: "What command starts the dev server?", then save via `.devforge/lib/configure_helper set-ac-runtime-cli-command <answer>`.

If detection produced an empty value, skip the AskUserQuestion and ask plainly: "What command starts the dev server? (e.g., `npm run dev`)", then save via `.devforge/lib/configure_helper set-ac-runtime-cli-command <answer>`.
