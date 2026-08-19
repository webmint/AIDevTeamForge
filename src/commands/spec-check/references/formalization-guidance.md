# Formalization guidance — worked NL→IR examples

The orchestrator injects this file into the `spec-formalizer` Task prompt in
PHASE 2, after the machine OUTPUT CONTRACT the `render-formalize-brief` verb
emits. The agent's own body (`.claude/agents/spec-formalizer.md`) carries the
translation RULES; this file grounds them with concrete AC → IR examples.

Every example shows the acceptance criterion text and the exact JSON IR it
formalizes to. The IR is one object with three top-level arrays — `variables`,
`constraints`, `coverage` — using the flat atom shapes: numeric
`{"var","op","value"}`, Bool `{"var","negated"}`, Enum `{"var","op","value"}`.
Every variable also carries a `subject_resolution` record; the fourth rule below
states it and Examples 6–8 work all three of its shapes.

The brief above lists each AC as `**AC-1** (<subsection>): <text>` when the spec
recorded a subsection for it, and as `**AC-1**: <text>` when it did not. That
subsection annotation is the primary preservation trigger (fourth rule below):
Example 6 shows it firing. Examples 1–5, 7 and 8 quote the unannotated form, and
Example 8 shows the secondary (wording) trigger firing without it.

## Four load-bearing rules (the agent enforces these; the examples show them)

- **Skip honestly, never force.** A subjective/non-logical AC → `skipped_prose`;
  an AC whose logic the IR cannot express (e.g. arithmetic over 2+ variables) →
  `skipped_unsupported`. Both carry a `reason`. A forced bad translation produces
  a false verdict and is worse than an honest skip.
- **Co-refer.** The SAME real-world quantity across different ACs MUST become the
  SAME variable `name`, declared once in `variables[]` and reused — that is
  exactly how the solver sees a cross-AC conflict. Splitting one quantity across
  two names hides the conflict.
- **The `gloss` is the human's check.** Each variable's `gloss` is the
  plain-English meaning the human reads to catch a mistranslation. Treat it as
  required substance, not decoration.
- **Resolve the subject before you formalize.** Before writing any constraint
  over a quantity, establish what PRODUCES the state it models and record that
  in the variable's `subject_resolution`: the **code arm** cites a construction
  site in the existing codebase (`citation` = repo-relative path, `locator` = a
  symbol name or verbatim fragment present in that file, `note` = what was found
  — that pair is checked mechanically), the **spec arm** cites the spec's own
  declaration of new behavior (`citation` = the section or AC id, `locator`
  omitted). Preservation is code-arm-only under TWO triggers: the PRIMARY
  trigger is the AC's subsection — an AC the brief renders as
  `**AC-1** (5.2 Behavior preservation): <text>` resolves via the code arm
  REGARDLESS of how it is worded — and the SECONDARY trigger is the wording — an
  AC under any OTHER subsection whose statement presupposes presently-existing
  behavior ALSO resolves via the code arm, checked whether or not the subsection
  trigger fired. Either way, a preservation subject resolvable only via the spec
  arm is UNRESOLVED. The search is bounded per subject — at most three search
  terms, five files opened (a file opened as a hop target counts toward that
  cap), one hop from a hit, and the first mechanically-checkable site wins — and
  when it comes up empty the record is
  `{"status": "unresolved", "searched": "…"}`, that AC's
  coverage is `unresolved_subject` naming the variable in `subject`, and the AC
  contributes NO constraints. An AC over a state nothing constructs is
  unfalsifiable, and an unfalsifiable AC conflicts with nothing — formalizing it
  would prove "consistent" for free.

## Example 1 — a numeric threshold AC → `assertion`

AC text: *"AC-3: The system shall respond to a delete request within 100ms."*

```json
{
  "variables": [
    {"name": "response_ms", "sort": "Real", "gloss": "delete-request response latency in milliseconds", "subject_resolution": {"status": "resolved", "arm": "code", "citation": "src/api/records.py", "locator": "def delete_record", "note": "records.delete_record serves the delete request whose latency this quantity measures"}}
  ],
  "constraints": [
    {"ac_id": "AC-3", "kind": "assertion", "consequent": [{"var": "response_ms", "op": "<", "value": 100}]}
  ],
  "coverage": [
    {"ac_id": "AC-3", "status": "formalized"}
  ]
}
```

A plain `shall` invariant with no trigger is a `kind: assertion` — the
`consequent` is the outcome that must always hold. If a second AC asserted
`response_ms > 200` over the same `response_ms` variable, the solver would return
`unsat` with the two conflicting `ac_id`s as the core.

## Example 2 — an EARS trigger AC → `implication`

AC text: *"AC-4: WHEN the cart is empty, checkout shall be disabled."*

```json
{
  "variables": [
    {"name": "cart_empty", "sort": "Bool", "gloss": "the shopping cart contains zero items", "subject_resolution": {"status": "resolved", "arm": "code", "citation": "src/cart/cart_state.ts", "locator": "isCartEmpty", "note": "cart_state.isCartEmpty derives the empty-cart flag from the line-item list"}},
    {"name": "checkout_enabled", "sort": "Bool", "gloss": "the checkout action is available to the user", "subject_resolution": {"status": "resolved", "arm": "code", "citation": "src/checkout/CheckoutButton.tsx", "locator": "canCheckout", "note": "CheckoutButton renders from canCheckout, which is the availability of the checkout action"}}
  ],
  "constraints": [
    {"ac_id": "AC-4", "kind": "implication", "antecedent": [{"var": "cart_empty", "negated": false}], "consequent": [{"var": "checkout_enabled", "negated": true}]}
  ],
  "coverage": [
    {"ac_id": "AC-4", "status": "formalized"}
  ]
}
```

An EARS trigger/condition form (`WHEN`, `WHILE`, `WHERE`, `IF…THEN`) is a
`kind: implication` — the trigger/condition is the `antecedent` (a multi-atom
conjunction is allowed), the required outcome is the `consequent`. Here "checkout
shall be disabled" is `checkout_enabled` = false, so the Bool atom is
`{"var": "checkout_enabled", "negated": true}`.

## Example 3 — a permission GRANT vs a restriction (the permission-clash case)

Two ACs, formalized together so the shared variables co-refer:

- AC text: *"AC-6: Only admins can delete a record."*
- AC text: *"AC-7: A support agent (a non-admin) can delete a stuck record."*

```json
{
  "variables": [
    {"name": "can_delete", "sort": "Bool", "gloss": "the acting user is permitted to delete a record", "subject_resolution": {"status": "resolved", "arm": "code", "citation": "src/auth/permissions.py", "locator": "def can_delete", "note": "permissions.can_delete computes the acting user's delete permission"}},
    {"name": "is_admin", "sort": "Bool", "gloss": "the acting user holds the admin role", "subject_resolution": {"status": "resolved", "arm": "code", "citation": "src/auth/roles.py", "locator": "ADMIN_ROLE", "note": "roles assigns ADMIN_ROLE, the role membership this criterion reads"}}
  ],
  "constraints": [
    {"ac_id": "AC-6", "kind": "implication", "antecedent": [{"var": "can_delete", "negated": false}], "consequent": [{"var": "is_admin", "negated": false}]},
    {"ac_id": "AC-7", "kind": "assertion", "consequent": [{"var": "can_delete", "negated": false}, {"var": "is_admin", "negated": true}]}
  ],
  "coverage": [
    {"ac_id": "AC-6", "status": "formalized"},
    {"ac_id": "AC-7", "status": "formalized"}
  ]
}
```

The RESTRICTION "only admins can delete" is a rule → `implication`
(`can_delete ⇒ is_admin`). The GRANT "a non-admin can delete" asserts a reachable
case → an `assertion` of `can_delete ∧ ¬is_admin`, NOT another implication. This
is the load-bearing move: the solver detects the clash (`unsat`, core
`{AC-6, AC-7}`) ONLY because the permitting scenario is ASSERTED reachable. If
BOTH were formalized as pure implications, the solver would correctly return
`sat` — a rule set that merely permits is genuinely consistent until a permitted
case is asserted. Formalize a permission-grant statement ("<role> can <action>")
as an assertion of the reachable case; if a statement is genuinely a conditional
rule rather than a reachable grant, formalize it as an implication and let it
stand.

## Example 4 — a subjective prose AC → `skipped_prose`

AC text: *"AC-5: The UI should feel responsive and uncluttered."*

```json
{
  "variables": [],
  "constraints": [],
  "coverage": [
    {"ac_id": "AC-5", "status": "skipped_prose", "reason": "'feel responsive and uncluttered' is subjective — no logical quantity to formalize"}
  ]
}
```

A subjective or non-logical criterion has no real-world quantity to name. Record
it as `skipped_prose` with a reason — never force it into a constraint.

## Example 5 — arithmetic over two variables → `skipped_unsupported`

AC text: *"AC-9: The order total shall equal the subtotal plus tax."*

```json
{
  "variables": [],
  "constraints": [],
  "coverage": [
    {"ac_id": "AC-9", "status": "skipped_unsupported", "reason": "arithmetic relating three variables (total = subtotal + tax) — the flat-atom IR cannot express multi-variable arithmetic"}
  ]
}
```

The flat atom shape is one variable, one op, one value — it cannot express an
equation over 2+ variables. Record such an AC as `skipped_unsupported` with a
reason; it is outside the check by design, and the coverage ledger makes that
honest to the reader.

## Example 6 — a preservation AC resolved through the CODE arm

AC text, as the brief renders it: *"**AC-2** (5.2 Behavior preservation): The
exporter shall continue to emit the `legacy_id` column on every exported row."*

```json
{
  "variables": [
    {"name": "legacy_id_emitted", "sort": "Bool", "gloss": "the export writer includes the legacy_id column in each exported row", "subject_resolution": {"status": "resolved", "arm": "code", "citation": "src/export/row_writer.py", "locator": "_build_row", "note": "row_writer._build_row appends the legacy_id column for every exported row"}}
  ],
  "constraints": [
    {"ac_id": "AC-2", "kind": "assertion", "consequent": [{"var": "legacy_id_emitted", "negated": false}]}
  ],
  "coverage": [
    {"ac_id": "AC-2", "status": "formalized"}
  ]
}
```

The rendered subsection is `5.2 Behavior preservation`, so the PRIMARY
preservation trigger fires and this AC is CODE-ARM-ONLY regardless of how it is
worded: the state it talks about must already be produced somewhere in the
existing codebase. The wording ("shall continue to") points the same way here,
but that is the SECONDARY trigger and it is not what decided this case — an AC
under this subsection worded as a plain `shall` invariant would be code-arm-only
just the same, because the subsection is the primary key and re-framing the claim
is no exit from it. If the only thing citable were the spec's own text, the
subject would be UNRESOLVED — "this behavior is preserved" and "this feature
introduces it" cannot both be true. The `citation` + `locator` pair is checked
mechanically (the cited file must exist under the repo root and `_build_row` must
appear in it verbatim), so cite a path you actually opened and a symbol you
actually read — a guessed path fails the check and the resolution does not stand.
What a code-arm resolution proves is bounded: the column is emitted at a site the
search reached, not that it is emitted at every site, and the check confirms the
citation points at real text, not that it points at the RIGHT text. The `note` is
what the human reads to judge that.

## Example 7 — a new-behavior AC resolved through the SPEC arm

AC text: *"AC-8: WHEN an export finishes, the system shall set the archive's
retention to 30 days."* — retention is behavior this feature introduces; no code
sets it today.

```json
{
  "variables": [
    {"name": "export_finished", "sort": "Bool", "gloss": "the export job has reached its terminal finished state", "subject_resolution": {"status": "resolved", "arm": "code", "citation": "src/export/job_runner.py", "locator": "mark_finished", "note": "job_runner.mark_finished sets the terminal finished state on an export job"}},
    {"name": "retention_days", "sort": "Int", "gloss": "days a finished export archive is retained before deletion", "subject_resolution": {"status": "resolved", "arm": "spec", "citation": "spec.md §3.2 Retention", "note": "retention is new behavior this feature introduces; §3.2 declares it and no code sets it yet"}}
  ],
  "constraints": [
    {"ac_id": "AC-8", "kind": "implication", "antecedent": [{"var": "export_finished", "negated": false}], "consequent": [{"var": "retention_days", "op": "=", "value": 30}]}
  ],
  "coverage": [
    {"ac_id": "AC-8", "status": "formalized"}
  ]
}
```

Resolution is per VARIABLE, not per AC — one criterion's two variables resolve
through different arms here. `export_finished` presupposes behavior that exists
today — the SECONDARY preservation trigger, checked on an AC under any subsection
— so it takes the code arm. `retention_days` is introduced by this feature,
so the spec arm is the honest answer: `citation` is the section that declares the
new behavior, and `locator` is OMITTED (on the spec arm the citation IS the
locator; including one is a schema error). The spec arm is not a shortcut for "I
could not find it in the code" — that outcome is `unresolved`, shown next. Only
the code arm is filesystem-checked, so the spec arm rests entirely on the reader's
judgment; the `note` must therefore say plainly that the state does not exist yet.

## Example 8 — a subject nothing constructs → `unresolved_subject`

AC text: *"AC-11: The dashboard shall continue to show the per-tenant quota
banner while a tenant is over quota."* — no such banner exists; the AC preserves
a behavior that was never built.

```json
{
  "variables": [
    {"name": "tenant_over_quota", "sort": "Bool", "gloss": "the tenant's usage exceeds its quota", "subject_resolution": {"status": "resolved", "arm": "code", "citation": "src/billing/quota.py", "locator": "def is_over_quota", "note": "quota.is_over_quota computes the over-quota condition per tenant"}},
    {"name": "quota_banner_shown", "sort": "Bool", "gloss": "the dashboard renders the per-tenant over-quota banner", "subject_resolution": {"status": "unresolved", "searched": "grepped 'quota_banner', 'QuotaBanner', 'over.?quota.*banner' (3 terms — the term bound) under src/dashboard/ and src/components/; opened src/dashboard/Dashboard.tsx, src/dashboard/DashboardHeader.tsx, src/components/Banner.tsx, then followed the one permitted hop from Banner.tsx to its caller src/components/AlertRail.tsx and opened that too (4 of at most 5 files, the hop target included); Banner renders alert and upgrade variants only; no site constructs or renders an over-quota banner"}}
  ],
  "constraints": [],
  "coverage": [
    {"ac_id": "AC-11", "status": "unresolved_subject", "subject": "quota_banner_shown"}
  ]
}
```

This is the case the whole duty exists for. The brief recorded no subsection for
AC-11, so the primary trigger never fired — but "shall continue to show"
presupposes presently-existing behavior, which is the SECONDARY trigger, and it
is checked whether or not the subsection trigger fired. So the spec arm was never
available here either: a state this feature would have to INTRODUCE cannot also
be one it PRESERVES. And nothing in the codebase constructs the banner, so the AC
is unfalsifiable: had it been formalized anyway, the solver would have proven it
"consistent" for free, because a state nothing produces can never conflict with
anything. Instead:

- The unresolved variable is still DECLARED, carrying its
  `{"status": "unresolved", "searched": …}` record — that record is the evidence,
  so it has to be inspectable. No other field is present on an unresolved record.
- `constraints` is EMPTY for AC-11. An unresolved variable may not appear in any
  constraint of any AC, not even a different one.
- The coverage entry is `unresolved_subject` and its `subject` field NAMES the
  unresolved variable — required for this status, because an AC with no
  constraints has no other path back to the record that explains it. A `reason`
  is optional here; the detail already lives in `searched`.
- `tenant_over_quota` resolved cleanly and stays declared even though it now
  appears in no constraint. ONE unresolved variable is enough to make the whole
  AC `unresolved_subject`.

The `searched` text above is falsifiable: it names the actual terms, the actual
paths, how much of the bound was spent (3 of at most 3 terms, 4 of at most 5 files
counting the hop target, the one permitted hop), and what was found instead.
"Searched the codebase and found nothing" is not a searched record — a human
cannot check it. The bound is deliberate and per subject — at most three search
terms, five files opened, one hop from a hit, and the first mechanically-checkable
construction site ends the search. A file opened as a hop target spends the file
budget like any other open: one budget, not two. When the bound runs out,
`unresolved` is the correct and honest outcome, never a defeat to paper over with
the nearest plausible-looking file.
