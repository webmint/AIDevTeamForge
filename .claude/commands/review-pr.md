# /review-pr — Strict Review of a Pull Request Without a Spec

Ad-hoc review of a pull request (merge request) that never went through the spec cycle: no spec in `specs/`, no per-task code review, no constitution enforcement by `/execute-task`. It launches the same agents as `/review` plus a constitution and architecture pass by the **code-reviewer**, and it reviews more strictly than `/review`: the author's skill level is unknown, so nothing in the diff gets the benefit of the doubt.

Not part of the workflow chain and not run by `/conduct`. Use `/review` for a feature built with `/specify` → `/execute-task`.

## Usage
```
/review-pr <PR number | PR URL | issue key>
```

## Arguments
- `$ARGUMENTS` — one of:
  - a PR number (`42`);
  - a PR URL of this project's repository: its last numeric path segment is the PR number (`…/pull/42`, `…/merge_requests/42`);
  - an issue key: the whole argument matches `ISSUE_KEY_PATTERN` (`ABC-123`, or `#123` for GitHub Issues); resolved to a PR with `PR_SEARCH_COMMAND`.
  - Empty, or anything else: ask the user for the PR number.

## Configuration

All keys live in `.claude/project-config.json` and are set by `/setup-wizard` (Question 11) or by hand. A missing key, `""` and `"N/A"` all mean the default.

| Key | Meaning | Default |
|-----|---------|---------|
| `PR_VIEW_COMMAND` | Prints the PR's title, description, head branch, base branch, URL and head commit. `<N>` = PR number | — (required) |
| `PR_DIFF_COMMAND` | Prints the PR's diff. `<N>` = PR number | — (required) |
| `PR_SEARCH_COMMAND` | Lists the PRs that name an issue key, with number and title. `<KEY>` = the key | none: an issue-key argument is not supported |
| `PR_HEAD_REF` | Remote ref that holds the PR's head commit. `<N>` = PR number | none: agents review the diff only |
| `PR_REMOTE` | Remote that holds the PRs and their base branches (`upstream` in a fork workflow) | `PUSH_REMOTE`, else `origin` |
| `ISSUE_TRACKER` | `jira`, `github` or `none` | `none` |
| `ISSUE_KEY_PATTERN` | Extended regex of an issue key | `[A-Z][A-Z0-9]+-[0-9]+` (jira), `#[0-9]+` (github), none (`none`) |
| `JIRA_MCP_SERVER` | Name of the MCP server that serves Jira, as in its tool names `mcp__<server>__…` | `atlassian` |
| `JIRA_SITE` | Jira site host (`acme.atlassian.net`) or cloudId, for a server that needs one | the only site the server can access |

Presets the wizard offers (any host works with its own commands):

| Host | `PR_VIEW_COMMAND` | `PR_DIFF_COMMAND` | `PR_SEARCH_COMMAND` | `PR_HEAD_REF` |
|------|-------------------|-------------------|---------------------|---------------|
| GitHub (`gh`) | `gh pr view <N> --json number,title,body,headRefName,headRefOid,baseRefName,url,closingIssuesReferences` | `gh pr diff <N>` | `gh pr list --search "<KEY> in:title" --state all --json number,title,url` (with GitHub Issues: `in:title,body`) | `pull/<N>/head` |
| GitLab (`glab`) | `glab mr view <N> --output json` | `glab mr diff <N>` | `glab mr list --search "<KEY>" --all` | `merge-requests/<N>/head` |

## Output Discipline
- No preamble and no narration of steps: produce the report.
- No praise, no "overall looks good", no hedging. "None" where a section has no findings.
- Every finding: severity, `file:line`, the defect, a concrete fix. PHASE 6's format exactly.

## PHASE 1: Load Context

**Source Root**: Read `.claude/project-config.json` for `SOURCE_ROOT`. When it is not `.` (wrapper mode), run every git, PR and issue command inside that directory and tell the agents that changed paths are relative to it.

**Cleanup on every stop**: once step 5 has created refs under `refs/forge/review-pr/`, delete them (`git update-ref -d <ref>`) before any later stop, as PHASE 6 does.

1. **Commands**: when `PR_VIEW_COMMAND` or `PR_DIFF_COMMAND` is unset, stop: "⛔ /review-pr needs `PR_VIEW_COMMAND` and `PR_DIFF_COMMAND` in `.claude/project-config.json` (re-run `/setup-wizard` or set them by hand; presets are in `.claude/commands/review-pr.md`)."
2. **Constitution**: read `constitution.md` in full.
   - **Guard**: if it contains `_Run /constitute to populate_`, stop: "⛔ constitution.md has not been populated yet. Run `/constitute` before using `/review-pr`."
3. **Resolve the PR number** from `$ARGUMENTS`:
   - A number or a URL: use the number.
   - An issue key: when `PR_SEARCH_COMMAND` is unset, ask for the PR number. Otherwise run it with `<KEY>` replaced by the key (never by other text of the argument). One PR: use it. Several: list them and ask which one. None: say so and stop. Never guess a number.
4. **Load the PR**: run `PR_VIEW_COMMAND` and `PR_DIFF_COMMAND` with `<N>` replaced. Take the title, description, head branch, base branch, URL and head commit from the view output, and the changed files from the diff (deduplicated).
   - A URL argument: when the view's URL is not the argument's URL (host and path up to the number), stop: the URL belongs to another repository, and the commands review this project's repository only.
   - Read the diff from the command's output. **Never write it to an intermediate file** (`/tmp/*.diff` or similar) and read it back: a saved diff is stale the moment the PR gets a new commit, and nothing invalidates it.
   - A diff too large for one output: with the PR head fetched (step 5), read it per path with `git diff <merge-base> refs/forge/review-pr/<N> -- <paths>`. Without it, re-run `PR_DIFF_COMMAND` piped through `sed -n '<a>,<b>p'` for consecutive line ranges (each run is fresh); stop at what fits and list the remaining files under "Not reviewed".
5. **Fetch the PR head** (when `PR_HEAD_REF` is set; `<remote>` = `PR_REMOTE`):
   ```
   git fetch <remote> +<PR_HEAD_REF>:refs/forge/review-pr/<N> +refs/heads/<base branch>:refs/forge/review-pr/<N>-base
   git merge-base refs/forge/review-pr/<N> refs/forge/review-pr/<N>-base
   ```
   Agents read a changed file at the PR's head with `git show refs/forge/review-pr/<N>:<path>` and a scoped diff with `git diff <merge-base> refs/forge/review-pr/<N> -- <paths>`. The working tree is not the PR: use it to search for existing patterns, never as the PR's version of a changed file. A failed fetch or an empty merge-base (shallow clone): delete the refs, continue with the diff only, and say so under "Not reviewed".
6. **Issue** (when `ISSUE_TRACKER` is not `none`):
   - Candidates, in order: the key from step 3; for `github`, the issues the view lists as closed by the PR (`closingIssuesReferences`) and `Closes|Fixes|Resolves #<n>` in the description; then every match of `ISSUE_KEY_PATTERN` in the title, the head branch name and the description. Try them in order: the first one the tracker returns is the issue. A key the tracker does not know (`SHA-256`, `UTF-8`) is skipped.
   - `jira`: use the tool of the `mcp__<JIRA_MCP_SERVER>__` server that reads one issue by key (on the Atlassian server: `getJiraIssue`). When that tool needs a cloudId, take it from `JIRA_SITE`, else from the server's list of accessible sites (one site: use it; several: ask which). When the server's tools are not available in this session, continue without the issue and say so under "Not reviewed".
   - `github`: `gh issue view <number> --json title,body`.
   - The issue's summary and description are the acceptance criteria the PR must satisfy.
   - No candidate resolves: a **Warning** (missing traceability) in the Constitution & Architecture section. Never guess a key.
   - `ISSUE_TRACKER` is `none`: the PR description is the only statement of intent; no traceability finding.
7. Read `.claude/memory/MEMORY.md` for pitfalls in the touched areas.

## PHASE 2: Constitution & Architecture Review

`/review` does not run this pass: there `/execute-task` already enforced the constitution per task. Nothing did here.

Launch the **code-reviewer** agent (read `.claude/agents/code-reviewer.md` and include its full content as the opening section of the prompt). Give it:
1. The diff, the changed files, and how to read them at the PR head (PHASE 1 step 5).
2. The issue's summary and description as the specification, or the PR description when there is no issue.
3. `constitution.md` in full.
4. The checklist `.claude/checklists/task-review.md`, when it exists and its `**Gate**:` line does not say `off`: report every failed item by its id.
5. Instruction: "Run your whole checklist at maximum strictness. The author's skill level is unknown: verify every claim against the file content at the PR head, not against the diff's framing. For architecture and patterns, search the rest of the repository (not only the changed files) for existing code that does the same or a structurally similar thing as anything this PR adds. A new way of doing something the repository already has a pattern for is at least a Warning, even when the new code works. A hand-written type that overlaps a generated or shared type is Critical. Constitution violations are Critical."

## PHASE 3: Security Review

If `.claude/agents/security-reviewer.md` exists, launch the **security-reviewer** agent (its full content opens the prompt). Give it the diff, the changed files and how to read them at the PR head, the issue or PR description, the constitution's security rules and the relevant MEMORY.md entries. Instruction: "Constitution violations are Critical regardless of other severity factors. The author's skill level is unknown: verify, do not trust the diff's intent."

If the agent doesn't exist, note in the report: _Skipped — no security-reviewer agent configured._

## PHASE 4: Performance Review

If `.claude/agents/performance-analyst.md` exists, launch the **performance-analyst** agent with the diff, the changed files and how to read them at the PR head, the issue or PR description (performance-relevant criteria) and the MEMORY.md anti-patterns. If it doesn't exist, skip this phase silently.

## PHASE 5: Test Assessment

If `.claude/agents/qa-engineer.md` exists, launch the **qa-engineer** agent with the diff, the changed files and how to read them at the PR head, the issue as acceptance criteria (or the PR description), the PR's test files, and the checklist `.claude/checklists/test-lens.md` when it exists and its `**Gate**:` line does not say `off`. It assesses coverage gaps, untested criteria and test strength (would each test fail if the change were broken). It does not write tests. If it doesn't exist, skip this phase silently.

## PHASE 6: Report

Delete the refs step 5 created (`git update-ref -d refs/forge/review-pr/<N>` and `…/<N>-base`), then print:

```
PR #<N> — <title> — <issue key, or "no issue">
<URL> @ <head commit, short>

Code review: Critical <n> | Warning <n> | Info <n>
Security: Critical <n> | High <n> | Medium <n> | Info <n>
Performance: High <n> | Medium <n> | Low <n>

### Constitution & Architecture
- [Critical] file:line — <defect>. Fix: <concrete fix>.

### Security
- [High] file:line — <defect>. Fix: <concrete fix>.

### Performance
- [Medium] file:line — <defect>. Fix: <concrete fix>.

### Tests
- Criteria covered: <n of m>. Gaps: <list>.

### Not reviewed
- <files left out, a failed fetch, an issue that could not be read; "None">

Verdict: APPROVE | APPROVE WITH WARNINGS | REQUEST CHANGES | BLOCK
```

- `BLOCK`: any Critical.
- `REQUEST CHANGES`: any Warning, High or Medium finding that is cheap to fix before merge.
- `APPROVE WITH WARNINGS`: the remaining findings belong in follow-up issues; say why for each.
- `APPROVE`: no findings above Info / Low.

The review holds for the head commit in the header only: a new commit to the PR needs a new run.

Never soften a verdict to make the review feel less harsh.

## IMPORTANT RULES

1. **Agents run in parallel**: PHASES 2–5 are independent; launch them together.
2. **No downgrades by you**: never lower an agent's severity when presenting the report. If you disagree with a rating, add a note; do not change it.
3. **Constitution violations are always Critical.**
4. **A divergent new pattern is at least a Warning**, even in a small bug fix: reuse was cheap, and a minimal-change framing does not excuse leaving the codebase less consistent.
5. **Read-only**: no edits, no commits, no comments on the PR. The only writes are the fetched refs, deleted before the command ends.
6. **Chat only**: the report is not written to `specs/` (there is no spec). Save it only when the user asks.
7. **Configured commands only**: run the PR and issue commands from `.claude/project-config.json` and the tools they name; never fall back to a host or tracker the project did not configure.
