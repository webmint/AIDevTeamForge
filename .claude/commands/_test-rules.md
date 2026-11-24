---
disable-model-invocation: true
user-invocable: false
---
# Test Rules: What a Test Must Prove

Referenced by `/execute-task` (the implementer prompt's Rules and the task review's input 5), by `/breakdown` for the boundary done condition, and by the agents that write tests. Five rules a test can fail, each reported by its name, then how reviewers apply them.

## Purpose

A test names, in its title, the criterion it proves (the AC-titled form `breakdown.md` requires) or, for a test that proves no criterion, the failure it guards against in words. A test that names neither is not written.

## The real boundary

A criterion whose new or changed behaviour crosses an external boundary (a database or query engine, an HTTP API, a mail or queue service, a file another system reads) has at least one test in one of these forms:
- a dry run, or a test instance of the engine or service;
- a dev instance;
- a local server of the protocol, started by the test and delivering nothing outside the machine;
- the dependency's real client against a recorded real response;
- for a file another system reads, that system's own parser, validator or published schema.

A stub of the project's own wrapper is not one of them, and neither is a library's in-memory or JSON transport: it shows what reaches the library, not what the dependency accepts.

**Terms.** A test instance is reserved for tests: local (an emulator, a container) or remote (a test project or dataset). A dev instance is the shared development environment. A dry run, a dev instance and a remote test instance send the request to the remote service; the other forms stay on the machine. A criterion or constraint that rules out the real service in tests ("without a real mail server") is met by the forms that stay on the machine.

**Writes.** For a write to a database or query engine, the case executes the write against a test instance where the project has one and reads the stored value back; otherwise it is a dry run, which checks the statement alone. A test never writes to a shared dev instance (it would leave rows in shared data); a dev instance serves reads and dry runs.

**An existing suite.** When the project already has a suite in one of these forms, every new method that crosses that boundary adds a case to it.

**The done condition** (`/breakdown` writes it for each task that adds or changes behaviour across an external boundary). An unmet done condition goes to a repair agent up to three times and then stops the chain, so it is written to be checkable in the session:
- `- [ ] Boundary test (<form>[, via <dev dependency>]) passes (.claude/commands/_test-rules.md → The real boundary<tail>)`;
- when the plan or `CLAUDE.md` says the suite needs credentials or a service the session lacks: `- [ ] Boundary test (<form>[, via <dev dependency>]) is written in <suite> and collected by it; the user runs: <command> (.claude/commands/_test-rules.md → The real boundary<tail>)`. Such a test skips itself, with the runner's skip and a reason, when its credentials are missing, so the affected-test run passes; "collected" is checked by the runner listing it, skipped.

`<tail>` is empty when the plan already planned a test at the boundary for that criterion; "; beyond the plan's level" when the test is added; "; replaces the plan's text test (Contract, not text)" when it takes the place of a planned test that matches query or statement text; both, in that order, when both hold; then "; overrides plan <DEC id>" when a plan decision chose a test form this rule excludes (for example "tests stub the module's `send`; a local server is rejected"). This rule wins over such a decision for the boundary test, and for the text-matching test it replaces; the plan's decisions stand for the criterion's other tests. The citation, with the named dev dependency, is the note that says why the task goes beyond the plan, for the test and for the manifest change.

The boundary test is written even when the plan chose only unit tests for the criterion. A dev dependency it needs (a local protocol server, an engine's test client) is part of the task: `/breakdown` lists the package manifest and its lockfile among the task's files, and the boundary done condition is the justification for the install. A repair that replaces the boundary test with a stub does not meet the condition; the task review checks that the test is the form its done condition names.

**Structural specs** are exempt: their tests follow `breakdown.md` → "Structural specs".

## Contract, not text

The request a unit builds is checked against a documented contract: the API's documented limits and required headers (TL-21), and the fields the contract names. Query, statement or template text that only the engine can judge is checked by the engine ("The real boundary"), never by matching the text in a unit test.

## One per shape, not one per value

A shape is a case the spec, the contract or a checklist item lists (each variant TL-07 names, each entry path TL-16 names, each case a criterion enumerates, TL-20), or a branch of the code. A listed shape gets its test, as the item already asks; a branch defines a distinct shape but does not by itself require a test. Further values of the same shape get no test. A sweep that checks every entry of a document or catalog (each route, each definition of an API description) is one shape: one test that loops over the entries, not one test case per entry. An expected value comes from the spec, the contract or the design, never from repeating the code's expression (TL-22).

## Not tests

Not written:
- a copy of a constant, label or table;
- a test of the framework or a library (decorator settings, generated routes);
- an assertion only on what a mock received, as the test itself set it up (TL-24);
- a markup or class assertion where the criterion states no style.

A guard the task or a checklist names (a catalog test, a lint rule, a ratchet, PG-Q07's permanent guard) is not a copy, and neither is an expected value taken from the spec, the contract or the design, even when it equals a constant in the code (TL-19's pinned defaults and messages).

## How reviewers apply it

A failed rule is reported by its name, on the review's own scale and in its own sections (the test-lens scale in the task review). A test that fails both a rule and a checklist item (for example "Not tests" and TL-24) is reported once. The boundary test is enforced by its done condition, which `/execute-task` checks in Phase 3.2 before the review, not by a severity of its own.

Like every Forge text, this partial yields to the project's constitution: where a constitution rule conflicts with a rule here, the constitution's rule is followed and the rule here is not reported as failed. A rule that mocks external calls in unit tests does not conflict with "The real boundary". A rule that bans the real service in tests conflicts only with the forms that send the request to the remote service; the forms that stay on the machine are used instead. A rule that allows only unit tests does conflict.
