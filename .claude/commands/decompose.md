---
description: A large intent into a tree of tracker tickets, each leaf ready for /research. Run by the user.
argument-hint: "[\"intent\" | issue key]"
disable-model-invocation: true
---

# /decompose — An Intent into a Tree of Tickets

Turns a request too large for one feature into a tree of tickets. A **leaf** is one vertical slice, the size of one feature, that `/research` starts: a ticket or a subtask. A **container** (an epic, or a ticket with subtasks) only groups leaves and holds no work of its own. It writes `decompositions/YYYY-MM-DD-<slug>.md`.

Not part of the workflow chain and not run by `/conduct`: no autonomous points, no delivery ledger, no roadmap rows. A request that is one feature goes straight to `/research`.

## Usage
```
/decompose "the client wants sign-in with Google"
/decompose PROJ-123      ← build under an existing epic or ticket (Jira)
/decompose #42           ← the intent from a GitHub issue
```

## Arguments
`$ARGUMENTS`, read in this order (`ISSUE_TRACKER`, `ISSUE_KEY_PATTERN`, `JIRA_MCP_SERVER` and `JIRA_SITE` in `.claude/project-config.json`, as `.claude/commands/review-pr.md` → "Configuration" defines them, defaults included):
1. Empty: ask for the intent (`AskUserQuestion`).
2. The whole argument matches `ISSUE_KEY_PATTERN` and `ISSUE_TRACKER` is `jira`: that issue is the parent (PHASE 1, an existing parent).
3. The whole argument matches `ISSUE_KEY_PATTERN` and `ISSUE_TRACKER` is `github`: run `gh issue view <n> --json title,body` (`<n>` = the argument without its `#`) (in wrapper mode inside the Source Root); its title and body are the intent. No parent: the shape follows PHASE 3, "Shape". The issue cannot be read: stop and say why.
4. Anything else is an intent. Keys inside an intent are never read: to build under a parent, pass the key alone. With `ISSUE_TRACKER` `none`, a key-shaped argument is an intent.

Keep the intent word for word (or the user's reply when you asked) for the file.

## PHASE 1: Load Context

1. Read `.claude/project-config.json` for the keys above and `CLAUDE.md` for the Source Root and the project structure.
2. Resolve the argument (Arguments).
3. **An existing parent** (`jira`, the argument is a key). Read it with the tool of the `mcp__<JIRA_MCP_SERVER>__` server that reads one issue by key (on the Atlassian server: `getJiraIssue`); when that tool needs a cloudId, take it from `JIRA_SITE`, else from the server's list of accessible sites (one site: use it).
   - Take its summary, description and issue type; its summary and description are the intent.
   - Its level comes from its issue type's hierarchy level, never from the type's name: `hierarchyLevel` 1 is an epic, 0 a ticket, -1 (or `subtask: true`) a subtask. The parent is a subtask: stop; the tracker cannot nest below a subtask. Any other level: stop and say that this command builds only under an epic or a ticket.
   - Its existing children (key, summary, type): an epic's children with the tool that searches issues (on the Atlassian server: `searchJiraIssuesUsingJql`, JQL `parent = <KEY>`); a ticket's subtasks from the single-issue read.
   - The parent cannot be read (tools not available, several Jira sites and no `JIRA_SITE`): stop and say why; a key alone leaves no intent to fall back on.
   - An epic and no search tool: stop before slicing and name the missing tool; the check against duplicates depends on the children.
4. **A vague intent**: when no outcome a user could observe can be named from the intent ("the client wants something for reports"), ask once, with one `AskUserQuestion` call of at most 4 questions, and slice from the answer. No scoping interview: the review (PHASE 5) catches a wrong reading.

## PHASE 2: A Shallow Look at the Project

Find only what the slicing needs:
- what already exists in the areas the intent touches (the current sign-in, the user model, the sessions);
- where the natural seams are;
- what depends on what (data before the screen that shows it).

**When nothing exists** (Google sign-in in an app with no users, no sessions and no sign-in), the absence is a finding, stated in the file. The look goes one step out, to what the capability will stand on: how the app stores data, whether there is a server side, routing, where configuration and secrets live.

**Scope**: when `CLAUDE.md` specifies a Source Root other than `.`, search only inside it. When `.claude/quality-profile.json` sets `searchScopes`, search only inside them, never the repository root (`python3 scripts/forge/quality_profile.py scopes` prints them minus `generatedDirs`). Read at most 10 files in all.

No feasibility verdict, no comparison of approaches, no web research: each leaf's own `/research` does that.

**An unfamiliar technology**: when slicing needs facts this look cannot give (a technology neither the project nor you know well enough to name the steps of its path), say so and stop. Recommend `/research "<the intent>"` on the whole intent first, then `/decompose` with an intent that names the chosen approach.

## PHASE 3: Slice

**Rules**:
- **End to end.** Each leaf changes behaviour that a user, or a consumer of what this workspace delivers (a screen, an API endpoint, a CLI), can observe, through the whole path. A leaf whose only outcome is internal (a database set up, a library added, a model with no caller) is not a leaf. Leaves are never cut by layer ("the backend leaf", "the screen leaf").
- **Within this workspace.** Outside work is named in a leaf's `Depends on:`, never made a leaf:
  - work in a repository this workspace does not hold (a separate front end, another service);
  - non-code work that someone with access must do: accounts, provider console setup (an OAuth client, a consent screen, redirect URIs), credentials and secrets in each environment, access granted by another team.
- **Thinnest path first.** The first leaf is the thinnest path that works end to end; later leaves widen it or build on it. In an app that already has users: sign-in with Google for an existing user, matched by verified email. When nothing exists (PHASE 2), the first leaf carries the minimal foundation its path needs and no more (the user record, the session, one protected page); there is no foundation-only leaf.
- **Under the size thresholds.** Estimate each leaf against `.claude/storage-rules.md` → "Feature Size": at most 20 acceptance criteria, fewer than 3 parts delivered separately. A leaf that would cross them, its foundation included, is cut thinner along the path, each piece still end to end (sign-in with a session and no stored user first; a returning user keeps their profile second).
- **Order.** Each leaf names the leaves it depends on, with no cycles.
- **What is left out.** Each leaf says what it leaves to which other leaf.
- **Existing children** (PHASE 1) are in the tree as already present. A new leaf fills only what they do not cover; a leaf an existing child already covers is not proposed.

**Shape**:
- Without a parent, by the number of leaves:
  - one leaf: not a decomposition. Say so and give `/research "<the intent, verbatim>"` (from a GitHub issue: `/research #<n>`). Nothing is saved; stop.
  - two or three: tickets without an epic;
  - four or more: an epic with tickets. A ticket gets subtasks when several leaves together make one capability a user sees.
- Under an existing parent, its level (PHASE 1) decides: under an epic, the leaves are tickets, and a ticket may get subtasks by the rule above; under a ticket, every leaf is a subtask, whatever their number. One leaf is still one child: say that the intent was a single feature.
- A container this command would create with one leaf collapses into that leaf. An existing parent never collapses.

The user can regroup at the review.

## PHASE 4: Write the Issues

Each new issue uses exactly one of two templates. Every section is present, in this order, its label at the start of a line; a section's text follows on the same line, or as `- ` items below it. An empty section holds `—`. Nothing is written outside the sections. The heading line carries the summary (the issue title).

**A leaf**:
```
### <n>. <Ticket | Subtask>: <the outcome: one sentence of what a person can observe>

Context: <one line on the whole intent>; part of <the parent's title, when there is one>
Outcome: <1–3 checkable statements of what works after this issue>
Out of scope: <what this leaf leaves to which other leaf>
Depends on: <other leaves; outside work>
Open questions: <what the requester or the client must decide ("only the company's email domain?"); not questions for the developer>
```
`Outcome:` statements are not acceptance criteria: those are `/specify`'s. Without a parent, `Context:` ends after the intent.

**A container**:
```
### <n>. <Epic | Ticket>: <the capability as a whole>

Intent: <the intent, in English>
Outcome: <what works when all its parts are done>
Split into: <the titles of its children, in dependency order>
Depends on: <the outside work of its leaves, listed for the reader>
```

Rules for the text:
- **Other issues by title.** A leaf names another leaf by its title, never by its number in the file: the number means nothing in the tracker or to `/research`. An existing parent or child is named by key and title (`PROJ-123 <title>`).
- **Each leaf stands on its own.** `/research` reads only the leaf's summary and description, never the parent.
- **No design** and no implementation steps ("add a method to the service"): those are `/breakdown`'s tasks.
- **No Forge traces**: no command names, no `decompositions/` paths, no `file:line` into the workspace. People outside this workspace read the tracker; in wrapper mode, the client does.
- **English**, whatever the intent's language. Only the quoted source text in the file (the intent, the parent's or the issue's text, the answers) stays word for word in its own language.
- **Every tracker, the same template**: with `github` or `none` the texts in the file read the same.
- **A leaf's request**, for `/research "<its request>"`: its summary (the heading without `### <n>. <level>: `), then its sections, as the file holds them.

## PHASE 5: Review

Show in the console:
1. The tree, one line per issue, indented under its container: `<n>. <level>: <title> · depends on: <numbers | none>`; an existing parent or child as `<n>. <level>: <KEY> <title> · existing`.
2. Below it, the full text of every new issue in its template, exactly as it will be written.

Then ask (`AskUserQuestion`): **accept**, **change** (the user says what) or **cancel**. A change redraws both and asks again. Cancel: nothing is saved; stop.

## PHASE 6: Save the File

Write `decompositions/YYYY-MM-DD-<slug>.md` (`<slug>`: lowercase kebab-case, 2–4 English words; when that file exists, add `-2`, `-3`). The directory sits at the workspace root, the directory that holds `CLAUDE.md`; in wrapper mode the wrapper root, never inside the Source Root. Write it by `.claude/commands/_writing.md` → "Rules" and "Reports". Do not commit it.

```markdown
# Decomposition: <the capability, in English>

**Date**: <YYYY-MM-DD>
**Tracker**: <`ISSUE_TRACKER` at this run: jira | github | none>
**Intent (verbatim)**:
> <the intent, word for word; every line prefixed `> `, a blank line as `>`>

<With a parent instead: **Parent**: <KEY> — <summary> (<issue type>), its description quoted the same way, then **Existing children**: <KEY> <summary> (<type>), one per line, or none. From a GitHub issue: **Issue**: #<n> — <title>, its body quoted the same way.>
<After the vague-intent question: **Answers**: each question and the user's answer, word for word.>

## Current State

<A few lines on what exists in the touched areas, with `file:line`; the absence finding when nothing exists.>

## Tree

<The tree of PHASE 5, as approved.>

## Issues

<Each new issue's text, in tree order, as approved.>
```

## PHASE 7: Next Steps

Confirm `Saved to decompositions/<file>.md`, then list the leaves in dependency order, each as `/research "<its request>"`.
- Mark the leaves that depend on no other leaf: two or more of them can start in parallel.
- **When everything waits on one leaf** (every other leaf depends on it, directly or through other leaves; the usual case when nothing existed), say so plainly: start with that leaf; the rest after it.
- Never imply that leaves can start in parallel when they cannot.

## IMPORTANT RULES

1. **Read-only for the code**: the only write is the file, left uncommitted. An existing parent and its children are only read.
