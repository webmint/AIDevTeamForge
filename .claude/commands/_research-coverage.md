---
disable-model-invocation: true
user-invocable: false
---
# Research Coverage: Read What Must Be Read

Referenced by `/research` Phases 2 and 4. An instruction such as "search thoroughly" does not make research complete. This procedure does: it works out up front what must be read, requires each item to be read with a verified quote or excluded with a reason, and checks the coverage by script. It is the same for every language and stack. You read the code and name what it calls; the scripts only extract bodies and check the ledger, the coverage, the quotes and the identifiers.

## Files

Choose the report path before Step A: `research/YYYY-MM-DD-<topic-slug>.md` (`/research` Phase 5's naming rules, `-2`, `-3` … when the path exists). `<report>` below is that path without `.md`.
- `<report>-ledger.md`: the call ledger, written while you read (Step C).
- `<report>.md`: the report, written in Phase 4.
- `<report>-closure.txt` and `<report>-research-lint.txt`: written by the checks. They and the ledger are the report's traces.

## Turns and context

Cost grows with turns times context, not with the code read. So:
- **Read code in batches.** `python3 scripts/forge/research_query.py bodies <item> <item> …` prints 10–20 bodies in one call, each under its ledger heading `### `<symbol>` `<path:N-M>`` with line numbers. Give items as `path:N` (a line inside a body names the function that holds it); a bare symbol prints every namesake. `research_query.py pending <report>.md` prints the next batch of depth-0–1 items still to read. After the last seeds are read (end of Step D), `pending --leaves --max-lines 120` prints all depth-2 items once (they need only their deciding lines). Do not read one function per call, and do not read a whole file to find one body. Use Read only for a file that holds no definitions (configuration, docs), for the lines a `cut at` note names, or after an `end: uncertain` body: read on from its last line shown and correct `M` in the heading.
- **Run the checks as one command**, `python3 scripts/forge/research_check.py <report>.md` (closure check and lint on one definition index), at most three times: once when the ledger is complete (end of Step D), once when the report is written (Step E), and once after that run's fixes. Not after each edit. When blocking lines remain after the third run, do not run it again: record the counts and the open lines in the `**Checks**:` line.
- **Explore digests are pointers.** A fact counts once you have read the code and quoted it. This holds in autonomous mode too: `_autonomous-mode.md`'s "read the Explore digest instead of the whole file" does not apply to a closure item.

## Step A: Two independent searches

Launch two read-only searches in parallel, in one message, as `subagent_type: Explore`, inside the search scopes:
- **top-down**: from the entry points the request names or implies (routes, handlers, commands, jobs, UI actions), inward along the calls;
- **bottom-up**: from the data and the names (collections, tables, fields, keys, identifiers and literals of the request), outward to the code that reads and writes them.

Ask each for a hit list of `symbol path:N`. Record each hit as a pass-1 seed at the definition line of the function, method or type that holds it, not at the hit's own line, marked `top-down`, `bottom-up` or `both`.

## Step B: The facets

Find at least one site for each facet, or record what you searched:
1. entry point;
2. authorisation path;
3. data path (DAOs, path builders, queries);
4. data model (collections, fields, casing);
5. validators and normalisers;
6. error mapping;
7. runtime limits and configuration (timeout, memory, concurrency);
8. test infrastructure: helpers, fakes, harnesses and fixtures, with the operations each one supports and does not support;
9. duplicates: other copies of the same rule or logic in any package;
10. contracts and docs that already fix behaviour.

Each facet site in code is a pass-1 seed (`facet <n>`).

## Step C: The ledger, roles and the closure

Write `<report>-ledger.md` as you read:

```
## Seeds
- `<symbol>` `<path:N>` — pass <1|2> — <reason> [<role>]

## Read
### `<symbol>` `<path:N-M>` [<role>]
- `<callee>` → `<path:N>` [<role>]
- `<callee>` → external
- `<token>` → ignored — <reason>

## Excluded
- `<symbol>` `<path:N>` — <reason>
```

- **Reasons**: `top-down`, `bottom-up`, `both`, `request`, `facet <n>`, `approach`, and the four directions of Step D: `duplicate of <rule>`, `caller of <symbol> — behaviour changes | unchanged`, `sibling of <symbol>`, `test infra`.
- **Roles**, required on every seed and entry, optional on an edge: `[access]` for the authorisation or scope path; `[data]` for the read/write path (queries, keys, path builders, normalisers, serialisers); `[container]` for a class or module body; `[other]` for the rest. Tag every edge whose callee is on the access or data path: a depth-2 item gets its role only from its edges, and an untagged one is `other` and may fall over budget.
- `### ` names the whole body you read: `N` is its definition line, `M` its last line. Copy the heading `research_query.py bodies` prints, drop its `(end: …)` note, add the role tag, and replace a `?` symbol with the real name.
- One bullet per repository-defined symbol the body calls or references (functions, methods, types), with its definition line, or `external` for a library or framework symbol. `ignored — <reason>` is for a token in the body that only looks like a reference: a local variable named like a repository function, a string key, a namesake method of another type.
- **Containers**: do not read a whole class or module, and do not ask `bodies` for one. `research_query.py siblings <path:N>` lists its members with their ranges. Write its entry as `### `<X>` `<path:N>` [container]` with the members that matter as edges: the members are the items, at the container's own depth, and the container needs only a Coverage row (read or excluded with a reason). A container with no entry blocks (`container_no_entry`) until it has one or is excluded.
- **Depth**: follow the edges to depth 2 from the seeds. Every non-container item at depth 0 or 1 gets its own `### ` entry, read in full. Items at depth 2 need a Coverage row (Step E), not an entry. Depth-2 `access` and `data` items are always in. Depth-2 `other` items share a line budget (half the depth-0–1 entry lines, smallest first); the rest are `not covered: over budget`, and you leave them unread. Nothing is dropped silently.
- On the access path and the data read/write path, read every body whole, with its callees. No item there is skimmed or a passthrough. Read adapters, mappers, normalisers, builders and serialisers whole too, and tag them `[data]`: their names promise a shape change and hide value changes (trim, case, slashes, encoding, defaults, generated ids).
- A bottom-up name found while reading that no seed or edge reaches becomes a new seed.

- `## Excluded` lists an item you decide not to read, with the reason, as soon as you decide: the checks and `pending` treat it as excluded before the report exists. Coverage repeats it as an `excluded` row.

Work in rounds: write the seeds' entries from one `bodies` batch, then `research_query.py pending <report>.md` for the next round, until it shows no entry to write and no container without an entry. Run no check yet: the ledger is complete only after Step D.

The check's blocking lines, and their fixes:
- `not_read`: read the item and add its entry, or list it under `## Excluded` with the reason.
- `container_no_entry`: write the container's entry with its members as edges, or exclude it.
- `missed_ref`: the body uses a repository definition the entry does not name. Add the edge, or add `ignored — <reason>` when the token is not a reference.
- `ledger_*`: fix the line it names (`ledger_no_role`: add the tag).

With Universal Ctags installed, `missed_ref` blocks, except a member access (`obj.m()`, `pkg.F()`) to a definition in another file, which is `advisory`. With the regex fallback every `missed_ref` is `advisory`. Check each advisory line all the same.

## Step D: The other directions

A callee-only closure misses a third of what a spec needs. Seed these too, each with its reason, and read them as in Step C:
1. **Duplicates** (pass 1): other implementations of the same rule or logic in any package. Search by the rule's distinctive literals, field names and operators, not by the function's name. Facet 9 sites count.
2. **Siblings** (pass 1, after the first round): for each depth-0 `[data]` item, the other functions in its file or module that touch the same resource: `python3 scripts/forge/research_query.py siblings <path:N> --terms '<collection>,<table>,<key prefix>'` (one quoted, comma-separated argument) lists them, marked `[mentions: …]`. Seed the marked ones: `sibling of <symbol>`.
3. **Test infrastructure** (pass 1): the helpers, fakes and fixtures that the tests of the touched functions use. Facet 8 sites count. In Coverage, say which operations each one supports and which it does not.
4. **Callers** (pass 2): once Phase 4 has chosen the recommended approach, take every existing function the approach will change or whose behaviour it depends on. `python3 scripts/forge/research_query.py callers <symbol>` lists the uses grouped by enclosing definition. Drop namesakes: a hit must call this symbol. Seed each caller one level up, `caller of <symbol> — behaviour changes` or `— unchanged`. A caller whose behaviour is unchanged may go under `## Excluded` (`caller, behaviour unchanged: <why>`) instead of taking an entry.

Pass 2 also seeds every existing function the approach will call or change (`approach`), so the helpers that new code will use are covered even when no current code path reaches them. Read the pass-2 seeds with `bodies`/`pending` as in Step C.

Then run `python3 scripts/forge/research_check.py <report>.md`, before the report is written: the ledger is complete, and the lint is skipped. Fix its blocking lines in one pass. Then run `research_query.py pending <report>.md --leaves --max-lines 120` once for the depth-2 items' deciding lines, and `python3 scripts/forge/research_query.py items <report>.md` for the item list for Coverage as it stands after your fixes (neither writes anything or counts as a check run).

## Step E: The report sections and the checks

Add these sections to the report:

```
## Search routes
- top-down: <start points>; <hits>; found only by this route: <items | none>
- bottom-up: <start names>; <hits>; found only by this route: <items | none>
- duplicates: <seeds> | none — searched: <terms, paths>
- callers: <symbol>: <n> — <path:N> (changes | unchanged), … | none — searched: <terms, paths>
- siblings: <seeds> | none — searched: <terms, paths>
- test infrastructure: <seeds> | none — searched: <terms, paths>

## Facets
- **1. Entry point**: `<path:N>` `<verbatim line>` — <what it does here>
- **2. Authorisation path**: none — searched: <terms, paths>
…one bullet for each of the ten facets, in Step B's order and with its number

## Coverage
- `<symbol>` `<path:N>` — read — `<path:N-M>` `<verbatim line(s)>` [<found by>]
- `<symbol>` `<path:N>` — excluded — <reason>
- `<symbol>` `<path:N>` — not covered: over budget
```

- **Coverage**: one bullet per closure item `research_query.py items` lists. `<path:N>` is the item's line exactly as it prints it. Mark an item `not covered: over budget` only when it says so, and `excluded` for each item under the ledger's `## Excluded`, with the same reason. The found-by tag of a seed is its reason: `top-down`, `bottom-up`, `both`, `duplicate`, `caller`, `sibling`, `test infra`, or `pass 2` for `approach`. `request` and `facet <n>` count as `top-down`, except facets 8 and 9, which are `test infra` and `duplicate`. An item reached only by edges is `closure`. A `read` row quotes the line or lines that decide the item's behaviour for this request: normalisation, validation, limits, error mapping, defaults. An item found by only one search route says which one.
- **Over budget**: a `not covered: over budget` item is not quoted or cited anywhere in the report. When you need its code, read it, and give it a `read` row: the lint blocks a cited over-budget item.
- **Quotes**: a quote is a code span (or `"…"`) holding the lines exactly as they appear in the file, whitespace aside. `path:N` may run on past line N, `path:N-M` stays within those lines, and ` … ` joins fragments that appear in that order. When the line holds a backtick, wrap the quote in a longer run (` `` … `` `) or in `"…"`.
- **Claims**: anywhere in the report, a claim about what a function does, such as "does not change the value", "strict", "no trim" or "fully testable on X", carries the quoted line that decides it. Without one, it is not stated.

Run `python3 scripts/forge/research_check.py <report>.md`. Fix every blocking line in one pass (a missing row, a quote that does not verify: copy the line from the `bodies` output; a missing seed-kind bullet). For each `advisory claim_without_quote`, add the quote or drop the claim. Run it once more, the last time. When a script exits 2 (usage or I/O error), fix what its message names (a path, an argument, the ledger file) and run it again; this run does not count. Only when it still exits 2, put its message in the `**Checks**:` line and go on. Record the result in the report's `**Checks**:` line.

Last, run `python3 scripts/forge/research_query.py trace <report>.md` and copy its `trace:` result, without the `transcript:` line, into the report's `**Runner trace**:` line.
