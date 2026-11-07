#!/usr/bin/env python3
"""Tests for scripts/forge/wave-preflight.py (stdlib unittest; Python 3.9+): the pre-wave tree check.

A throwaway git repository stands in for the worktree; each case leaves one kind of leftover and runs the script.
Wrapper mode uses a second repository nested in the first. All names are invented.

Run: python3 -m unittest discover -s tests/scripts/forge -p 'test_wave_preflight.py' -v
"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SCRIPTS = os.path.join(REPO, "scripts", "forge")
SCRIPT = os.path.join(SCRIPTS, "wave-preflight.py")

GIT_ENV = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.test",
               GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.test")


def git(root, *args):
    return subprocess.run(["git", "-C", root, *args], check=True, capture_output=True, text=True,
                          env=GIT_ENV).stdout


def write(root, rel, text):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


def init_repo(root):
    git(root, "init", "-q", "-b", "main")
    write(root, ".gitignore", "ignored/\n")
    write(root, "src/a.txt", "one\n")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "base")
    return git(root, "rev-parse", "HEAD").strip()


def load_module():
    sys.path.insert(0, SCRIPTS)
    spec = importlib.util.spec_from_file_location("wave_preflight", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Preflight(unittest.TestCase):
    def setUp(self):
        self.root = os.path.realpath(tempfile.mkdtemp(prefix="wave-preflight-"))
        self.addCleanup(shutil.rmtree, self.root, True)
        self.head = init_repo(self.root)

    def run_check(self, *args, tree=None):
        return subprocess.run([sys.executable, SCRIPT, tree or self.root, *args], capture_output=True, text=True)

    def assertOk(self, result):
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertEqual(result.stdout.strip().splitlines()[-1], "ok")

    def assertProblem(self, result, *fragments):
        self.assertEqual(result.returncode, 1, result.stderr + result.stdout)
        for fragment in fragments:
            self.assertIn(fragment, result.stdout)

    def test_clean_tree_is_ok(self):
        self.assertOk(self.run_check())

    def test_expected_head_forms(self):
        self.assertOk(self.run_check(self.head))
        self.assertOk(self.run_check(self.head[:8]))
        self.assertOk(self.run_check("HEAD"))

    def test_modified_tracked_file(self):
        write(self.root, "src/a.txt", "two\n")
        self.assertProblem(self.run_check(), "tree not clean", "src/a.txt")

    def test_staged_change_counts(self):
        write(self.root, "src/a.txt", "two\n")
        git(self.root, "add", "src/a.txt")
        self.assertProblem(self.run_check(), "src/a.txt")

    def test_untracked_file_in_a_new_directory_is_listed(self):
        write(self.root, "newdir/deep/b.txt", "x\n")
        self.assertProblem(self.run_check(), "newdir/deep/b.txt")

    def test_ignored_file_is_not_a_problem(self):
        write(self.root, "ignored/c.txt", "x\n")
        self.assertOk(self.run_check())

    def test_many_paths_are_truncated(self):
        for index in range(12):
            write(self.root, f"junk/f{index}.txt", "x\n")
        self.assertProblem(self.run_check(), "12 path(s)", "; ...")

    def test_allow_untracked_file_and_directory(self):
        write(self.root, "notes/one.txt", "x\n")
        write(self.root, "scratch.txt", "x\n")
        self.assertOk(self.run_check("--allow-untracked", "notes", "--allow-untracked", "scratch.txt"))
        self.assertOk(self.run_check("--allow-untracked", "notes/", "--allow-untracked", "scratch.txt"))
        self.assertProblem(self.run_check("--allow-untracked", "notes"), "scratch.txt")

    def test_allow_untracked_does_not_excuse_a_tracked_change(self):
        write(self.root, "src/a.txt", "two\n")
        self.assertProblem(self.run_check("--allow-untracked", "src"), "src/a.txt")

    def test_allow_untracked_matches_whole_path_components(self):
        write(self.root, "notes2/one.txt", "x\n")
        self.assertProblem(self.run_check("--allow-untracked", "notes"), "notes2/one.txt")

    def test_wip_marker_is_one_line_of_its_own(self):
        write(self.root, ".claude/wip.md", "task 1\n")
        result = self.run_check()
        self.assertProblem(result, ".claude/wip.md exists")
        self.assertNotIn("tree not clean", result.stdout)

    def test_head_mismatch(self):
        write(self.root, "src/b.txt", "x\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "next")
        self.assertProblem(self.run_check(self.head), "HEAD is", "previous runner reported")

    def test_unresolvable_head_is_usage_error(self):
        result = self.run_check("no-such-rev")
        self.assertEqual(result.returncode, 2)
        self.assertIn("does not resolve", result.stderr)

    def test_merge_in_progress(self):
        git(self.root, "checkout", "-q", "-b", "other")
        write(self.root, "src/a.txt", "other\n")
        git(self.root, "commit", "-qam", "other")
        git(self.root, "checkout", "-q", "main")
        write(self.root, "src/a.txt", "main\n")
        git(self.root, "commit", "-qam", "main")
        subprocess.run(["git", "-C", self.root, "merge", "other"], capture_output=True, text=True, env=GIT_ENV)
        self.assertProblem(self.run_check(), "git operation in progress: merge")

    def test_index_lock(self):
        write(self.root, ".git/index.lock", "")
        self.assertProblem(self.run_check(), "index.lock")

    def test_linked_worktree_is_checked_in_its_own_state(self):
        other = self.root + "-wt"
        self.addCleanup(shutil.rmtree, other, True)
        git(self.root, "worktree", "add", "-q", other, "-b", "wave")
        self.assertOk(self.run_check(tree=other))
        write(other, "src/a.txt", "dirty\n")
        self.assertProblem(self.run_check(tree=other), "src/a.txt")
        self.assertOk(self.run_check())

    def test_not_a_git_repo_and_bad_usage(self):
        plain = tempfile.mkdtemp(prefix="wave-preflight-plain-")
        self.addCleanup(shutil.rmtree, plain, True)
        self.assertEqual(self.run_check(tree=plain).returncode, 2)
        self.assertEqual(self.run_check(tree=os.path.join(plain, "missing")).returncode, 2)
        bare = subprocess.run([sys.executable, SCRIPT], capture_output=True, text=True)
        self.assertEqual(bare.returncode, 2)
        flag = self.run_check("--no-such-flag")
        self.assertEqual(flag.returncode, 2)


class WrapperMode(unittest.TestCase):
    def setUp(self):
        self.root = os.path.realpath(tempfile.mkdtemp(prefix="wave-preflight-wrap-"))
        self.addCleanup(shutil.rmtree, self.root, True)
        self.src = os.path.join(self.root, "app")
        os.makedirs(self.src)
        init_repo(self.src)
        write(self.root, ".gitignore", "app/\n")
        write(self.root, ".claude/project-config.json", json.dumps({"SOURCE_ROOT": "app"}))
        write(self.root, "README.md", "wrapper\n")
        git(self.root, "init", "-q", "-b", "main")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "base")

    def run_check(self, *args):
        return subprocess.run([sys.executable, SCRIPT, self.root, *args], capture_output=True, text=True)

    def test_clean_wrapper_and_source_is_ok(self):
        result = self.run_check()
        self.assertEqual((result.returncode, result.stdout.strip().splitlines()[-1]), (0, "ok"), result.stderr)

    def test_dirty_source_repo_is_reported_with_its_label(self):
        write(self.src, "src/a.txt", "two\n")
        result = self.run_check()
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("source repo: tree not clean", result.stdout)
        self.assertIn("src/a.txt", result.stdout)

    def test_source_repo_in_progress_and_wip(self):
        write(self.src, ".claude/wip.md", "x\n")
        write(self.src, ".git/index.lock", "")
        result = self.run_check()
        self.assertIn("source repo: .claude/wip.md exists", result.stdout)
        self.assertIn("source repo: git operation in progress: index.lock", result.stdout)

    def test_allow_untracked_applies_to_the_source_repo(self):
        write(self.src, "notes/n.txt", "x\n")
        result = self.run_check("--allow-untracked", "notes")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_source_root_in_the_same_repository_is_not_checked_twice(self):
        shutil.rmtree(os.path.join(self.src, ".git"))
        write(self.root, ".gitignore", "")
        write(self.root, "app/src/a.txt", "one\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "app")
        write(self.root, "app/src/a.txt", "two\n")
        result = self.run_check()
        self.assertEqual(result.stdout.count("tree not clean"), 1, result.stdout)

    def test_bad_project_config_is_usage_error(self):
        write(self.root, ".claude/project-config.json", "{not json")
        self.assertEqual(self.run_check().returncode, 2)


class StaleWaits(unittest.TestCase):
    """The advisory check for sleep and wait loops; `ps` and `lsof` are mocked, nothing is killed."""

    def setUp(self):
        self.tree = os.path.realpath(tempfile.mkdtemp(prefix="wave-preflight-stale-"))
        self.addCleanup(shutil.rmtree, self.tree, True)
        self.mod = load_module()

    def stale(self, processes, cwds, minutes=15):
        with mock.patch.object(self.mod, "list_processes", return_value=processes), \
                mock.patch.object(self.mod, "process_cwds",
                                  side_effect=lambda pids: {p: cwds[p] for p in pids if p in cwds}):
            return self.mod.stale_waits(self.tree, minutes)

    def test_etime_forms(self):
        parse = self.mod.parse_etime
        self.assertEqual(parse("00:05"), 5)
        self.assertEqual(parse("14:59"), 899)
        self.assertEqual(parse("1:02:03"), 3723)
        self.assertEqual(parse("5-02:00:00"), 5 * 86400 + 7200)
        self.assertEqual(parse("garbage"), -1)

    def test_old_sleep_in_the_tree_is_reported(self):
        lines = self.stale([(101, 1480, "sleep 600")], {101: self.tree})
        self.assertEqual(len(lines), 1)
        self.assertIn("stale wait: pid 101 age 24m cwd ", lines[0])

    def test_until_loop_in_a_subdirectory(self):
        loop = "/bin/zsh -c until [ -f /tmp/x ] && false; do sleep 5; done"
        lines = self.stale([(11331, 5 * 86400 + 3600, loop)], {11331: os.path.join(self.tree, "pkg")})
        self.assertEqual(len(lines), 1)
        self.assertIn("pid 11331 age 5d 1h", lines[0])

    def test_while_loop_is_reported(self):
        self.assertEqual(len(self.stale([(7, 7200, "bash -c while true; do sleep 30; done")], {7: self.tree})), 1)

    def test_young_sleep_is_not_reported(self):
        self.assertEqual(self.stale([(101, 899, "sleep 600")], {101: self.tree}), [])
        self.assertEqual(len(self.stale([(101, 899, "sleep 600")], {101: self.tree}, minutes=10)), 1)

    def test_other_directory_or_unknown_cwd_is_not_reported(self):
        self.assertEqual(self.stale([(101, 9999, "sleep 600")], {101: self.tree + "-other"}), [])
        self.assertEqual(self.stale([(101, 9999, "sleep 600")], {101: "/"}), [])
        self.assertEqual(self.stale([(101, 9999, "sleep 600")], {}), [])

    def test_commands_that_only_mention_sleep_are_not_waits(self):
        processes = [(1, 9999, "vim sleeping-notes.md"), (2, 9999, "node build.js --asleep"),
                     (3, 9999, "python3 sleepy.py 5")]
        self.assertEqual(self.stale(processes, {1: self.tree, 2: self.tree, 3: self.tree}), [])

    def test_ps_output_is_parsed(self):
        out = "  12 05:00 /usr/bin/sleep 600\n 345 1-00:00:01 zsh -c until x; do sleep 5; done\nbad line\n"
        with mock.patch.object(self.mod.subprocess, "run",
                               return_value=subprocess.CompletedProcess([], 0, stdout=out, stderr="")):
            self.assertEqual(self.mod.list_processes(), [(12, 300, "/usr/bin/sleep 600"),
                                                         (345, 86401, "zsh -c until x; do sleep 5; done")])

    def test_lsof_output_is_parsed(self):
        out = "p12\nfcwd\nn/work/a\np345\nfcwd\nn/work/b c\n"
        with mock.patch.object(self.mod.subprocess, "run",
                               return_value=subprocess.CompletedProcess([], 0, stdout=out, stderr="")):
            self.assertEqual(self.mod.process_cwds([12, 345]), {12: "/work/a", 345: "/work/b c"})
        self.assertEqual(self.mod.process_cwds([]), {})

    def test_missing_tools_give_no_warnings(self):
        with mock.patch.object(self.mod.subprocess, "run", side_effect=FileNotFoundError("ps")):
            self.assertEqual(self.mod.list_processes(), [])
            self.assertEqual(self.mod.process_cwds([1]), {})
            self.assertFalse(self.mod.ps_available())

    def run_main(self, *args):
        with mock.patch("sys.stdout") as stdout:
            code = self.mod.main([self.tree, *args])
        return code, "".join(call.args[0] for call in stdout.write.call_args_list)

    def test_warning_never_changes_the_exit_code(self):
        init_repo(self.tree)
        line = "stale wait: pid 5 age 1h 0m cwd /x: sleep 9"
        with mock.patch.object(self.mod, "ps_available", return_value=True), \
                mock.patch.object(self.mod, "stale_waits", return_value=[line]):
            code, text = self.run_main()
        self.assertEqual(code, 0)
        self.assertIn("warning: " + line, text)
        self.assertIn("ok", text)

    def test_missing_ps_is_one_skip_line_and_exit_unchanged(self):
        init_repo(self.tree)
        with mock.patch.object(self.mod, "ps_available", return_value=False):
            code, text = self.run_main()
        self.assertEqual(code, 0)
        self.assertEqual(text.count("ps is unavailable"), 1)


if __name__ == "__main__":
    unittest.main()
