---
disable-model-invocation: true
user-invocable: false
---
# Research Coverage: Read What Must Be Read

Referenced by `/research` Phases 2 and 4. An instruction such as "search thoroughly" does not make research complete. This procedure does: it works out up front what must be read, requires each item to be read with a verified quote or excluded with a reason, and checks the coverage by script. It is the same for every language and stack. You read the code and name what it calls; the scripts only check the ledger, the coverage, the quotes and the identifiers.

## Files

Choose the report path before Step A: `research/YYYY-MM-DD-<topic-slug>.md` (`/research` Phase 5's naming rules, `-2`, `-3` … when the path exists). `<report>` below is that path without `.md`.
- `<report>-ledger.md`: the call ledger, written while you read (Step C).
- `<report>.md`: the report, written in Phase 4.
- `<report>-closure.txt` and `<report>-research-lint.txt`: written by the scripts. They and the ledger are the report's traces.

## Step A: Two independent searches

Launch two read-only searches in parallel, in one message, as `subagent_type: Explore`, inside the search scopes:
- **top-down**: from the entry points the request names or implies (routes, handlers, commands, jobs, UI actions), inward along the calls;
- **bottom-up**: from the data and the names (collections, tables, fields, keys, identifiers and literals of the request), outward to the code that reads and writes them.

Ask each for a hit list of `symbol path:N`. Record each hit as a pass-1 seed at the definition line of the function, method or type that holds it, not at the hit's own line, marked `top-down`, `bottom-up` or `both`. An Explore digest is only a pointer: a fact counts once you have read the code and quoted it. This holds in autonomous mode too: `_autonomous-mode.md`'s "read the Explore digest instead of the whole file" does not apply to a closure item.

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

## Step C: The ledger and the closure

Write `<report>-ledger.md` as you read:

```
## Seeds
- `<symbol>` `<path:N>` — pass <1|2> — <top-down | bottom-up | both | request | facet <n> | approach | caller of <symbol>>

## Read
### `<symbol>` `<path:N-M>`
- `<callee>` → `<path:N>`
- `<callee>` → external
- `<token>` → ignored — <reason>
```

- `### ` names the whole body you read: `N` is its definition line, `M` its last line.
- One bullet per repository-defined symbol the body calls or references (functions, methods, types), with its definition line, or `external` for a library or framework symbol.
- `ignored — <reason>` is for a token in the body that only looks like a reference: a local variable named like a repository function, a string key, a namesake method of another type.
- Follow the edges to depth 2 from the seeds: every item at depth 0 or 1 gets its own `### ` entry. Items at depth 2 need a Coverage row (Step E), not an entry.
- On the access path and on the data read/write path, read every body whole, with its callees. No item there is skimmed or a passthrough. Read adapters, mappers, normalisers, builders and serialisers whole too: their names promise a shape change and hide value changes (trim, case, slashes, encoding, defaults, generated ids).
- A bottom-up name found while reading that no seed or edge reaches becomes a new seed.

Then run `python3 scripts/forge/closure_check.py <report>.md`. It also runs before the report exists. Handle each blocking line, then run it again until none is left:
- `not_read`: read the item and add its entry, or exclude it in Coverage with the reason.
- `missed_ref`: the body uses a repository definition the entry does not name. Add the edge, or add `ignored — <reason>` when the token is not a reference.
- `ledger_*`: fix the line it names.

An item you exclude stays `not_read` until the report's Coverage holds its `excluded` row (Phase 4). In Phase 2, clear the other blocking lines; Step E's last run must show none.

With Universal Ctags installed, `missed_ref` blocks, except a member access (`obj.m()`, `pkg.F()`) to a definition in another file, which is `advisory`. With the regex fallback every `missed_ref` is `advisory`. Check each advisory line all the same. The closure has depth 2 and a cap of 60 items, ordered by distance from the seeds (`--depth`, `--cap`; pass the same values to both scripts). Items past the cap get the Coverage row `not covered: over cap`. Nothing is dropped silently.

## Step D: Pass 2, after the recommendation

Once Phase 4 has chosen the recommended approach, add `pass 2` seeds and read them as in Step C:
- every existing function the approach will call (`approach`), so the helpers that new code will use are covered even when no current code path reaches them;
- every existing function the approach will change (`approach`). List its inbound callers under `## Search routes` as `- callers of <symbol>: <n> — <path:N>, …` (search the scopes for the name; drop namesakes, a hit must call this symbol). Seed (`caller of <symbol>`) only the callers whose behaviour the change alters for this request.

Run `closure_check.py` again.

## Step E: The report sections and the lint

Add these sections to the report:

```
## Search routes
- top-down: <start points>; <hits>; found only by this route: <items | none>
- bottom-up: <start names>; <hits>; found only by this route: <items | none>

## Facets
- **1. Entry point**: `<path:N>` `<verbatim line>` — <what it does here>
- **2. Authorisation path**: none — searched: <terms, paths>
…one bullet for each of the ten facets, in Step B's order and with its number

## Coverage
- `<symbol>` `<path:N>` — read — `<path:N-M>` `<verbatim line(s)>` [<top-down | bottom-up | both | closure | pass 2>]
- `<symbol>` `<path:N>` — excluded — <reason>
- `<symbol>` `<path:N>` — not covered: over cap
```

- **Coverage**: one bullet per closure item in `<report>-closure.txt`. `<path:N>` is the item's line exactly as `<report>-closure.txt` prints it. The found-by tag of a seed is its ledger reason (`request` and `facet <n>` count as `top-down`); an item reached only by edges is `closure`. A `read` row quotes the line or lines that decide the item's behaviour for this request: normalisation, validation, limits, error mapping, defaults. An item found by only one search route says which one.
- **Quotes**: a quote is a code span (or `"…"`) holding the lines exactly as they appear in the file, whitespace aside. `path:N` may run on past line N, `path:N-M` stays within those lines, and ` … ` joins fragments that appear in that order. When the line holds a backtick, wrap the quote in a longer run (` `` … `` `) or in `"…"`.
- **Claims**: anywhere in the report, a claim about what a function does, such as "does not change the value", "strict", "no trim" or "fully testable on X", carries the quoted line that decides it. Without one, it is not stated.

Run `python3 scripts/forge/research_lint.py <report>.md`, fix every blocking line (a missing row, a quote that does not verify: re-open the file and copy the line), and re-run both scripts until neither prints a blocking line. For each `advisory claim_without_quote`, add the quote or drop the claim. When a script exits 2 (usage or I/O error), fix what its message names (a path, an argument, the ledger file) and run it again. Only when it still exits 2, put its message in the `**Checks**:` line and go on. Record the result in the report's `**Checks**:` line.
