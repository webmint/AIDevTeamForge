# Q11 — Claude tier model picks

`/devforge:configure` Phase 4 fills eight fields here: one model and one effort level for each of the four tiers (think / do / verify / security). Probe which model aliases this session can dispatch on FIRST, then make one AskUserQuestion call per tier — each call carries BOTH of that tier's questions. Persist a tier's two answers before issuing the next tier's call. The answers reach two file classes at `/devforge:configure` Phase 5.4, where `apply-models` rewrites the `model:` and `effort:` frontmatter of every `.claude/agents/*.md` that carries a `model_tier:` line AND of the eight pipeline commands under `.claude/commands/devforge/` that the same verb maps to a tier; until that sub-step runs, the answers change no file. On a command the `model:` line is a turn-scoped override — it applies for the rest of that command's turn, and the session's own model resumes at the next prompt.

## Availability probe — run before Q11.1

For EACH of the four Claude Code model aliases — `opus`, `sonnet`, `haiku`, `fable` — start one minimal subagent with the Agent tool, passing `model: <alias>` and the fixed prompt `Reply with the single word OK`. Give it no other task, no files, and no follow-up. (The Agent tool's per-invocation `model` parameter accepts these four aliases, a full model ID, or `inherit` — documented at `code.claude.com/docs/en/sub-agents.md`.)

- Reply is exactly `OK` → the alias is AVAILABLE in this session.
- The call errors, or the reply is anything else → the alias is UNAVAILABLE in this session. Record that and move on; a failed probe is the probe's answer, not an error to retry.

Print one information line carrying all four results, then continue — this line reports, it asks nothing:

`Model availability in this session: opus available · sonnet available · haiku available · fable unavailable`

In the same message, state in your own words what the probe settled and what it did not: it answers whether THIS session can dispatch a subagent on an alias, and nothing about the account's plan, its entitlements, or its data-retention setting. An alias that probes green may still fail later.

An alias the probe marked unavailable is NOT offered as an option in Q11.1–Q11.4. It stays reachable anyway — the free-text row AskUserQuestion adds to every question accepts any model name (see `## Pinning a model the list did not offer`). When a tier's recommended alias is one the probe marked unavailable, no option in that tier's model question carries `(Recommended)`; never move the marker to a different alias.

**When fewer than two aliases are available**, the model question cannot be asked at all — AskUserQuestion needs at least two named options. Do not ask it, and do not drop the effort question with it:

- Exactly one alias available → save it with that tier's model setter, and say in one line which alias was set and that `.devforge/lib/configure_helper set-claude-tier-<tier> <model>` followed by a re-run of `render-config` changes it later without re-running this command.
- No alias available → save no model for that tier. That tier then stays unconfigured, and there is no framework default behind it: its agents keep the `model: inherit` line they were emitted with, and no `model:` line is written into its commands, so both run on whatever model the session is on. Say that in one line, naming the same setter.
- Either way, still ask that tier's effort question — one AskUserQuestion call carrying question (b) alone.

## Q11.1 — Think tier

One AskUserQuestion call carrying both questions below. Do not split them across two calls, and do not author an `Other` option — the tool adds its own free-text row to every question.

Question (a): "Which model handles the 'think' tier (architecture, plan, breakdown)?" The options are the aliases the probe marked available, written lowercase exactly as Claude Code spells them:
- `opus` (Recommended) — deep reasoning for design-heavy work
- `sonnet` — balanced capability and cost; cheaper per token than `opus`
- `haiku` — fastest and cheapest; Claude Code lists no Haiku model as supporting effort, so this tier's answer to question (b) is silently ignored on this alias
- `fable` — highest reasoning depth; priced above `opus` per token; needs Fable access on the account and 30-day data retention. `security-reviewer` is not in this tier — Q11.4 asks for it separately, so this answer does not move it.

Question (b): "Effort for the 'think' tier?"
- `default` (Recommended) — inherit the session's own effort level; no `effort:` line is written for this tier
- `medium` — a fixed level for this tier, whatever the session is set to
- `high` — a fixed level above `medium`
- `xhigh` — a fixed level above `high`

`low` and `max` are the two remaining levels; they do not fit a four-option list, so tell the user to type either one into the free-text row verbatim. The scale runs `low` → `medium` → `high` → `xhigh` → `max`.

Save via `.devforge/lib/configure_helper set-claude-tier-think <model>` and `.devforge/lib/configure_helper set-claude-effort-think <effort>`.

## Q11.2 — Do tier

One AskUserQuestion call carrying both questions below, same shape as Q11.1.

Question (a): "Which model handles the 'do' tier (code execution, edits, refactors)?"
- `sonnet` (Recommended) — balanced capability and cost, on the tier whose turns are paid for most often
- `opus` — more capable per turn and more expensive; reach for it on unusually complex implementation work
- `haiku` — fastest and cheapest; too limited for most engineering work, and it supports no effort level (see Q11.1)
- `fable` — highest reasoning depth; priced above `opus` per token; needs Fable access on the account and 30-day data retention

Question (b): "Effort for the 'do' tier?" — same four options and the same `low` / `max` note as Q11.1.

Save via `.devforge/lib/configure_helper set-claude-tier-do <model>` and `.devforge/lib/configure_helper set-claude-effort-do <effort>`.

## Q11.3 — Verify tier

One AskUserQuestion call carrying both questions below, same shape as Q11.1.

Question (a): "Which model handles the 'verify' tier (review, audit, ac-verification)?"
- `sonnet` (Recommended) — the verify-tier agents weigh evidence and issue a verdict, and this balances that judgment work against its cost
- `opus` — deeper review, for a project where a missed finding is expensive
- `haiku` — fastest and cheapest, and it supports no effort level (see Q11.1); a poor fit for judgment work
- `fable` — highest reasoning depth; priced above `opus` per token; needs Fable access on the account and 30-day data retention

Question (b): "Effort for the 'verify' tier?" — same four options and the same `low` / `max` note as Q11.1.

Save via `.devforge/lib/configure_helper set-claude-tier-verify <model>` and `.devforge/lib/configure_helper set-claude-effort-verify <effort>`.

## Q11.4 — Security tier

One AskUserQuestion call carrying both questions below, same shape as Q11.1. This tier has exactly one member, the `security-reviewer` agent, and no command runs in it.

It is asked separately from `verify` for one reason, and you state that reason in your own words in the message that carries the question: the vendor documents that one model family's bug-finding gains EXCLUDE security-focused analysis where its cyber classifiers apply, and that a request in that shape can end in a refusal — and a reviewer that returns nothing inside `/devforge:implement`'s reviewer panel or `/devforge:grill`'s refutation pass reads as a missing verdict, not as an error. Say plainly that the choice is the user's: nothing here validates the answer, and no phase of this framework detects a verdict that never arrived.

Question (a): "Which model reviews security (the `security-reviewer` agent)?"
- `opus` (Recommended) — deep reasoning, with no documented restriction on security-focused analysis
- `sonnet` — balanced capability and cost, under the same absence of a documented restriction
- `haiku` — fastest and cheapest, and it supports no effort level (see Q11.1); a poor fit for judgment work
- `fable` — highest reasoning depth, but its documented bug-finding gains exclude security-focused analysis, and a review request can be refused outright

Question (b): "Effort for the 'security' tier?" — same four options and the same `low` / `max` note as Q11.1.

Save via `.devforge/lib/configure_helper set-claude-tier-security <model>` and `.devforge/lib/configure_helper set-claude-effort-security <effort>`.

## Pinning a model the list did not offer

AskUserQuestion adds a free-text row to every question; a user who takes it types a model name instead of picking an alias. Before saving that answer, do two things in one message:

1. List on one line the full model IDs you can name in this session, labelled `as known to this session — unverified`. If you cannot name any, say so in one line instead and carry on. The list is a run-time convenience only: it is never recorded anywhere, and only the value the user actually chooses is saved.
2. Say that a pinned ID is the user's to maintain — nothing here checks that a pinned model exists, is entitled, or is current, and nothing will ever report one as stale.

Then save the typed value with that tier's model setter, unchanged.

## Saving the answers

`.devforge/lib/configure_helper set-claude-tier-<tier> <value>` — `<tier>` is `think`, `do`, `verify` or `security`. A value matching `opus`, `sonnet`, `haiku` or `fable` case-insensitively is normalized to lowercase; any other non-empty value is stored verbatim as a pinned model ID.

`.devforge/lib/configure_helper set-claude-effort-<tier> <value>` — the value must be one of `default`, `low`, `medium`, `high`, `xhigh`, `max`. The setter exits 2 on anything else and writes nothing: surface its stderr and ask that tier's effort question again rather than substituting a value of your own.

Save a tier's two answers before issuing the next tier's call, so an interrupted run keeps every answer already collected.

## Recommendations

Recommended picks: `think = opus`, `do = sonnet`, `verify = sonnet`, `security = opus`, and effort `default` on all four tiers. These are recommendations and nothing more — the framework applies no model of its own, so a tier nobody answers stays unconfigured rather than falling back to a value this file names.

- **`think = opus`** — it stays the recommendation until a measured comparison inside this pipeline moves it, so recommending it is not evidence that `opus` is the better choice here; it is the absence of evidence that the pricier `fable` is.
- **`do = sonnet`** — this tier carries the per-task execution work, so its cost per turn is the one paid most often, and `sonnet` balances that against the capability the work needs.
- **`verify = sonnet`** — the verify-tier agents weigh evidence rather than run mechanical checks, and judgment is not the tier to economize on.
- **`security = opus`** — it is the deep-reasoning alias carrying no documented restriction on security-focused analysis, which is the whole reason this tier is asked separately.
- **effort `default`** — it inherits the session's own effort level, so the framework never overrides a level the user set deliberately, and it tracks whatever levels the chosen model supports instead of pinning one the model may not have.

Six bounds this command does not close, and none of them is a defect to report:

- **There is no built-in model default anywhere in this framework.** A tier left unanswered leaves its agents on the `model: inherit` line they were emitted with and writes no `model:` line into its commands, so both run on the model the session is already on.
- **Nothing checks the security answer.** A model that declines security-focused analysis returns no verdict rather than an error, and no phase of this framework detects the verdict that never arrived — Q11.4 replaces a guarantee with an informed choice, and that is a real loss of protection.
- **Nothing validates a model against an effort level.** Claude Code falls back to the highest supported level at or below the one set, and it does so silently (documented at `code.claude.com/docs/en/model-config.md` for the session's own effort setting, and not documented either way for the `effort:` frontmatter line this command writes), so an unsupported combination looks exactly like success. No phase of `/devforge:configure` detects it.
- **A green probe is not an entitlement guarantee.** It says this session could dispatch a subagent on that alias — nothing about the account's plan, its data-retention setting, or whether the alias still works tomorrow.
- **A pinned model ID is the user's to maintain.** Nothing in this framework reports one as stale, now or later.
- **Whether an agent follows a command's model override is not documented.** An agent carrying `model: inherit` takes the main conversation's model (documented at `code.claude.com/docs/en/sub-agents.md`); what that resolves to inside a command turn that carries its own `model:` override is stated nowhere, so do not tell the user which model such an agent will run on.
