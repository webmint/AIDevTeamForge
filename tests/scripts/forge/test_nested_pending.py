#!/usr/bin/env python3
"""Tests for scripts/forge/nested-pending.py and `scripts/forge/wave-preflight.py --runner` (stdlib unittest; Python
3.9+): the conductor-side half of the nested-wait check (the runner-side half is the hook
`.claude/hooks/forge/nested-wait-guard.py`, tested in tests/hooks/test_nested_wait_guard.py).

Transcripts are synthetic JSONL with invented ids under a throwaway projects dir
(`<projects>/<project>/<session>/subagents/agent-<id>.jsonl`); the record builder `Rec` is the hook tests' one.

Run: python3 -m unittest discover -s tests/scripts/forge -p 'test_nested_pending.py' -v
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
NESTED_PENDING = os.path.join(SCRIPTS, "nested-pending.py")
PREFLIGHT = os.path.join(SCRIPTS, "wave-preflight.py")
HOOK_TESTS = os.path.join(REPO, "tests", "hooks", "test_nested_wait_guard.py")

GIT_ENV = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.test",
               GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.test")


def load_by_path(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_hook_tests = load_by_path("nested_wait_guard_tests", HOOK_TESTS)
Rec = _hook_tests.Rec
SECRET = _hook_tests.SECRET
write_jsonl = _hook_tests.write_jsonl
del _hook_tests  # keep its test classes out of this module's discovery


def git(root, *args):
    return subprocess.run(["git", "-C", root, *args], check=True, capture_output=True, text=True,
                          env=GIT_ENV).stdout


def write(root, rel, text):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


class NestedPendingCli(unittest.TestCase):
    """scripts/forge/nested-pending.py over a throwaway projects dir."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="nested-pending-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.projects = os.path.join(self.tmp, "projects")
        self.r = Rec()
        self.np = load_by_path("nested_pending", NESTED_PENDING)

    def agent_file(self, agent_id, records, session="sess-1"):
        path = os.path.join(self.projects, "proj-1", session, "subagents", f"agent-{agent_id}.jsonl")
        return write_jsonl(path, records)

    def cli(self, *args):
        env = {k: v for k, v in os.environ.items() if k != "CLAUDE_CONFIG_DIR"}
        return subprocess.run([sys.executable, NESTED_PENDING, *args, "--projects-dir", self.projects],
                              capture_output=True, text=True, env=env)

    def test_clean_runner_exits_0_and_counts_launches(self):
        self.agent_file("RUN1", self.r.agent("u1", "AG1") + [self.r.notify("AG1")] + self.r.shell("u2", "bsh1")
                        + [self.r.notify("bsh1")])
        result = self.cli("RUN1", "--no-recursive")
        self.assertEqual((result.returncode, result.stdout.strip()), (0, "ok: no pending nested work (2 launched)"))

    def test_pending_runner_exits_1_with_one_line_per_item_and_no_text(self):
        self.agent_file("RUN1", self.r.agent("u1", "AG1") + self.r.shell("u2", "bsh1"))
        result = self.cli("RUN1")
        self.assertEqual(result.returncode, 1, result.stderr)
        lines = result.stdout.strip().splitlines()
        self.assertEqual(len([line for line in lines if line.startswith("pending:")]), 2)
        self.assertIn("pending: agent AG1 (backend-engineer, launched ", result.stdout)
        self.assertIn("pending: shell bsh1 (Bash, launched ", result.stdout)
        self.assertNotIn(SECRET, result.stdout + result.stderr)

    def test_unresolvable_targets_exit_2(self):
        os.makedirs(self.projects)
        for target in ("NOPE", os.path.join(self.tmp, "missing.jsonl"), "x.jsonl"):
            with self.subTest(target=target):
                result = self.cli(target)
                self.assertEqual(result.returncode, 2)
                self.assertIn("nested-pending:", result.stderr)

    def test_transcript_path_is_accepted_as_the_target(self):
        path = self.agent_file("RUN1", self.r.agent("u1", "AG1"))
        self.assertEqual(self.cli(path).returncode, 1)

    def test_recursion_reports_a_nested_agents_pending_shell_via_its_parent(self):
        self.agent_file("RUN1", self.r.agent("u1", "CH1") + [self.r.notify("CH1")])
        self.agent_file("CH1", self.r.shell("u2", "bsh9"))
        result = self.cli("RUN1")
        self.assertEqual(result.returncode, 1)
        self.assertIn("pending: shell bsh9 (Bash, launched ", result.stdout)
        self.assertIn("via CH1", result.stdout)

    def test_no_recursive_skips_the_nested_agents(self):
        self.agent_file("RUN1", self.r.agent("u1", "CH1") + [self.r.notify("CH1")])
        self.agent_file("CH1", self.r.shell("u2", "bsh9"))
        result = self.cli("RUN1", "--no-recursive")
        self.assertEqual((result.returncode, result.stdout.strip()), (0, "ok: no pending nested work (1 launched)"))

    def test_grandchild_chain_is_labelled_with_the_path(self):
        self.agent_file("RUN1", self.r.agent("u1", "CH1") + [self.r.notify("CH1")])
        self.agent_file("CH1", self.r.agent("u2", "GC1") + [self.r.notify("GC1")])
        self.agent_file("GC1", self.r.shell("u3", "bsh7"))
        result = self.cli("RUN1")
        self.assertEqual(result.returncode, 1)
        self.assertIn("via CH1 > GC1", result.stdout)

    def test_agent_without_a_transcript_prints_unchecked_and_keeps_the_exit_code(self):
        self.agent_file("RUN1", self.r.agent("u1", "CH2") + [self.r.notify("CH2")])
        result = self.cli("RUN1")
        self.assertEqual(result.returncode, 0)
        self.assertIn("unchecked: agent CH2 (no transcript found)", result.stdout)
        self.agent_file("RUN2", self.r.agent("u1", "CH3") + [self.r.notify("CH3")] + self.r.shell("u2", "bsh1"))
        result = self.cli("RUN2")
        self.assertEqual(result.returncode, 1)
        self.assertIn("unchecked: agent CH3", result.stdout)

    def test_functions_resolve_and_inspect(self):
        path = self.agent_file("RUN1", self.r.agent("u1", "AG1"))
        self.assertEqual(self.np.resolve_target(path, self.projects), (path, "agent-RUN1.jsonl"))
        self.assertEqual(self.np.resolve_target("RUN1", self.projects), (path, "RUN1"))
        lines, launched, unchecked = self.np.inspect("RUN1", self.projects, recursive=False)
        self.assertEqual((len(lines), launched, unchecked), (1, 1, []))
        self.assertEqual(len(self.np.pending_for(path, self.projects)), 1)
        with self.assertRaises(self.np.Unresolvable):
            self.np.resolve_target("NOPE", self.projects)

    def test_the_newest_transcript_of_an_id_wins(self):
        old = self.agent_file("RUN1", self.r.agent("u1", "AG1"), session="sess-old")
        new = self.agent_file("RUN1", [self.r.use("b1", "Bash"), self.r.result("b1")], session="sess-new")
        os.utime(old, (1_000, 1_000))
        os.utime(new, (2_000, 2_000))
        self.assertEqual(self.np.find_agent_transcript("RUN1", self.projects), new)
        self.assertEqual(self.cli("RUN1").returncode, 0)

    def test_default_projects_dir_follows_the_config_dir_variable(self):
        with mock.patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": "/cfg"}):
            self.assertEqual(self.np.default_projects_dir(), os.path.join("/cfg", "projects"))

    def test_the_parser_is_the_hook_next_to_the_script(self):
        self.assertEqual(os.path.realpath(self.np.hook_path()),
                         os.path.realpath(os.path.join(REPO, ".claude", "hooks", "forge", "nested-wait-guard.py")))


class RunnerFlag(unittest.TestCase):
    """wave-preflight.py --runner: the conductor-side half of the same check."""

    def setUp(self):
        self.root = os.path.realpath(tempfile.mkdtemp(prefix="wave-preflight-runner-"))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        git(self.root, "init", "-q", "-b", "main")
        write(self.root, "src/a.txt", "one\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "base")
        self.config = self.root + "-cfg"
        self.addCleanup(shutil.rmtree, self.config, ignore_errors=True)
        self.r = Rec()

    def transcript(self, name, records):
        path = os.path.join(self.config, "projects", "proj-1", "sess-1", "subagents", f"agent-{name}.jsonl")
        return write_jsonl(path, records)

    def run_preflight(self, *runners):
        env = {**os.environ, "CLAUDE_PROJECT_DIR": self.root, "CLAUDE_CONFIG_DIR": self.config}
        args = [arg for runner in runners for arg in ("--runner", runner)]
        return subprocess.run([sys.executable, PREFLIGHT, self.root, *args], capture_output=True, text=True, env=env)

    @staticmethod
    def problem_lines(stdout):
        return [line for line in stdout.strip().splitlines() if not line.startswith("warning: ")]

    def test_runner_with_pending_nested_work_is_a_problem(self):
        path = self.transcript("RUN1", self.r.agent("u1", "AG1") + self.r.shell("u2", "bsh1"))
        for target in (path, "RUN1"):
            with self.subTest(target=target):
                result = self.run_preflight(target)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertIn(f"runner {target}: nested work still pending: agent AG1 (backend-engineer", result.stdout)
                self.assertIn("shell bsh1 (Bash", result.stdout)
                self.assertNotIn(SECRET, result.stdout + result.stderr)

    def test_clean_runner_is_ok(self):
        path = self.transcript("RUN1", self.r.agent("u1", "AG1") + [self.r.notify("AG1")])
        result = self.run_preflight(path)
        self.assertEqual((result.returncode, self.problem_lines(result.stdout)), (0, ["ok"]), result.stderr)

    def test_each_of_several_runners_is_checked(self):
        clean = self.transcript("RUN1", [self.r.use("b1", "Bash"), self.r.result("b1")])
        busy = self.transcript("RUN2", self.r.shell("u1", "bsh1"))
        result = self.run_preflight(clean, busy)
        self.assertEqual(result.returncode, 1)
        self.assertIn(f"runner {busy}:", result.stdout)
        self.assertNotIn(f"runner {clean}:", result.stdout)

    def test_unresolvable_runner_exits_2(self):
        result = self.run_preflight("NOPE")
        self.assertEqual(result.returncode, 2)
        self.assertIn("runner NOPE", result.stderr)

    def test_runner_problems_adds_to_the_tree_problems(self):
        write(self.root, "src/a.txt", "dirty\n")
        path = self.transcript("RUN1", self.r.shell("u1", "bsh1"))
        result = self.run_preflight(path)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(len(self.problem_lines(result.stdout)), 2, result.stdout)

    def test_no_runner_flag_changes_nothing(self):
        sys.path.insert(0, SCRIPTS)
        module = load_by_path("wave_preflight", PREFLIGHT)
        self.assertEqual(module.runner_problems([]), [])


if __name__ == "__main__":
    unittest.main()
