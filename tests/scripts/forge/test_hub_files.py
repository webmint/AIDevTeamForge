#!/usr/bin/env python3
"""Tests for scripts/forge/hub-files.py (stdlib unittest; Python 3.9+).

Each test builds a throwaway git repository with its own `.claude/quality-profile.json` and a few invented feature
commits, so nothing here reads this repository's history. All names are invented.

Run: python3 -m unittest discover -s tests/scripts/forge -v
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SCRIPT = os.path.join(REPO, "scripts", "forge", "hub-files.py")
HUBS = {"commitPattern": "^feat(\\(|:)", "window": 4, "threshold": 3, "paths": ["src/"], "ignore": ["src/gen/*"]}


class HubFilesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = tempfile.mkdtemp(prefix="hub-files-")
        self.addCleanup(shutil.rmtree, self.repo)
        self.git("init", "-q")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "user.name", "test")
        self.write(".claude/quality-profile.json",
                   json.dumps({"integrationRef": "main", "searchScopes": ["src/"], "hubFiles": HUBS}))
        self.write("src/app/root.ts", "init\n")
        self.commit("chore: profile")
        self.git("branch", "-M", "main")
        # Five feature commits: the oldest one falls outside the window of four.
        for n, files in enumerate((["src/app/root.ts"],
                                   ["src/app/root.ts", "src/a/a.ts", "src/gen/types.ts"],
                                   ["src/app/root.ts", "src/b/b.ts", "src/app/routes.ts", "src/gen/types.ts"],
                                   ["src/app/routes.ts", "src/c/c.ts", "src/gen/types.ts"],
                                   ["src/app/root.ts", "docs/x.md"])):
            for path in files:
                self.write(path, f"{n}\n")
            self.commit(f"feat(f{n}): feature {n}")
        self.write("src/app/routes.ts", "fix\n")
        self.commit("fix: not a feature commit")

    def git(self, *args: str) -> str:
        return subprocess.run(["git", "-C", self.repo, *args], check=True, capture_output=True, text=True).stdout

    def write(self, rel: str, text: str) -> None:
        path = os.path.join(self.repo, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)

    def commit(self, message: str) -> None:
        self.git("add", "-A")
        self.git("-c", "commit.gpgsign=false", "commit", "-q", "-m", message)

    def run_hubs(self, *args: str) -> subprocess.CompletedProcess:
        profile = os.path.join(self.repo, ".claude", "quality-profile.json")
        return subprocess.run([sys.executable, SCRIPT, "--profile", profile, *args], capture_output=True, text=True)

    def test_list_counts_only_the_window_of_feature_commits(self) -> None:
        result = self.run_hubs("list")
        self.assertEqual(result.returncode, 0, result.stderr)
        # root.ts: 3 of the newest 4 feature commits (the oldest is outside the window); routes.ts only 2;
        # src/gen is ignored although 3 commits edited it; docs/ is out of scope.
        self.assertEqual(result.stdout.splitlines(), [
            "hub 3/4 src/app/root.ts",
            "hub-files: 1 hub(s) (4 feature commit(s) on main, threshold 3)",
        ])

    def test_check_files_marks_hubs_and_new_hubs(self) -> None:
        result = self.run_hubs("check", "--files", "src/app/root.ts", "src/app/routes.ts", "src/a/a.ts",
                               "src/gen/types.ts")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines()[:2], ["hub 3/4 src/app/root.ts", "new-hub 3/4 src/app/routes.ts"])
        self.assertIn("1 hub(s), 1 new hub(s) among 4 file(s)", result.stdout)

    def test_check_base_reads_the_diff_and_fail_exits_one(self) -> None:
        self.git("switch", "-q", "-c", "spec/x")
        self.write("src/app/routes.ts", "spec\n")
        self.write("src/d/d.ts", "spec\n")
        self.commit("feat(x): wip")
        result = self.run_hubs("check", "--base", "main", "--fail")
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("new-hub 3/4 src/app/routes.ts", result.stdout)
        self.assertNotIn("src/d/d.ts", result.stdout.splitlines()[0])
        clean = self.run_hubs("check", "--files", "src/d/d.ts", "--fail")
        self.assertEqual(clean.returncode, 0, clean.stdout)

    def test_check_needs_exactly_one_of_files_and_base(self) -> None:
        self.assertEqual(self.run_hubs("check").returncode, 2)
        self.assertEqual(self.run_hubs("check", "--files", "src/a/a.ts", "--base", "main").returncode, 2)

    def test_an_unset_integration_ref_reads_head(self) -> None:
        self.write(".claude/quality-profile.json", json.dumps({"integrationRef": "", "hubFiles": HUBS}))
        result = self.run_hubs("list")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("4 feature commit(s) on HEAD", result.stdout)

    def test_unset_binding_says_so_on_one_line_and_exits_0(self) -> None:
        for profile in ({"integrationRef": "main", "hubFiles": {}}, {"integrationRef": "main"}):
            with self.subTest(profile=profile):
                self.write(".claude/quality-profile.json", json.dumps(profile))
                for args in (("list",), ("check", "--files", "src/app/root.ts", "--fail")):
                    result = self.run_hubs(*args)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stderr, "")
                    self.assertEqual(result.stdout.splitlines(),
                                     ["hub-files: hubFiles is unset in the quality profile; list the hubs by hand"])

    def test_a_missing_or_broken_binding_file_exits_2(self) -> None:
        os.remove(os.path.join(self.repo, ".claude", "quality-profile.json"))
        self.assertEqual(self.run_hubs("list").returncode, 2)
        self.write(".claude/quality-profile.json", "{not json")
        self.assertEqual(self.run_hubs("list").returncode, 2)

    def test_an_invalid_binding_is_an_error(self) -> None:
        self.write(".claude/quality-profile.json",
                   json.dumps({"integrationRef": "main", "hubFiles": {**HUBS, "threshold": 9}}))
        result = self.run_hubs("list")
        self.assertEqual(result.returncode, 2)
        self.assertIn("hubFiles.threshold: must be at least 1 and at most window", result.stderr)


if __name__ == "__main__":
    unittest.main()
