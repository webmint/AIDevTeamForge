#!/usr/bin/env python3
"""Tests for the source-root contract of the harness scripts (wrapper projects; stdlib unittest; Python 3.9+).

A throwaway wrapper repository holds `.claude/` (the binding and `project-config.json` with `SOURCE_ROOT`), and a
nested git repository `app/` holds the product code. The scripts that inspect product code must run git in `app/`
and read product paths relative to it. All names are invented.

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
SCRIPTS = os.path.join(REPO, "scripts", "forge")
sys.path.insert(0, SCRIPTS)
import quality_profile  # noqa: E402

PATTERN = {"files": ["src/**/*.py"], "regex": r"^def ([a-z_]+)"}


def git(cwd: str, *args: str) -> str:
    return subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True, check=True).stdout


def init_repo(path: str) -> None:
    os.makedirs(path, exist_ok=True)
    git(path, "init", "-q")
    git(path, "config", "user.email", "fixture@example.test")
    git(path, "config", "user.name", "Fixture")


def commit(path: str, message: str) -> str:
    git(path, "add", "-A")
    git(path, "-c", "commit.gpgsign=false", "commit", "-q", "--allow-empty", "-m", message)
    return git(path, "rev-parse", "HEAD").strip()


class WrapperCase(unittest.TestCase):
    def setUp(self) -> None:
        self.wrapper = tempfile.mkdtemp(prefix="wrapper-")
        self.addCleanup(shutil.rmtree, self.wrapper)
        self.app = os.path.join(self.wrapper, "app")
        init_repo(self.wrapper)
        self.write(".gitignore", "app/\n")
        self.write(".claude/project-config.json", json.dumps({"SOURCE_ROOT": "app"}))
        commit(self.wrapper, "wrapper")
        git(self.wrapper, "branch", "-M", "main")
        init_repo(self.app)
        self.write("app/src/old.py", "def old_name():\n    pass\n")
        self.write("app/src/dup.py", "a = 1\nb = 2\n")
        self.base = commit(self.app, "base")
        git(self.app, "branch", "-M", "main")
        git(self.app, "checkout", "-q", "-b", "feature")
        self.write("app/src/old.py", "def old_name():\n    pass\n\ndef new_name():\n    pass\n")
        commit(self.app, "feat: feature")
        self.profile_path = os.path.join(self.wrapper, ".claude", "quality-profile.json")

    def write(self, rel: str, text: str) -> None:
        path = os.path.join(self.wrapper, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)

    def set_profile(self, data: dict) -> None:
        self.write(".claude/quality-profile.json", json.dumps(data))

    def run_script(self, name: str, *args: str, cwd: str | None = None) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, os.path.join(SCRIPTS, name), *args], capture_output=True, text=True,
                              cwd=cwd or self.wrapper)


class SourceRootTests(WrapperCase):
    def test_source_root_reads_source_root_and_defaults_to_the_project(self) -> None:
        self.assertEqual(quality_profile.source_root(self.wrapper), os.path.normpath(self.app))
        os.remove(os.path.join(self.wrapper, ".claude", "project-config.json"))
        self.assertEqual(quality_profile.source_root(self.wrapper), os.path.abspath(self.wrapper))
        self.write(".claude/project-config.json", json.dumps({"PROJECT_NAME": "x"}))
        self.assertEqual(quality_profile.source_root(self.wrapper), os.path.abspath(self.wrapper))

    def test_an_unusable_source_root_raises(self) -> None:
        for value in ("../outside", "missing-dir", 3):
            self.write(".claude/project-config.json", json.dumps({"SOURCE_ROOT": value}))
            with self.assertRaises(quality_profile.ProfileError):
                quality_profile.source_root(self.wrapper)

    def test_source_path_accepts_both_forms(self) -> None:
        self.assertEqual(quality_profile.source_path("app/src/old.py", self.wrapper), "src/old.py")
        self.assertEqual(quality_profile.source_path("src/old.py", self.wrapper), "src/old.py")
        self.assertEqual(quality_profile.source_path("app/", self.wrapper), ".")
        self.assertEqual(quality_profile.source_path(os.path.join(self.app, "src"), self.wrapper), "src")

    def test_hub_paths_are_validated_under_the_source_root(self) -> None:
        hubs = {"commitPattern": "^feat", "window": 2, "threshold": 1, "paths": ["src/"]}
        self.assertEqual(quality_profile.validate({"hubFiles": hubs}, repo=self.wrapper), [])
        hubs["paths"] = ["docs/"]
        self.assertTrue(quality_profile.validate({"hubFiles": hubs}, repo=self.wrapper))


class WrapperScriptTests(WrapperCase):
    def test_new_exports_diffs_the_source_repository(self) -> None:
        for files in (["src/**/*.py"], ["app/src/**/*.py"]):
            self.set_profile({"integrationRef": "main", "newExports": {"patterns": [dict(PATTERN, files=files)]}})
            for extra in (("--base", self.base), ()):
                done = self.run_script("new-exports.py", "--profile", self.profile_path, *extra)
                self.assertEqual(done.returncode, 0, done.stderr)
                self.assertIn("src/old.py:4: new_name", done.stdout)
                self.assertIn("new-exports=1", done.stdout)

    def test_new_exports_fails_loudly_on_a_revision_of_neither_repository(self) -> None:
        self.set_profile({"newExports": {"patterns": [PATTERN]}})
        done = self.run_script("new-exports.py", "--profile", self.profile_path, "--base", "no-such-rev")
        self.assertEqual(done.returncode, 2)
        self.assertIn("bad revision", done.stderr)

    def test_copies_reads_added_lines_in_the_source_repository(self) -> None:
        group = "echo '3 2 src/dup.py:1-2 src/x.py:1-2 src/y.py:1-2'"
        self.set_profile({"baselineFile": ".claude/b.json",
                          "ratchets": [{"name": "dup", "countCommand": "echo 0", "groupsCommand": group}]})
        args = ("ratchet.py", "copies", "--profile", self.profile_path, "--added-since", "HEAD", "--files")
        # dup.py is committed in the source repository and untracked by the wrapper: nothing is added.
        for path in ("src/dup.py", "app/src/dup.py"):
            done = self.run_script(*args, path)
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertIn("copies: 0 group(s)", done.stdout)
        self.write("app/src/dup.py", "a = 1\nb = 3\n")
        self.assertIn("copies: 1 group(s)", self.run_script(*args, "src/dup.py").stdout)
        missing = self.run_script(*args, "src/x.py")
        self.assertEqual(missing.returncode, 2)
        self.assertIn("not in the source repository", missing.stderr)

    def test_matches_counts_the_source_repository_and_fails_on_a_missing_path(self) -> None:
        for path in ("src/", "app/src/"):
            done = self.run_script("count-tools.py", "matches", "^def ", path)
            self.assertEqual((done.returncode, done.stdout), (0, "2\n"), done.stderr)
        done = self.run_script("count-tools.py", "matches", "^def ", "nowhere/")
        self.assertEqual(done.returncode, 2)
        self.assertIn("not under the source root", done.stderr)

    def test_hub_files_reads_the_source_history(self) -> None:
        self.set_profile({"integrationRef": "feature",
                          "hubFiles": {"commitPattern": "^feat", "window": 2, "threshold": 1, "paths": ["src/"]}})
        done = self.run_script("hub-files.py", "--profile", self.profile_path, "list")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("hub 1/1 src/old.py", done.stdout)
        done = self.run_script("hub-files.py", "--profile", self.profile_path, "check", "--files", "app/src/old.py")
        self.assertIn("hub 1/2 src/old.py", done.stdout)


if __name__ == "__main__":
    unittest.main()
