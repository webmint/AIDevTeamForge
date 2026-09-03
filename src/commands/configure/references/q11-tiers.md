# Q11 — Claude tier model picks

`/devforge:configure` Phase 4 fills six fields here: one model and one effort level for each of the three agent tiers (think / do / verify). Probe which model aliases this session can dispatch on FIRST, then make one AskUserQuestion call per tier — each call carries BOTH of that tier's questions. Persist a tier's two answers before issuing the next tier's call. The answers reach the emitted agents at Phase 5.4, where `apply-agent-models` rewrites each `.claude/agents/*.md` `model:` and `effort:` frontmatter line from them; until that sub-step runs, the answers change no agent file.

## Availability probe — run before Q11.1

For EACH of the four Claude Code model aliases — `opus`, `sonnet`, `haiku`, `fable` — start one minimal subagent with the Agent tool, passing `model: <alias>` and the fixed prompt `Reply with the single word OK`. Give it no other task, no files, and no follow-up. (The Agent tool's per-invocation `model` parameter accepts these four aliases, a full model ID, or `inherit` — documented at `code.claude.com/docs/en/sub-agents.md`.)

- Reply is exactly `OK` → the alias is AVAILABLE in this session.
- The call errors, or the reply is anything else → the alias is UNAVAILABLE in this session. Record that and move on; a failed probe is the probe's answer, not an error to retry.

Print one information line carrying all four results, then continue — this line reports, it asks nothing:

`Model availability in this session: opus available · sonnet available · haiku available · fable unavailable`

In the same message, state in your own words what the probe settled and what it did not: it answers whether THIS session can dispatch a subagent on an alias, and nothing about the account's plan, its entitlements, or its data-retention setting. An alias that probes green may still fail later.

An alias the probe marked unavailable is NOT offered as an option in Q11.1–Q11.3. It stays reachable anyway — the free-text row AskUserQuestion adds to every question accepts any model name (see `## Pinning a model the list did not offer`). When a tier's recommended alias is one the probe marked unavailable, no option in that tier's model question carries `(Recommended)`; never move the marker to a different alias.

**When fewer than two aliases are available**, the model question cannot be asked at all — AskUserQuestion needs at least two named options. Do not ask it, and do not drop the effort question with it:

- Exactly one alias available → save it with that tier's model setter, and say in one line which alias was set and that `.devforge/lib/configure_helper set-claude-tier-<tier> <model>` followed by a re-run of `render-config` changes it later without re-running this command.
- No alias available → save no model for that tier; the framework's built-in tier default stays in force. Say that in one line, naming the same setter.
- Either way, still ask that tier's effort question — one AskUserQuestion call carrying question (b) alone.

## Q11.1 — Think tier

One AskUserQuestion call carrying both questions below. Do not split them across two calls, and do not author an `Other` option — the tool adds its own free-text row to every question.

Question (a): "Which model handles the 'think' tier (architecture, plan, breakdown)?" The options are the aliases the probe marked available, written lowercase exactly as Claude Code spells them:
- `opus` (Recommended) — deep reasoning for design-heavy work; the framework's built-in default for this tier
- `sonnet` — balanced capability and cost; cheaper per token than `opus`
- `haiku` — fastest and cheapest; Claude Code lists no Haiku model as supporting effort, so this tier's answer to question (b) is silently ignored on this alias
- `fable` — highest reasoning depth; priced above `opus` per token; needs Fable access on the account and 30-day data retention. `security-reviewer` runs on `opus` whatever this answer is — the framework pins that one agent, and this tier's answer does not move it.

Question (b): "Effort for the 'think' tier?"
- `default` (Recommended) — inherit the session's own effort level; this tier's agents carry no `effort:` line
- `medium` — a fixed level for this tier's agents, whatever the session is set to
- `high` — a fixed level above `medium`
- `xhigh` — a fixed level above `high`

`low` and `max` are the two remaining levels; they do not fit a four-option list, so tell the user to type either one into the free-text row verbatim. The scale runs `low` → `medium` → `high` → `xhigh` → `max`.

Save via `.devforge/lib/configure_helper set-claude-tier-think <model>` and `.devforge/lib/configure_helper set-claude-effort-think <effort>`.

## Q11.2 — Do tier

One AskUserQuestion call carrying both questions below, same shape as Q11.1.

Question (a): "Which model handles the 'do' tier (code execution, edits, refactors)?"
- `sonnet` (Recommended) — balanced capability and cost; the framework's built-in default for this tier
- `opus` — more capable per turn and more expensive; reach for it on unusually complex implementation work
- `haiku` — fastest and cheapest; too limited for most engineering work, and it supports no effort level (see Q11.1)
- `fable` — highest reasoning depth; priced above `opus` per token; needs Fable access on the account and 30-day data retention

Question (b): "Effort for the 'do' tier?" — same four options and the same `low` / `max` note as Q11.1.

Save via `.devforge/lib/configure_helper set-claude-tier-do <model>` and `.devforge/lib/configure_helper set-claude-effort-do <effort>`.

## Q11.3 — Verify tier

One AskUserQuestion call carrying both questions below, same shape as Q11.1.

Question (a): "Which model handles the 'verify' tier (review, audit, ac-verification)?"
- `sonnet` (Recommended) — the verify-tier agents weigh evidence and issue a verdict; this is the framework's built-in default for the tier
- `opus` — deeper review, for a project where a missed finding is expensive
- `haiku` — fastest and cheapest, and it supports no effort level (see Q11.1); a poor fit for judgment work
- `fable` — highest reasoning depth; priced above `opus` per token; needs Fable access on the account and 30-day data retention

Question (b): "Effort for the 'verify' tier?" — same four options and the same `low` / `max` note as Q11.1.

Save via `.devforge/lib/configure_helper set-claude-tier-verify <model>` and `.devforge/lib/configure_helper set-claude-effort-verify <effort>`.

## Pinning a model the list did not offer

AskUserQuestion adds a free-text row to every question; a user who takes it types a model name instead of picking an alias. Before saving that answer, do two things in one message:

1. List on one line the full model IDs you can name in this session, labelled `as known to this session — unverified`. If you cannot name any, say so in one line instead and carry on. The list is a run-time convenience only: it is never recorded anywhere, and only the value the user actually chooses is saved.
2. Say that a pinned ID is the user's to maintain — nothing here checks that a pinned model exists, is entitled, or is current, and nothing will ever report one as stale.

Then save the typed value with that tier's model setter, unchanged.

## Saving the answers

`.devforge/lib/configure_helper set-claude-tier-<tier> <value>` — `<tier>` is `think`, `do` or `verify`. A value matching `opus`, `sonnet`, `haiku` or `fable` case-insensitively is normalized to lowercase; any other non-empty value is stored verbatim as a pinned model ID.

`.devforge/lib/configure_helper set-claude-effort-<tier> <value>` — the value must be one of `default`, `low`, `medium`, `high`, `xhigh`, `max`. The setter exits 2 on anything else and writes nothing: surface its stderr and ask that tier's effort question again rather than substituting a value of your own.

Save a tier's two answers before issuing the next tier's call, so an interrupted run keeps every answer already collected.

## Defaults rationale

Recommended defaults: `think = opus`, `do = sonnet`, `verify = sonnet`, and effort `default` on all three tiers. These are the same values the framework emits into the agent files before this command runs, so a user who takes every recommendation changes no agent file.

- **`think = opus`** — it stays the recommendation until a measured comparison inside this pipeline moves it. The vendor's documented reasoning gains for `fable` are real, they have not been measured against this framework's own commands, and `fable` is the most expensive of the four per token — so recommending it would spend a project's budget on an untested expectation. Recommending `opus` is not evidence that `opus` is the better choice here; it is the absence of evidence that `fable` is.
- **`do = sonnet`** — this tier carries the per-task execution work, so its cost per turn is the one paid most often, and `sonnet` balances that against the capability the work needs.
- **`verify = sonnet`** — the verify-tier agents weigh evidence rather than run mechanical checks, and they are tools-locked read-only reviewers precisely because their output is a judgment and not an edit; judgment is not the tier to economize on. `sonnet` is also the value the framework emits for this tier, so the recommendation and what installs actually receive now agree. This file recommended `haiku` here before it was rewritten, and that recommendation never reached an agent file — nothing read these answers until `apply-agent-models` existed.
- **effort `default`** — it inherits the session's own effort level, so the framework never overrides a level the user set deliberately, and it tracks whatever levels the chosen model supports instead of pinning one the model may not have.

Three bounds this command does not close, and none of them is a defect to report:

- **Nothing validates a model against an effort level.** Claude Code falls back to the highest supported level at or below the one set, and it does so silently (documented at `code.claude.com/docs/en/model-config.md`), so an unsupported combination looks exactly like success. No phase of `/devforge:configure` detects it.
- **A green probe is not an entitlement guarantee.** It says this session could dispatch a subagent on that alias — nothing about the account's plan, its data-retention setting, or whether the alias still works tomorrow.
- **A pinned model ID is the user's to maintain.** Nothing in this framework reports one as stale, now or later.
