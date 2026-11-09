# Checklist: spec-gate

**Gate**: on — set to `off` to skip this gate (the file is project-owned; deleting it does not work, `update.sh` restores missing checklists).
**Runs**: in `/specify`, after the spec is written and before its HARD GATE · **Reviewer**: `general-purpose`; a fresh context; a different model from the author where possible.
**Inputs**: `specs/NNN-*/spec.md`; `CLAUDE.md`; `constitution.md` if present; `docs/architecture.md` and the `docs/features/*.md` the spec touches; the `/research` report the spec cites, if any; the source files the spec's Affected Areas name.

**How to use**:
- Check every item against the artifact and its sources; report each failed item by id with evidence quoted from both sides.
- Severity follows the review scale (Critical / Warning / Suggestion / Info). Critical when the spec breaks a project rule (`CLAUDE.md`, `constitution.md`), leaves an AC untestable, leaves an open question unclosed that an AC depends on, or can be read two ways on an AC. Otherwise Warning, Suggestion or Info.
- Defects outside the list are reported too, as `new`.

**Origin**: `seed` = shipped with Forge; `field` = generalized from defects that escaped earlier gates in field use; `escape NNN/E<n>` = added by this project's /finalize learning step; `audit <date>/<theme>` = added by /audit. New items take the next free id; ids are never reused. An escape that an existing item already covers adds its origin to that item instead of a new item.

## Items

- **SG-01** Every AC states an observable outcome with exact expected values (texts, codes, counts, states) and names how it is checked (unit, integration, end-to-end, command or manual). — seed
- **SG-02** No AC or rule can be read two ways: no "should", "may", "appropriate" or "etc.", no undefined term, and no quantity without a unit or bound. Where two readings exist, the spec picks one. — seed
- **SG-03** Every flow specifies its negative paths with the user-visible result: invalid input, permission denied, not found, conflict or stale version, offline or server error, and the empty state. — seed
- **SG-04** Nothing contradicts a rule in `CLAUDE.md` or `constitution.md`. A spec decision that relaxes a project rule is a conflict to raise with the user, not a decision. — seed
- **SG-05** Every question the spec raises is closed, with its answer or working default recorded in the spec; an Open Question that an AC depends on is not left open, and no TBD remains in a requirement or AC. — seed
- **SG-06** When a design source covers the spec's screens, every field, state and user-visible text of those screens appears in the spec verbatim, and the spec names the design version it was taken from. — seed
- **SG-07** Every deliverable the feature request names is in scope or deferred explicitly with where it goes; Out of Scope lists what is excluded. — seed
- **SG-08** When the spec names test anchors (test ids, accessible names), each sits on the element the AC observes (the box that is measured, the container whose contents are asserted), the spec says which element carries it, and each value names exactly one element. — field
- **SG-09** An AC's check proves the stated outcome itself. A proxy (a marker count, a file's existence, a search for one string) that can pass while the outcome is false is a defect. — field
- **SG-10** When the spec changes, removes or renames a fact, symbol or string (a command, a path, a status, a default), its edit list comes from running the search over the stated scope at spec time (docs, instruction and agent files included) and matches that output; a file it keeps unchanged is deferred explicitly, with where the superseded fact is recorded. A hand-written list of places is a Warning. — field
- **SG-11** A guard or check that enforces an invariant covers every kind of object that can violate it, not only the obvious one. — field
- **SG-12** A decision that calls a credential, password or key "non-secret" or "local only" is checked against the project's secrets rule; when they conflict, the project rule wins. — field
- **SG-13** A flow whose state is shared across tabs, windows or instances specifies every identity or state change another instance can cause (sign-in as another user, sign-out, switch), including while this instance is mid-transition. — field
- **SG-14** An AC that states what a given role or caller receives (an empty set, records, a denial) is checked against that role's actual permissions in the sources; the stated outcome must be reachable without widening a permission the sources keep closed. — field
- **SG-15** An assertion over a whole result set (totals, records, counts) names every expected record and value and states the full start state, so a record from another owner or an earlier step cannot make the expected set read two ways. — field
- **SG-16** Where the spec reuses a shared component, an earlier feature's screen or an existing operation, each AC step is checked against that source's real behaviour: its default state, which controls exist in each state, and the order in which it validates (which error wins). Where the design and the shared behaviour differ, the spec picks one and records it. — field
- **SG-17** A relation between two records stated as "earlier/later", "before/after" or "previous/next" names the full ordering key and the tie-break when the leading key can be equal, and an AC covers two records with equal leading keys. — field
- **SG-18** A rule the spec states in more than one place (an AC, a section table, a decision and its rationale, a sibling spec it mirrors) is searched for every statement and made identical; two statements that give different values for the same state are a contradiction to fix before approval. — field
- **SG-19** An AC that states a layout outcome at a viewport (wraps, sits beside, scrolls) is checked against the arithmetic of the spec's own widths, gaps and layout rules; the AC states the numbers it relies on. — field
- **SG-20** The spec names the existing features and modules whose behaviour it reuses, re-specifies or changes. The reviewer searches `docs/features/`, `docs/architecture.md` and the code independently of the author; a missed one that the spec re-specifies as new behaviour, or whose behaviour an AC contradicts without saying so, is Critical, any other miss is a Warning. — seed
- **SG-21** A target count or limit in the spec (a "remaining n", a threshold) is taken from the command's output at the base on the stated scope, not from an estimate or a finding list; the command and its measured value are recorded next to the figure. — field
- **SG-22** An AC that names a test file, test tag or test location is checked against the repository's test-file conventions (the folder the runner collects, the file the AC says it amends); a name the convention cannot hold is a Warning. — field
- **SG-23** A rule that gives an example (an input, a role, a change) per record type or surface is checked for each type against that type's own constraints (uniqueness, required fields, what its form can set); an example one type cannot reach is limited to the types that can, and the spec says so. — field
- **SG-24** A rule that classifies or displays the failures of an operation family on several surfaces (forms, lists, bulk actions) names the behaviour for every error the operation can raise on that surface, read from the operation's source; an error left to the default on one surface is a Warning. — field
- **SG-25** A spec that limits edits of existing tests to named classes (a permitted-change list, "no assertion weakened") also names the follow-on test edits its own decisions force: new helper probes after a permission change, inventories or pins of the objects the spec adds, mocks of a new API. A decision whose consequence in existing tests fits no named class is a Warning. — field
