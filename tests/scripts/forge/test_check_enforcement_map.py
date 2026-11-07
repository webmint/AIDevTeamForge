#!/usr/bin/env python3
"""Tests for scripts/forge/check-enforcement-map.py and the layers and catalogTests sections of
scripts/forge/quality_profile.py (stdlib unittest; Python 3.9+).

A throwaway repository root holds a rules document, a lint config, a test file and a gate file, so every tag kind can
resolve or fail on purpose. All rule ids and names are invented.

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

_spec = importlib.util.spec_from_file_location("check_enforcement_map",
                                               os.path.join(SCRIPTS, "check-enforcement-map.py"))
checker = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(checker)

HEADING = "## Enforcement"
DOC = """# Rules

**R-1. First rule.**
**R-2. Second rule.**

## Enforcement

| Rule | Enforcement | Notes |
|------|-------------|-------|
| R-1 | `lint:acme/no-foo`, `test:tests/foo.test.txt` | covered |
| R-2 | `review-only` | judgement |

## Later
"""


class MapCase(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.repo)
        for rel, text in {
            ".claude/placeholder": "",
            "rules.md": DOC,
            "lint.config": "rules: { 'acme/no-foo': 'error' }\n",
            "tests/foo.test.txt": "ok\n",
            "gates/gate.md": "- **G-1** Reuse is checked.\n",
        }.items():
            self.write(rel, text)
        self.profile = os.path.join(self.repo, ".claude", "quality-profile.json")
        self.write_profile()

    def write(self, rel: str, text: str) -> None:
        path = os.path.join(self.repo, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)

    def write_raw_profile(self, profile: dict) -> None:
        self.write(".claude/quality-profile.json", json.dumps(profile))

    def write_profile(self, **overrides: object) -> None:
        profile = {
            "ratchets": [{"name": "dup", "countCommand": "echo 1"}],
            "baselineFile": ".quality/baseline.json",
            "enforcementMap": {
                "doc": "rules.md",
                "heading": HEADING,
                "rulePattern": r"^\*\*(R-\d+)\.",
                "lintConfigs": ["lint.config"],
                "gateFiles": ["gates/*.md"],
            },
        }
        profile.update(overrides)
        self.write(".claude/quality-profile.json", json.dumps(profile))

    def run_check(self) -> tuple[int, str]:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = checker.run(self.profile)
        return code, out.getvalue() + err.getvalue()

    def set_doc(self, rows: str) -> None:
        self.write("rules.md", DOC.split("| R-1")[0] + rows + "\n\n## Later\n")


class EnforcementMapTests(MapCase):
    def test_an_invalid_section_exits_2_without_a_traceback(self) -> None:
        # rulePattern without a capture group used to raise IndexError, a missing lintConfigs KeyError.
        section = {"doc": "rules.md", "heading": HEADING, "rulePattern": r"^\*\*R-\d+"}
        self.write_profile(enforcementMap=section)
        code, out = self.run_check()
        self.assertEqual(code, 2)
        for problem in ("enforcementMap.lintConfigs: missing", "enforcementMap.gateFiles: missing",
                        "enforcementMap.rulePattern: needs a capture group (the rule id)"):
            self.assertIn(problem, out)
        self.assertNotIn("Traceback", out)

    def test_a_resolving_map_passes(self) -> None:
        code, out = self.run_check()
        self.assertEqual(code, 0, out)
        self.assertIn("2 rules, 1 machine-checked, 1 review-only", out)

    def test_a_lint_rule_that_is_not_configured_fails(self) -> None:
        self.set_doc("| R-1 | `lint:acme/no-bar` | x |\n| R-2 | `review-only` | y |")
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("lint rule `acme/no-bar` is not configured", out)

    def test_a_lint_id_is_not_matched_inside_a_longer_id(self) -> None:
        self.write("lint.config", "rules: { 'acme/no-foo-extra': 'error' }\n")
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("acme/no-foo", out)

    def test_a_missing_test_file_fails(self) -> None:
        self.set_doc("| R-1 | `test:tests/gone.test.txt` | x |\n| R-2 | `review-only` | y |")
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("test file `tests/gone.test.txt` does not exist", out)

    def test_gate_and_ratchet_tags_resolve_or_fail(self) -> None:
        self.set_doc("| R-1 | `gate:G-1`, `ratchet:dup` | x |\n| R-2 | `gate:G-9` | y |")
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("R-2: gate text `G-9`", out)
        self.assertNotIn("R-1:", out)
        self.set_doc("| R-1 | `ratchet:nope` | x |\n| R-2 | `review-only` | y |")
        self.assertIn("ratchet `nope` is not defined", self.run_check()[1])

    def test_a_row_without_a_tag_and_a_mixed_review_only_row_fail(self) -> None:
        self.set_doc("| R-1 | none | x |\n| R-2 | `review-only`, `gate:G-1` | y |")
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("R-1: no enforcement tag", out)
        self.assertIn("R-2: review-only cannot be combined", out)

    def test_a_declared_rule_without_a_row_fails(self) -> None:
        self.set_doc("| R-1 | `gate:G-1` | x |")
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("R-2: declared in the rules document but missing", out)

    def test_an_unknown_tag_kind_fails(self) -> None:
        self.set_doc("| R-1 | `magic:x` | x |\n| R-2 | `review-only` | y |")
        self.assertIn("unknown tag `magic:x`", self.run_check()[1])

    def test_a_missing_heading_is_unusable(self) -> None:
        self.write("rules.md", "# Rules\n")
        self.assertEqual(self.run_check()[0], 2)

    def test_a_separate_rules_doc_declares_the_rule_ids(self) -> None:
        section = {"doc": "rules.md", "heading": HEADING, "rulePattern": r"^\*\*(R-\d+)\.",
                   "lintConfigs": ["lint.config"], "gateFiles": ["gates/*.md"], "rulesDoc": "constitution.md"}
        self.write("constitution.md", "# Constitution\n\n**R-1.** one\n\n**R-9.** nine\n")
        self.write_profile(enforcementMap=section)
        code, out = self.run_check()
        self.assertEqual(code, 1, out)
        self.assertIn("R-9: declared in the rules document but missing from the enforcement map", out)
        self.write("constitution.md", "# Constitution\n\n**R-1.** one\n")
        self.assertEqual(self.run_check()[0], 0, self.run_check()[1])
        self.write("constitution.md", "# Constitution\n")
        self.assertEqual(self.run_check()[0], 0)
        os.remove(os.path.join(self.repo, "constitution.md"))
        self.assertEqual(self.run_check()[0], 2)

    def test_an_unset_key_prints_one_line_and_passes(self) -> None:
        for profile in ({"enforcementMap": {}, "ratchets": []}, {}):
            self.write_raw_profile(profile)
            code, out = self.run_check()
            self.assertEqual(code, 0, out)
            self.assertEqual(out.splitlines(), ["enforcement-map: enforcementMap is unset in the binding; no map to check"])

    def test_unset_ratchets_leave_a_ratchet_tag_unresolved(self) -> None:
        self.write_profile(ratchets=[], baselineFile="")
        self.set_doc("| R-1 | `ratchet:dup` | x |\n| R-2 | `review-only` | y |")
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("ratchet `dup` is not defined in the profile", out)

    def test_a_wrong_type_is_unusable_and_a_missing_profile_is_unset(self) -> None:
        self.write_raw_profile({"enforcementMap": "rules.md"})
        self.assertEqual(self.run_check()[0], 2)
        os.remove(self.profile)
        self.assertEqual(self.run_check(), (0, "enforcement-map: no .claude/quality-profile.json; run python3 scripts/forge/quality_profile.py init\n"))


class ProfileSectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.repo)
        os.makedirs(os.path.join(self.repo, "src", "mod", "ui"))

    def problems(self, profile: dict) -> list[str]:
        return quality_profile.validate(profile, repo=self.repo)

    def test_a_valid_layers_section_passes(self) -> None:
        layers = {
            "scope": "src/mod/",
            "layers": [
                {"name": "top", "dirs": ["ui"], "mayImport": ["low"]},
                {"name": "low", "dirs": ["io"], "mayImport": []},
            ],
            "sharedDirs": ["types"],
        }
        self.assertEqual(self.problems({"layers": layers}), [])

    def test_layers_reject_unknown_targets_shared_dirs_in_a_layer_and_self_reference(self) -> None:
        layers = {
            "scope": "src/mod/",
            "layers": [
                {"name": "top", "dirs": ["ui"], "mayImport": ["ghost", "top"]},
                {"name": "low", "dirs": ["ui"], "mayImport": []},
            ],
            "sharedDirs": ["ui"],
        }
        found = self.problems({"layers": layers})
        self.assertIn("layers.layers[0].mayImport: unknown layer: ghost", found)
        self.assertIn("layers.layers[0].mayImport: a layer lists itself", found)
        self.assertIn("layers.layers: a directory belongs to two layers", found)
        self.assertIn("layers.sharedDirs: a shared directory is also a layer directory", found)

    def test_catalog_tests_must_exist(self) -> None:
        self.assertEqual(len(self.problems({"catalogTests": ["nope.sql"]})), 1)


if __name__ == "__main__":
    unittest.main()
