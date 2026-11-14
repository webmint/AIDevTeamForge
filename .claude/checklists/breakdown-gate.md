# Checklist: breakdown-gate

**Gate**: on — set to `off` to skip this gate (the file is project-owned; deleting it does not work, `update.sh` restores missing checklists).
**Runs**: in `/breakdown`, after the task files are written and before its HARD GATE · **Reviewer**: `general-purpose` on `sonnet` (`_independent-gate.md` → "Model"); a fresh context.
**Inputs**: `specs/<KEY|NNN>-*/tasks/README.md` and every task file; `plan.md`; `contracts.md` and `data-model.md` if present; `spec.md`; `CLAUDE.md`; `.claude/commands/_agent-assignment.md`.

**How to use**:
- Check every item against the artifact and its sources; report each failed item by id with evidence quoted from both sides.
- Severity is Critical, Warning or Suggestion. Critical when an AC has no task, a dependency or wave order would break a build, or a task contradicts a contract. A task that omits or contradicts an AC's literal wording or a contract behaviour is at least a Warning and is fixed, never deferred (`_independent-gate.md` → "Loop").
- Defects outside the list are reported too, as `new`.

**Origin**: `seed` = shipped with Forge; `field` = generalized from defects that escaped earlier gates in field use; `escape <KEY|NNN>/E<n>` = added by this project's /finalize learning step; `audit <date>/<theme>` = added by /audit. New items take the next free id; ids are never reused. An escape that an existing item already covers adds its origin to that item instead of a new item.

## Items

- **BG-01** Every AC maps to at least one task whose Done when proves it; no AC, and no lettered sub-item of an AC, is missing from every task's Spec criteria addressed. — seed
- **BG-02** Every UI AC is covered by an end-to-end test task with the AC id in the test title. — seed
- **BG-03** Dependencies are acyclic and complete: a task depends on every task that produces what its Expects needs, and every Expects is either true in the codebase now or produced upstream. The order follows the project's layers (types and schema first, then logic and data access, then UI, then end-to-end tests). — seed
- **BG-04** Waves group 2–4 consecutive tasks in dependency order; a new wave starts at a dependency fan-in, after a large task, after 4 tasks or before a review checkpoint. Tasks in one wave do not edit the same file unless they are ordered. — seed
- **BG-05** Names, signatures, error codes and file paths in the task files match `plan.md` and `contracts.md` exactly. — seed
- **BG-06** Agent assignment follows `.claude/commands/_agent-assignment.md` and the `CLAUDE.md` table (file layer to agent), and each test sits in the task with the code it tests or in a task that depends on it. — seed
- **BG-07** Every plan item (decision, file, contract) lands in a task, and nothing in the tasks lies outside the plan without a note. — seed
- **BG-08** When one task composes parts that other tasks build, its Done when covers the composed result with its optional inputs, not only each part alone. — seed
- **BG-09** Every control, anchor and action that the spec's screen sections or anchor list name has an owning task, found by searching the task files for each name, not only by reading the AC table. — field
- **BG-10** Every reuse decision in the plan (reuse, extend or new) lands in the task that writes the consumer or creates the new definition. A task that creates an exported symbol the plan does not list is Critical. — seed
