#!/usr/bin/env python3
"""Tests for scripts/forge/research_lint.py (stdlib unittest), on the synthetic project of research_fixtures.py.

Run: python3 -m unittest discover -s tests/scripts/forge -p 'test_research_lint.py' -v
"""
from __future__ import annotations

import io
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(REPO, "scripts", "forge"))
sys.path.insert(0, HERE)
import research_fixtures as fx  # noqa: E402
import research_lint  # noqa: E402

COVERAGE = """## Coverage
- `getProfile` `src/js/handler.js:4` — read — `src/js/handler.js:5` `checkAccess(req.user, req.params.id);` [top-down]
- `checkAccess` `src/js/auth.js:1` — read — `src/js/auth.js:2` `if (user.id !== id) throw new Error` [closure]
- `buildUserPath` `src/js/paths.js:7` — read — `src/js/paths.js:8-9` `const clean = normalizeSegment(userId);` [closure]
- `normalizeSegment` `src/js/paths.js:3` — read — `src/js/paths.js:4` `return seg.trim().toLowerCase();` [closure]
"""

FACETS = """## Facets
- **1. Entry point**: `src/js/handler.js:4` `async function getProfile(req) {`
- **2. Authorisation path**: `src/js/auth.js:2` `if (user.id !== id) throw new Error`
- **3. Data path**: `src/js/paths.js:9` `return join(root, "users", clean);`
- **4. Data model**: none — searched: users, profile in src/
- **5. Validators and normalisers**: `src/js/paths.js:4` `return seg.trim().toLowerCase();`
- **6. Error mapping**: none — searched: catch, Error in src/js
- **7. Runtime limits and configuration**: none — searched: timeout, memory in src/, config/
- **8. Test infrastructure**: none — searched: test/, fake, mock
- **9. Duplicates**: `src/py/store.py:5` `return key.strip().lower()`
- **10. Contracts and docs**: none — searched: docs/, openapi
"""

ROUTES = """## Search routes
- top-down: from `getProfile`; reached checkAccess, buildUserPath
- bottom-up: from `users`; reached buildUserPath; only this route: none
"""

SUMMARY = """# Research: profile path

## Summary

The profile path is built from the user id after `normalizeSegment` lowers it.
"""


def report(summary=SUMMARY, coverage=COVERAGE, facets=FACETS, routes=ROUTES):
    return summary + "\n" + routes + "\n" + facets + "\n" + coverage


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.root = os.path.join(self.tmp, "proj")
        fx.write_project(self.root)
        os.makedirs(os.path.join(self.root, "research"))
        self.report = os.path.join(self.root, "research", "2026-11-13-topic.md")
        self.ledger = os.path.join(self.root, "research", "2026-11-13-topic-ledger.md")
        self.out = os.path.join(self.root, "research", "2026-11-13-topic-research-lint.txt")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def lint(self, text, ledger=fx.LEDGERS["js"], *extra):
        with open(self.report, "w", encoding="utf-8") as handle:
            handle.write(text)
        if ledger is not None:
            with open(self.ledger, "w", encoding="utf-8") as handle:
                handle.write(ledger)
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = research_lint.main([self.report, "--root", self.root] + list(extra))
        return code, out.getvalue(), err.getvalue()


class CoverageTest(Base):
    def test_clean_report(self):
        code, out, _ = self.lint(report())
        self.assertEqual(code, 0, out)
        self.assertIn("research-lint: 0 blocking, 0 advisory", out)
        with open(self.out, encoding="utf-8") as handle:
            self.assertEqual(handle.read(), out)

    def test_missing_row(self):
        cov = "\n".join(l for l in COVERAGE.splitlines() if "`normalizeSegment` `src" not in l) + "\n"
        code, out, _ = self.lint(report(coverage=cov))
        self.assertEqual(code, 1)
        self.assertIn("no_coverage_row D2 `normalizeSegment` src/js/paths.js:3", out)

    def test_read_row_quote_must_verify(self):
        cov = COVERAGE.replace("`return seg.trim().toLowerCase();` [closure]", "`return seg.toLowerCase();` [closure]")
        code, out, _ = self.lint(report(coverage=cov))
        self.assertEqual(code, 1)
        self.assertIn("quote_mismatch src/js/paths.js:4", out)

    def test_read_row_quote_must_be_on_the_item(self):
        cov = COVERAGE.replace("`src/js/paths.js:4` `return seg.trim().toLowerCase();`",
                               "`src/py/store.py:5` `return key.strip().lower()`")
        code, out, _ = self.lint(report(coverage=cov))
        self.assertEqual(code, 1)
        self.assertIn("read_quote_not_on_item", out)
        cov = COVERAGE.replace("`src/js/paths.js:8-9` `const clean = normalizeSegment(userId);`",
                               "`src/js/paths.js:4` `return seg.trim().toLowerCase();`")
        code, out, _ = self.lint(report(coverage=cov))
        self.assertEqual(code, 1)
        self.assertIn("read_quote_not_on_item", out)
        self.assertIn("inside its ledger body", out)

    def test_read_row_needs_a_quote(self):
        cov = COVERAGE.replace("`src/js/paths.js:4` `return seg.trim().toLowerCase();` [closure]", "skimmed")
        code, out, _ = self.lint(report(coverage=cov))
        self.assertEqual(code, 1)
        self.assertIn("read_without_quote", out)

    def test_excluded_needs_reason_and_bad_status(self):
        cov = COVERAGE.replace(
            "— read — `src/js/auth.js:2` `if (user.id !== id) throw new Error` [closure]", "— excluded")
        cov = cov.replace("— read — `src/js/handler.js:5`", "— skimmed — `src/js/handler.js:5`")
        code, out, _ = self.lint(report(coverage=cov))
        self.assertEqual(code, 1)
        self.assertIn("excluded_without_reason", out)
        self.assertIn("coverage_bad_status", out)

    def test_over_cap_rows(self):
        cov = COVERAGE.replace("— read — `src/js/paths.js:4` `return seg.trim().toLowerCase();` [closure]",
                               "— not covered: over cap")
        code, out, _ = self.lint(report(coverage=cov), fx.LEDGERS["js"], "--cap", "3")
        self.assertEqual(code, 0, out)
        code, out, _ = self.lint(report(coverage=cov))
        self.assertEqual(code, 1)
        self.assertIn("over_cap_in_cap", out)

    def test_no_coverage_and_no_ledger(self):
        code, out, _ = self.lint(report(coverage=""), None)
        self.assertEqual(code, 1)
        self.assertIn("no_coverage_section", out)
        self.assertIn("no_ledger", out)


class FacetsRoutesClaimsTest(Base):
    def test_facet_missing_and_unsupported(self):
        facets = FACETS.replace("- **6. Error mapping**: none — searched: catch, Error in src/js\n", "")
        facets = facets.replace("none — searched: test/, fake, mock", "the tests use a fake store")
        code, out, _ = self.lint(report(facets=facets))
        self.assertEqual(code, 1)
        self.assertIn("facet_missing L0 6. error mapping", out)
        self.assertIn("facet_unsupported", out)
        self.assertIn("8. test infrastructure", out)

    def test_facet_quote_must_verify(self):
        facets = FACETS.replace("`return key.strip().lower()`", "`return key.lower()`")
        code, out, _ = self.lint(report(facets=facets))
        self.assertEqual(code, 1)
        self.assertIn("quote_mismatch src/py/store.py:5", out)
        self.assertIn("facet_unsupported", out)

    def test_search_routes(self):
        code, out, _ = self.lint(report(routes=""))
        self.assertEqual(code, 1)
        self.assertIn("no_search_routes L0 -", out)
        code, out, _ = self.lint(report(routes="## Search routes\n- top-down: from the handler\n"))
        self.assertEqual(code, 1)
        self.assertIn("no_search_routes L0 no bottom-up bullet", out)

    def test_claims_are_advisory(self):
        summary = SUMMARY + "\nThe id is never trimmed before the access check.\n" \
                            "`src/js/paths.js:4` `return seg.trim().toLowerCase();` — trims the segment.\n"
        code, out, _ = self.lint(report(summary=summary))
        self.assertEqual(code, 0, out)
        claims = [l for l in out.splitlines() if l.startswith("advisory claim_without_quote")]
        self.assertEqual(len(claims), 1, out)
        self.assertIn("never trimmed", claims[0])

    def test_unreadable_report_is_exit_2(self):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = research_lint.main([os.path.join(self.root, "research", "none.md"), "--root", self.root])
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
