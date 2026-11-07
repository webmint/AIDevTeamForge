#!/usr/bin/env python3
"""Tests for scripts/forge/check-decision-records.py and the profile key decisionRecords (stdlib unittest;
Python 3.9+).

A throwaway git repository holds a frozen log, a base branch and a work branch, so rows added after the merge base
and fragment files can pass or fail on purpose. All rows and names are invented.

Run: python3 -m unittest discover -s tests/scripts/forge -v
"""
from __future__ import annotations

import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SCRIPTS = os.path.join(REPO, "scripts", "forge")
sys.path.insert(0, SCRIPTS)
import quality_profile  # noqa: E402

_spec = importlib.util.spec_from_file_location("check_decision_records",
                                               os.path.join(SCRIPTS, "check-decision-records.py"))
checker = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(checker)

HEADER = "| Date | Spec | Decision | Rationale | Source |\n|------|------|----------|-----------|--------|\n"
LOG = "# Log\n\n> Frozen.\n\n" + HEADER + "| 2026-01-01 | 001-a | D-1: one | because | brief |\n"
SECTION = {
    "log": "docs/log.md",
    "frozenOn": "2026-01-10",
    "fragments": "docs/decisions",
    "fragmentName": "^(\\d{3}-[a-z0-9-]+|fix-[a-z0-9-]+|chore-[a-z0-9-]+)$",
}


class RecordsCase(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.repo)
        self.git("init", "-q", "-b", "base")
        self.git("config", "user.email", "t@example.invalid")
        self.git("config", "user.name", "t")
        self.profile = os.path.join(self.repo, ".claude", "quality-profile.json")
        self.set_profile({"integrationRef": "base", "decisionRecords": SECTION})
        self.write("docs/log.md", LOG)
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "base")
        self.git("checkout", "-q", "-b", "work")

    def git(self, *args: str) -> None:
        subprocess.run(["git", "-c", "commit.gpgsign=false", "-C", self.repo, *args], check=True, capture_output=True)

    def set_profile(self, profile: dict) -> None:
        self.write(".claude/quality-profile.json", json.dumps(profile))

    def write(self, rel: str, text: str) -> None:
        path = os.path.join(self.repo, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)

    def run_check(self, *args: str) -> tuple[int, str]:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = checker.main(["--profile", self.profile, *args])
        return code, out.getvalue() + err.getvalue()


class LogFreezeTest(RecordsCase):
    def test_untouched_log_passes(self) -> None:
        code, out = self.run_check()
        self.assertEqual(code, 0, out)

    def test_row_dated_after_freeze_fails(self) -> None:
        self.write("docs/log.md", LOG + "| 2026-01-11 | 002-b | D-1: late | x | y |\n")
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("added after the freeze", out)

    def test_committed_row_after_freeze_fails(self) -> None:
        self.write("docs/log.md", LOG + "| 2026-02-01 | 002-b | D-1: late | x | y |\n")
        self.git("commit", "-q", "-am", "late row")
        self.assertEqual(self.run_check()[0], 1)

    def test_row_without_date_fails(self) -> None:
        self.write("docs/log.md", LOG + "| soon | 002-b | D-1 | x | y |\n")
        self.assertEqual(self.run_check()[0], 1)

    def test_row_within_grace_passes(self) -> None:
        self.write("docs/log.md", LOG + "| 2026-01-10 | 002-b | D-1: open branch | x | y |\n")
        code, out = self.run_check()
        self.assertEqual(code, 0, out)

    def test_row_already_on_base_passes(self) -> None:
        self.git("checkout", "-q", "base")
        self.write("docs/log.md", LOG + "| 2026-03-01 | 003-c | D-1 | x | y |\n")
        self.git("commit", "-q", "-am", "on base")
        code, out = self.run_check()
        self.assertEqual(code, 0, out)

    def test_note_outside_table_passes(self) -> None:
        self.write("docs/log.md", "# Log\n\nAnother note.\n" + LOG[5:])
        self.assertEqual(self.run_check()[0], 0)

    def test_missing_base_is_unusable(self) -> None:
        self.assertEqual(self.run_check("--base", "no-such-ref")[0], 2)


class FragmentTest(RecordsCase):
    def test_good_fragment_passes(self) -> None:
        self.write("docs/decisions/002-b.md", "# Decisions: 002-b\n\n" + HEADER + "| 2026-02-01 | 002-b | D-1 | x | y |\n")
        code, out = self.run_check()
        self.assertEqual(code, 0, out)
        self.assertIn("1 fragment", out)

    def test_dotfiles_readme_and_other_files_are_not_fragments(self) -> None:
        self.write("docs/decisions/002-b.md", "# Decisions: 002-b\n\n" + HEADER + "| 2026-02-01 | 002-b | D-1 | x | y |\n")
        self.write("docs/decisions/README.md", "# Fragments\n\nOne file per unit.\n")
        self.write("docs/decisions/.gitkeep", "")
        with open(os.path.join(self.repo, "docs/decisions/.DS_Store"), "wb") as handle:
            handle.write(b"\x00\x00\x00\x01Bud1\xff\xfe")
        code, out = self.run_check()
        self.assertEqual(code, 0, out)
        self.assertIn("1 fragment(s)", out)
        code, out = self.run_check("--list")
        self.assertEqual(code, 0, out)

    def test_bad_name_fails(self) -> None:
        self.write("docs/decisions/Notes.md", HEADER + "| 2026-02-01 | a | b | c | d |\n")
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("name does not match", out)

    def test_wrong_header_fails(self) -> None:
        self.write("docs/decisions/chore-x.md", "| Date | Decision |\n|---|---|\n| 2026-02-01 | x |\n")
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("no table with the log's header", out)

    def test_empty_table_fails(self) -> None:
        self.write("docs/decisions/fix-12.md", HEADER)
        self.assertIn("has no row", self.run_check()[1])

    def test_bad_date_and_short_row_fail(self) -> None:
        self.write("docs/decisions/fix-12.md", HEADER + "| 2026-13-01 | a | b | c | d |\n| 2026-02-01 | a |\n")
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("does not start with a date", out)
        self.assertIn("2 cells", out)


class LookupTest(RecordsCase):
    def test_list_sorts_by_date_and_greps(self) -> None:
        self.write("docs/decisions/002-b.md", HEADER + "| 2025-12-31 | 002-b | D-0: early | x | y |\n")
        code, out = self.run_check("--list")
        self.assertEqual(code, 0)
        lines = out.splitlines()
        self.assertTrue(lines[0].startswith("docs/decisions/002-b.md | "), lines)
        self.assertTrue(lines[1].startswith("docs/log.md | "), lines)
        code, out = self.run_check("--list", "--grep", "EARLY")
        self.assertEqual(len(out.splitlines()), 1)
        self.assertEqual(self.run_check("--list", "--grep", "(")[0], 2)


class UnsetKeyTest(RecordsCase):
    def test_an_unset_key_prints_one_line_and_passes(self) -> None:
        for profile in ({"integrationRef": "base", "decisionRecords": {}}, {}):
            self.set_profile(profile)
            for args in ((), ("--list",)):
                code, out = self.run_check(*args)
                self.assertEqual(code, 0, out)
                self.assertEqual(out.splitlines(), ["decision-records: decisionRecords is unset in the binding; "
                                                    "no decision records to check or list"])

    def test_an_unset_integration_ref_skips_the_log_check_but_not_the_fragments(self) -> None:
        self.set_profile({"integrationRef": "", "decisionRecords": SECTION})
        self.write("docs/log.md", LOG + "| 2026-02-01 | 002-b | D-1: late | x | y |\n")
        code, out = self.run_check()
        self.assertEqual(code, 0, out)
        self.assertIn("log rows not checked: integrationRef unset and no --base", out)
        self.assertIn("added after the freeze", self.run_check("--base", "base")[1])
        self.write("docs/decisions/Notes.md", HEADER + "| 2026-02-01 | a | b | c | d |\n")
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("name does not match", out)

    def test_a_wrong_type_is_unusable_and_a_missing_profile_is_unset(self) -> None:
        self.set_profile({"decisionRecords": ["docs/log.md"]})
        self.assertEqual(self.run_check()[0], 2)
        os.remove(self.profile)
        self.assertEqual(self.run_check(), (0, "decision-records: no .claude/quality-profile.json; run python3 scripts/forge/quality_profile.py init\n"))


class ProfileTest(unittest.TestCase):
    def test_valid_section(self) -> None:
        repo = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, repo)
        os.makedirs(os.path.join(repo, "docs"))
        open(os.path.join(repo, "docs", "log.md"), "w").close()
        self.assertEqual(quality_profile.validate({"decisionRecords": SECTION}, repo=repo), [])

    def test_bad_section(self) -> None:
        bad = {**SECTION, "frozenOn": "soon", "fragmentName": "(", "extra": 1, "log": "docs/none.md"}
        problems = quality_profile.validate({"decisionRecords": bad}, repo=tempfile.gettempdir())
        for text in ("frozenOn", "fragmentName", "unknown key: extra", "does not exist"):
            self.assertTrue(any(text in p for p in problems), (text, problems))


if __name__ == "__main__":
    unittest.main()
