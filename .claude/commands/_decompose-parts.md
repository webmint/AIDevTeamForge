---
disable-model-invocation: true
user-invocable: false
---
# Decompose Parts: One Intent Across Several Repositories

Read by `/decompose` (PHASE 1, when `RELATED_WORKSPACES` lists two or more parts; on a resume, when the file has a `**Parts**` header). Where this file and `decompose.md` differ, this file wins.

## What This File Overrides

Each `decompose.md` line below is replaced by the rule named after it, in a run these rules apply to:
- PHASE 2 "Scope": "Read at most 10 files in all", and the working tree, for the other parts → "The Look Across Parts".
- PHASE 3 "Within this workspace" → "Slicing Across Parts".
- PHASE 3 "End to end": "A leaf whose only outcome is internal … is not a leaf" and "Leaves are never cut by layer", for the agreement leaf and across parts → "Slicing Across Parts", "The Agreement Leaf".
- PHASE 3 "Thinnest path first": its first sentence and "there is no foundation-only leaf", for the agreement leaf → "Slicing Across Parts".
- PHASE 3 "Shape": the counts and subtasks → "Shape and Texts".
- PHASE 4, the leaf template: "1–3 checkable statements", for the agreement and the check → "The Agreement Leaf", "The Check of the Whole Flow"; "Without a parent, `Context:` ends after the intent" → "Shape and Texts".
- PHASE 5 item 2: "indented under its container" → "Shape and Texts".
- PHASE 6 "Current State": its `file:line` → "Shape and Texts".
- PHASE 8: "`/research <KEY>` for a leaf with a key", and its order → "Jira, Next Steps, Resume".

## The Parts

`RELATED_WORKSPACES` in `.claude/project-config.json` is one JSON string, like every value there: parts separated by `;`, each `<role>=<path>`.
- Example: `"backend API=.; web front end=../web-ws; mobile app="`.
- `<role>`: what this part delivers, in English, without `=` or `;`.
- `<path>`: the part's workspace directory (the directory that holds its `CLAUDE.md`), absolute or relative to this workspace's root. This workspace is `.`.
- A repository with two roles (an app and its server functions) is two parts with the same path.
- A repository that does not exist yet, or whose workspace is not installed: an empty path.
- Several workspaces can wrap the same repository; the list names one.

**Reading the list**: split on `;`, trim spaces around each entry and around its `=`, ignore empty entries (a trailing `;`). No key, `""`, `"N/A"` or one part: these rules do not apply.

**This workspace is in the list.** Every entry whose path resolves to this workspace (`.`, or its absolute path) is one of this workspace's parts. The first such entry's role names this workspace (the check, the file).

**A wrong entry**: an entry with no `=`; an empty role; a role used twice (the role prefix must tell the parts apart); a part whose non-empty path does not exist, or holds no `CLAUDE.md`; no entry that resolves to this workspace. Stop before the look and name the entry (not under an existing ticket: below). Never guess another workspace's location.

## When a Run Is Multi-Repository

**Under an existing ticket** (its leaves would be subtasks): the list is ignored, its entries are not checked, and the run is single-repository; say so. A subtask across repositories has no workspace to start in.

Otherwise the look decides which parts the intent touches; a part with no path is judged from its role.
- **Only one part, and it is this workspace's**: a single-repository run, as without the list; the file says so in one line and has no `**Parts**` header. Two parts of this workspace (two roles at `.`) are two parts: the rules below apply.
- **Only one part, of another workspace**: stop. Name the workspace to run `/decompose` in (`cd <path>`), or, for a part with no path, say that its workspace must be installed first. Nothing is saved.
- **Two or more parts** (two roles of one repository count as two): the rules below apply. This workspace need not be one of them; it still holds the file and runs the check.

**Under an existing epic**: its children stay in the tree and are not created again (PHASE 3, "Existing children"). An existing child's part is the part whose role starts its summary (`<role>: …`). A child with no such prefix is shown at the review as "part unknown", where the user can assign it; Next Steps lists it under "existing, part unknown", with no command. An existing child whose summary, the roles aside, is the agreement's or the check's fixed summary is that leaf, and no second one is proposed; one in other wording the user catches at the review.

## The Look Across Parts

- **One look per path**, at most 10 files per path, whatever the number of roles at it.
- **This workspace's path** is searched as PHASE 2, "Scope" says: the working tree.
- **Each other part with a path**: read its `CLAUDE.md` (Source Root) and its `.claude/project-config.json` (`DEFAULT_BRANCH`, `ISSUE_TRACKER`, `ISSUE_KEY_PATTERN`). Search inside its Source Root; when it has a `.claude/quality-profile.json`, only under its own `searchScopes` minus `generatedDirs` (`python3 scripts/forge/quality_profile.py scopes`, run in that workspace). The scopes are workspace-relative: strip the `<SOURCE_ROOT>/` prefix before passing them to `git grep`, from a scope and from the directory after an `:(exclude)` line alike (the Source Root itself, with or without its trailing `/`, becomes `.`). A scope or an exclude whose directory lies outside the Source Root (a wrapper's `docs/`) is not in the source repository: drop it.
- **Read a branch, not the working tree**: another session may have a feature branch checked out with uncommitted work. The ref, the first that exists: the part's binding `integrationRef`; `origin/<DEFAULT_BRANCH>`; `<DEFAULT_BRANCH>`; with no `DEFAULT_BRANCH`, the branch `origin/HEAD` points to; none of these: the working tree. Search with `git grep <pattern> <ref> -- <paths>` and read with `git show <ref>:./<path>`, both run inside the part's Source Root.
- **No fetch.** The ref is as fresh as that workspace's last fetch; the commit the file records shows how fresh.
- **A part with no path**: no look; the absence is its finding (PHASE 2, "When nothing exists").
- **Read-only**: no checkout, fetch, stash or other write in any part.

## Slicing Across Parts

- **A leaf is one part's piece of one capability.** It is end to end for what its part delivers, to its consumer: a back end's leaf to the front end that calls its endpoint, a front end's leaf to the user.
- **Inside one part, leaves are never cut by layer**: a part's leaf is never "the database leaf" of that part.
- **A capability** is what a user sees when all its leaves are done.
- **Thinnest path first** applies to capabilities: the first capability goes through every part it needs, each thinly, before any capability widens. The agreement leaf comes before it.
- **Across parts**, the leaf that provides blocks the leaf that consumes (the back end's sign-in blocks the front end's sign-in screens).
- **Outside work** is still named in `Depends on:`, never made a leaf: a repository that is not in the list, provider console setup, secrets, access from another team. Deploy order across parts, which a link cannot hold (a merge is not a deploy), stays text in `Depends on:`.
- **The size thresholds** apply to each leaf.

## The Agreement Leaf

- **One per epic**, when two or more parts pass something to each other (calls, events, shared data). None when they do not.
- **Its fixed summary**: `<role>: the interface between <the roles it covers, separated by commas, the last after "and"> is agreed` (`backend API: the interface between backend API, web front end and mobile app is agreed`).
- **Its `Outcome:`** has no 1–3 limit: one `- ` item per boundary. In words, what must be agreed: each boundary between two parts (which part gives what to which), and for each, the calls or events, the data, the configuration and secrets each side needs, and who owns each. No shapes and no fields: those are the agreement's own work. "No design" (PHASE 4) stays.
- **Its `Out of scope:`** says that building any of it belongs to the parts' own leaves.
- **It blocks every leaf that uses an interface it covers**, not only each part's first leaf: a leaf that does not name it in `Depends on:` never sees it. It comes first in every `Depends on:` that names it, so it is never past the five issues `/research` reads.
- **Where it starts**: in the workspace of the part that provides most of the interfaces (usually the back end); its role prefix names that part. The user can move it at the review.
- **Where it stops**: `/research` on it, in the providing workspace, writes a report whose `## Approaches` section and `**Recommended approach**` line hold the proposed interface for each boundary its `Outcome:` lists, from the provider's side; its `## Recommendation` is ignored for this leaf. The owners of the consuming parts read the draft and add or change their side (one person when one developer owns them all). The text they all accept is the agreed text. It goes into the agreement issue's description by hand: `/decompose` never edits an issue, and `/research` does not write to the tracker. It goes to no `/specify`: there is nothing to build.
- **Without a tracker read** (tracker `github` or `none`, or a consuming part whose tracker settings do not match): the developer passes the agreed text to that part's `/research "<its request>"` by hand, so it lands in the report's request, not in its `**Depends on**` field.

## The Check of the Whole Flow

- When the tree has leaves in two or more parts: a last leaf with the fixed summary `<role>: the whole flow works on the shared environment`, `<role>` being this workspace's role. It depends on every other leaf.
- **Its `Outcome:`** has no 1–3 limit: one `- ` item per capability, its user-visible outcome, checkable on the shared environment.

## Shape and Texts

- **Shape**: without a parent, always an epic, whatever the number of leaves: the check needs a container shared by all parts, and no part's ticket can hold the others. Leaves are tickets directly under the epic; this run makes no subtasks. A part's ticket can later get subtasks from `/decompose <KEY>` run in that part's workspace.
- **The summary** of every new leaf starts with its part's role: `<role>: <outcome>` (`backend API: a signed-in user's identity is returned to the front end`).
- **`Context:`** of a part's leaf: `<one line on the whole intent>; part of <the epic's title>; capability: <its user-visible outcome>`. The agreement and the check end after `part of <the epic's title>`. The epic's title appears with or without a parent.
- **The templates are otherwise unchanged.**
- **The review** (PHASE 5) shows the tree under the epic, grouped by capability, each line as PHASE 5 writes it (the title already starts with the role); the agreement first, the check last, existing children with their part or "part unknown". Grouping is in the file and the console only; the tracker has no container per capability.
- **Current State** cites `<role>: <path>:<line>`, since paths in different parts can be the same.
- **The file**: the header gains `**Parts**:`, then one line per part, in the list's order: `<role> — <path | none> — <ref and commit read | working tree | no look>`. The tree is as reviewed.

## Jira, Next Steps, Resume

- **One Jira project for the whole tree**: the parent epic's, or the one the user names (PHASE 7, "Choose").
- **Each part's tracker settings decide its commands.** For a part whose `ISSUE_TRACKER` is not `jira`, or whose `ISSUE_KEY_PATTERN` does not match the created keys, its leaves get `/research "<its request>"` instead of `/research <KEY>`, with the reason: `/research <KEY>` reads nothing there. A part with no path: its leaves wait for its workspace.
- **Next Steps** lists the leaves by part, in dependency order, each with the workspace to run it in (`cd <path>`).
  - The agreement first, with its stop point: its `/research` report's interface draft is where that leaf ends, whatever the report recommends next. A consumer whose command is `/research <KEY>` waits until the agreed text is in the agreement's issue; a consumer whose command is `/research "<its request>"` waits until the developer has the agreed text to pass in by hand.
  - The check last: run it in this workspace once all other leaves are done, by `/research` when the project has end-to-end tests that can cover the flow, by hand otherwise.
- **Tracker `github` or `none`**: the file is the output; Next Steps is the same, with `/research "<its request>"` for every leaf.
- **Resume from a file** with a `**Parts**` header, whatever the current list says: the parts come from the header, the list's entries are not checked, and the look is not repeated. Read each part's `.claude/project-config.json` again for its tracker settings, for Next Steps.
