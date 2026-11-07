#!/usr/bin/env python3
"""Tests for scripts/forge/check-canonical-sources.py and the profile keys canonicalSources and planningSources
(stdlib unittest; Python 3.9+).

A throwaway repository root holds a registry document and two source files, so paths, anchors and symbols can resolve
or fail on purpose. All concepts, paths and symbols are invented.

Run: python3 -m unittest discover -s tests/scripts/forge -v
"""
from __future__ import annotations

import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SCRIPTS = os.path.join(REPO, "scripts", "forge")
sys.path.insert(0, SCRIPTS)
import quality_profile  # noqa: E402

_spec = importlib.util.spec_from_file_location("check_canonical_sources",
                                               os.path.join(SCRIPTS, "check-canonical-sources.py"))
checker = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(checker)

HEADING = "## 9. Registry"
HEADER = (
    "| Concept | Kind | Owner | Single definition | How to consume | Actor / axis of change | Contract | "
    "Consumers and copies | Status | Introduced by |\n|---|---|---|---|---|---|---|---|---|---|\n"
)
GOOD = (
    "| Total of an invoice | derived figure | billing | `src/billing/total.ts` `invoiceTotal` | call it | finance | "
    "`docs/arch.md#totals` | `src/report/view.ts` | single | spec 001 |\n"
    "| Tax rule | variation point | billing | none: two copies | target: one resolver | regulator; second "
    "implementation appeared | none | `src/report/view.ts` | copies 2; issue 7 | spec 002 |\n"
)


class RegistryCase(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.repo)
        self.write("src/billing/total.ts", "export function invoiceTotal() {}\n")
        self.write("src/report/view.ts", "invoiceTotal();\n")
        self.set_rows(GOOD)
        self.profile = os.path.join(self.repo, ".claude", "quality-profile.json")
        self.set_profile({"canonicalSources": {"doc": "docs/arch.md", "heading": HEADING}})

    def set_profile(self, profile: dict) -> None:
        self.write(".claude/quality-profile.json", json.dumps(profile))

    def write(self, rel: str, text: str) -> None:
        path = os.path.join(self.repo, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)

    def set_rows(self, rows: str, header: str = HEADER) -> None:
        self.write("docs/arch.md", f"# Arch\n\n### Totals\n\ntext\n\n{HEADING}\n\nIntro.\n\n{header}{rows}\n## 10. Later\n")

    def run_check(self) -> tuple[int, str]:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = checker.run(self.profile)
        return code, out.getvalue() + err.getvalue()

    def test_a_resolving_registry_passes(self) -> None:
        code, out = self.run_check()
        self.assertEqual(code, 0, out)
        self.assertIn("2 rows: derived figure 1, variation point 1", out)

    def test_a_missing_path_fails(self) -> None:
        self.set_rows(GOOD.replace("src/report/view.ts", "src/report/gone.ts", 1))
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("path `src/report/gone.ts` does not exist", out)

    def test_a_line_suffix_is_ignored_and_a_wrong_anchor_fails(self) -> None:
        self.set_rows(GOOD.replace("`src/report/view.ts` | single", "`src/report/view.ts:1-2` | single")
                      .replace("#totals", "#gone"))
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("anchor `#gone` not found in docs/arch.md", out)
        self.assertNotIn("view.ts:1-2", out)

    def test_a_symbol_missing_from_its_file_fails(self) -> None:
        self.set_rows(GOOD.replace("`invoiceTotal`", "`invoiceSum()`"))
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("symbol `invoiceSum` not found in src/billing/total.ts", out)

    def test_unknown_kind_duplicate_concept_and_no_evidence_fail(self) -> None:
        rows = GOOD + "| Total of an invoice | gadget | x | none | x | x | x | nothing | open | spec 3 |\n"
        self.set_rows(rows)
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("Total of an invoice: listed twice", out)
        self.assertIn("unknown kind `gadget`", out)
        self.assertIn("no existing path cited as evidence", out)

    def test_a_none_row_needs_a_status_and_a_variation_point_needs_an_axis(self) -> None:
        self.set_rows(GOOD.replace("regulator; second implementation appeared", "—").replace("copies 2; issue 7", ""))
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("Tax rule: a variation point names its confirmed axis", out)
        self.assertIn("Tax rule: no single definition and no status", out)

    def test_an_empty_registry_passes_but_a_heading_without_a_table_does_not(self) -> None:
        self.set_rows("")
        code, out = self.run_check()
        self.assertEqual(code, 0)
        self.assertIn("ok (0 rows: empty registry", out)
        self.set_rows("", header="")
        code, out = self.run_check()
        self.assertEqual(code, 2)
        self.assertIn("no registry table under", out)

    def test_missing_columns_and_a_missing_heading(self) -> None:
        self.set_rows("| Total | derived figure | x |\n", header="| Concept | Kind | Owner |\n|---|---|---|\n")
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("missing column: single definition", out)
        self.write("docs/arch.md", "# Arch\n")
        self.assertEqual(self.run_check()[0], 2)

    def test_an_unset_key_prints_one_line_and_passes(self) -> None:
        for profile in ({"canonicalSources": {}}, {}):
            self.set_profile(profile)
            for kwargs in ({}, {"concepts": True}, {"pattern": "tax"}):
                code, out = self.run_lookup(**kwargs)
                self.assertEqual(code, 0, out)
                self.assertEqual(out.splitlines(), ["canonical-sources: canonicalSources is unset in the binding; "
                                                    "no registry to check or look up"])

    def test_a_wrong_type_is_unusable_and_a_missing_profile_is_unset(self) -> None:
        self.set_profile({"canonicalSources": ["docs/arch.md"]})
        self.assertEqual(self.run_check()[0], 2)
        os.remove(self.profile)
        code, out = self.run_check()
        self.assertEqual((code, out.strip()), (0, "canonical-sources: no .claude/quality-profile.json; run python3 scripts/forge/quality_profile.py init"))

    def run_lookup(self, **kwargs) -> tuple[int, str]:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = checker.run(self.profile, **kwargs)
        return code, out.getvalue() + err.getvalue()

    def test_concepts_lists_one_line_per_row(self) -> None:
        code, out = self.run_lookup(concepts=True)
        self.assertEqual(code, 0, out)
        self.assertEqual(out.splitlines(), ["Total of an invoice | derived figure", "Tax rule | variation point"])

    def test_rows_prints_matching_rows_with_the_header(self) -> None:
        code, out = self.run_lookup(pattern="TAX")
        self.assertEqual(code, 0, out)
        lines = out.splitlines()
        self.assertEqual(len(lines), 2)
        self.assertTrue(lines[0].startswith("| Concept | Kind |"))
        self.assertIn("| Tax rule | variation point |", lines[1])
        self.assertIn("no matching row", self.run_lookup(pattern="shipping")[1])
        self.assertEqual(self.run_lookup(pattern="(")[0], 2)

    def test_lookup_does_not_run_the_check(self) -> None:
        self.set_rows(GOOD.replace("src/report/view.ts", "src/report/gone.ts", 1))
        self.assertEqual(self.run_lookup(concepts=True)[0], 0)


class ProfileKeyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.repo)
        with open(os.path.join(self.repo, "plan.md"), "w", encoding="utf-8") as handle:
            handle.write("# Plan\n")

    def problems(self, profile: dict) -> list[str]:
        return quality_profile.validate(profile, repo=self.repo)

    def test_valid_keys_pass(self) -> None:
        profile = {"planningSources": ["plan.md"], "canonicalSources": {"doc": "plan.md", "heading": "## R"}}
        self.assertEqual(self.problems(profile), [])

    def test_missing_files_and_unknown_keys_fail(self) -> None:
        found = self.problems({"planningSources": ["gone.md"], "canonicalSources": {"doc": "gone.md", "extra": 1}})
        self.assertIn("planningSources: gone.md does not exist", found)
        self.assertIn("canonicalSources.doc: gone.md does not exist", found)
        self.assertIn("canonicalSources: unknown key: extra", found)
        self.assertIn("canonicalSources.heading: expected a non-empty str", found)


if __name__ == "__main__":
    unittest.main()
