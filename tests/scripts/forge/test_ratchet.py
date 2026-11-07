#!/usr/bin/env python3
"""Tests for scripts/forge/ratchet.py (stdlib unittest; Python 3.9+).

Each test builds a throwaway repository root with its own `.claude/quality-profile.json`; the ratchet commands are tiny
`cat` calls reading a counter file, so the metric is controlled by the test. All names are invented.

Run: python3 -m unittest discover -s tests/scripts/forge -v
"""
from __future__ import annotations

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
import ratchet  # noqa: E402
import quality_profile  # noqa: E402


class RatchetCase(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.repo)
        os.makedirs(os.path.join(self.repo, ".claude"))
        self.profile = os.path.join(self.repo, ".claude", "quality-profile.json")
        self.set_profile([{"name": "alpha", "countCommand": "cat alpha.count"}])
        self.counter("alpha", 10)

    def set_profile(self, ratchets: list[dict]) -> None:
        with open(self.profile, "w", encoding="utf-8") as handle:
            json.dump({"baselineFile": ".quality/baseline.json", "ratchets": ratchets}, handle)

    def counter(self, name: str, value: int) -> None:
        with open(os.path.join(self.repo, f"{name}.count"), "w", encoding="utf-8") as handle:
            handle.write(f"noise line\n{value}\n")

    def baselines(self) -> dict:
        with open(os.path.join(self.repo, ".quality", "baseline.json"), encoding="utf-8") as handle:
            return json.load(handle)["baselines"]

    def run_ratchet(self, mode: str, *names: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = ratchet.run(mode, list(names), self.profile)
        return code, out.getvalue(), err.getvalue()


class CheckTests(RatchetCase):
    def test_missing_baseline_fails_and_names_the_fix(self) -> None:
        code, out, _ = self.run_ratchet("check")
        self.assertEqual(code, 1)
        self.assertIn("MISSING", out)

    def test_update_sets_a_missing_baseline_then_check_passes(self) -> None:
        self.assertEqual(self.run_ratchet("update")[0], 0)
        self.assertEqual(self.baselines(), {"alpha": 10})
        code, out, _ = self.run_ratchet("check")
        self.assertEqual(code, 0)
        self.assertIn("alpha=10 (baseline 10, delta 0) ok", out)

    def test_growth_fails(self) -> None:
        self.run_ratchet("update")
        self.counter("alpha", 11)
        code, out, _ = self.run_ratchet("check")
        self.assertEqual(code, 1)
        self.assertIn("GREW", out)

    def test_a_drop_passes_and_asks_for_the_new_baseline(self) -> None:
        self.run_ratchet("update")
        self.counter("alpha", 7)
        code, out, _ = self.run_ratchet("check")
        self.assertEqual(code, 0)
        self.assertIn("LOWER", out)
        self.assertEqual(self.baselines(), {"alpha": 10})

    def test_update_lowers_but_never_raises(self) -> None:
        self.run_ratchet("update")
        self.counter("alpha", 7)
        self.assertEqual(self.run_ratchet("update")[0], 0)
        self.assertEqual(self.baselines(), {"alpha": 7})
        self.counter("alpha", 9)
        code, _, _ = self.run_ratchet("update")
        self.assertEqual(code, 1)
        self.assertEqual(self.baselines(), {"alpha": 7})

    def test_update_writes_what_it_prints_when_another_ratchet_grew(self) -> None:
        self.set_profile([
            {"name": "alpha", "countCommand": "cat alpha.count"},
            {"name": "beta", "countCommand": "cat beta.count"},
        ])
        self.counter("beta", 5)
        self.run_ratchet("update")
        self.counter("alpha", 7)
        self.counter("beta", 6)
        code, out, _ = self.run_ratchet("update")
        self.assertEqual(code, 1)
        self.assertIn("alpha=7 (baseline 10 -> 7) LOWERED", out)
        self.assertIn("beta=6 (baseline 5, delta +1) GREW", out)
        self.assertEqual(self.baselines(), {"alpha": 7, "beta": 5})

    def test_a_failing_command_fails_the_check(self) -> None:
        self.set_profile([{"name": "alpha", "countCommand": "exit 3"}])
        code, out, _ = self.run_ratchet("check")
        self.assertEqual(code, 1)
        self.assertIn("alpha=ERROR", out)

    def test_a_command_without_an_integer_fails(self) -> None:
        self.set_profile([{"name": "alpha", "countCommand": "echo not-a-number"}])
        self.assertEqual(self.run_ratchet("check")[0], 1)

    def test_selecting_one_ratchet_leaves_the_others_alone(self) -> None:
        self.set_profile([
            {"name": "alpha", "countCommand": "cat alpha.count"},
            {"name": "beta", "countCommand": "cat beta.count"},
        ])
        self.counter("beta", 5)
        self.run_ratchet("update")
        self.counter("beta", 6)
        self.assertEqual(self.run_ratchet("check", "alpha")[0], 0)
        self.assertEqual(self.run_ratchet("check", "beta")[0], 1)

    def test_an_unknown_name_is_unusable(self) -> None:
        self.assertEqual(self.run_ratchet("check", "nope")[0], 2)

    def test_unset_ratchets_print_one_line_and_exit_0_in_every_mode(self) -> None:
        # The init-only binding (`ratchets` and `baselineFile` empty) and a binding without the key are the manual form.
        for binding in ({"baselineFile": "", "ratchets": []}, {}):
            with open(self.profile, "w", encoding="utf-8") as handle:
                json.dump(binding, handle)
            for mode in ("check", "update", "report", "copies"):
                with self.subTest(binding=binding, mode=mode):
                    out, err = io.StringIO(), io.StringIO()
                    with redirect_stdout(out), redirect_stderr(err):
                        if mode == "report":
                            code = ratchet.report([], self.profile, None, 5)
                        elif mode == "copies":
                            code = ratchet.copies([], self.profile, ["src/a.ts"], 2, None, False)
                        else:
                            code = ratchet.run(mode, [], self.profile)
                    self.assertEqual((code, out.getvalue().splitlines(), err.getvalue()), (0, [ratchet.UNSET], ""))
            self.assertFalse(os.path.exists(os.path.join(self.repo, ".quality")))

    def test_an_invalid_binding_exits_2_without_a_traceback(self) -> None:
        # A ratchet entry without `name` used to raise KeyError; the binding is validated first.
        self.set_profile([{"countCommand": "cat alpha.count"}])
        for mode in ("check", "update"):
            code, _, err = self.run_ratchet(mode)
            self.assertEqual(code, 2)
            self.assertIn("ratchets[0].name", err)
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()) as err:
            self.assertEqual(ratchet.report([], self.profile, None, 5), 2)
            self.assertEqual(ratchet.copies([], self.profile, ["a"], 2, None, False), 2)

    def test_a_corrupt_baseline_file_is_unusable(self) -> None:
        os.makedirs(os.path.join(self.repo, ".quality"))
        with open(os.path.join(self.repo, ".quality", "baseline.json"), "w", encoding="utf-8") as handle:
            handle.write('{"baselines": {"alpha": "ten"}}')
        self.assertEqual(self.run_ratchet("check")[0], 2)


class ReportTests(RatchetCase):
    """`report`: the Structure measurements of an audit, with the trend against the previous audit."""

    def run_report(self, *names: str, previous: str | None = None, top: int = 20) -> tuple[int, str]:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = ratchet.report(list(names), self.profile, previous, top)
        return code, out.getvalue()

    def previous_report(self, rows: str) -> str:
        path = os.path.join(self.repo, "previous-audit.md")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("# Audit\n\n## Structure\n\n" + ratchet.TABLE_HEADER + "\n|---|---:|---:|---:|---|\n" + rows
                         + "\n## Other\n\n| Ratchet | Count |\n| alpha | 999 |\n")
        return path

    def test_first_measurement_without_a_previous_audit(self) -> None:
        self.run_ratchet("update")
        code, out = self.run_report()
        self.assertEqual(code, 0)
        self.assertIn("| alpha | 10 | 10 | - | first measurement |", out)

    def test_trend_against_the_previous_audit_ignores_other_sections(self) -> None:
        self.set_profile([
            {"name": "alpha", "countCommand": "cat alpha.count"},
            {"name": "beta", "countCommand": "cat beta.count"},
            {"name": "gamma", "countCommand": "cat gamma.count"},
            {"name": "delta", "countCommand": "cat delta.count"},
        ])
        for name, value in (("beta", 4), ("gamma", 0), ("delta", 3)):
            self.counter(name, value)
        previous = self.previous_report(
            "| alpha | 8 | 8 | - | first measurement |\n| beta | 6 | 6 | - | x |\n| gamma | 2 | 2 | - | x |\n"
            "| `delta` | 3 | 3 | - | x |\n")
        code, out = self.run_report(previous=previous)
        self.assertEqual(code, 0)
        self.assertIn("| alpha | 10 | - | 8 | grown (+2) |", out)
        self.assertIn("| beta | 4 | - | 6 | shrinking (-2) |", out)
        self.assertIn("| gamma | 0 | - | 2 | fixed (-2) |", out)
        self.assertIn("| delta | 3 | - | 3 | unchanged |", out)

    def test_locations_are_capped_and_counted(self) -> None:
        with open(os.path.join(self.repo, "where.txt"), "w", encoding="utf-8") as handle:
            handle.write("9 a.ts\n\n5 b.ts\n1 c.ts\n")
        self.set_profile([{"name": "alpha", "countCommand": "cat alpha.count", "locationsCommand": "cat where.txt"}])
        code, out = self.run_report(top=2)
        self.assertEqual(code, 0)
        self.assertIn("Locations of alpha (top 2 of 3):\n- 9 a.ts\n- 5 b.ts", out)
        self.assertNotIn("c.ts", out)

    def test_a_failing_command_is_reported_and_fails(self) -> None:
        self.set_profile([{"name": "alpha", "countCommand": "cat alpha.count", "locationsCommand": "exit 4"}])
        code, out = self.run_report()
        self.assertEqual(code, 1)
        self.assertIn("Locations of alpha: ERROR", out)
        self.set_profile([{"name": "alpha", "countCommand": "exit 3"}])
        self.assertEqual(self.run_report()[0], 1)

    def test_unknown_name_is_unusable(self) -> None:
        self.assertEqual(self.run_report("nope")[0], 2)

    def test_previous_counts_reads_only_the_structure_table(self) -> None:
        text = "## Structure\n\nprose 12\n\n| Ratchet | Count |\n|---|---:|\n| a | 3 |\n| b | ERROR |\n\n## Next\n| a | 9 |\n"
        self.assertEqual(ratchet.previous_counts(text), {"a": 3})
        self.assertEqual(ratchet.previous_counts("# no structure here\n"), {})


class ProfileTests(unittest.TestCase):
    """The ratchet entries of the binding, as quality_profile validates them."""

    def test_ratchets_need_a_baseline_file_and_unique_names(self) -> None:
        entry = {"name": "a", "countCommand": "x"}
        self.assertEqual(quality_profile._validate_ratchets({"ratchets": [entry]}), ["baselineFile: required by ratchets"])
        found = quality_profile._validate_ratchets({"baselineFile": "b.json", "ratchets": [entry, dict(entry), 3]})
        self.assertIn("ratchets: duplicate name: a", found)
        self.assertIn("ratchets[2]: expected object", found)

    def test_locations_command_is_optional_but_never_empty(self) -> None:
        base = {"baselineFile": "b.json"}
        ok = {**base, "ratchets": [{"name": "a", "countCommand": "x", "locationsCommand": "y"}]}
        self.assertEqual(quality_profile._validate_ratchets(ok), [])
        empty = {**base, "ratchets": [{"name": "a", "countCommand": "x", "locationsCommand": ""}]}
        self.assertEqual(quality_profile._validate_ratchets(empty),
                         ["ratchets[0].locationsCommand: expected non-empty str"])

    def test_semantic_clones_section_is_validated(self) -> None:
        repo = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, repo)
        os.makedirs(os.path.join(repo, "src"))
        good = {"enabled": False, "paths": ["src"], "scope": "same", "model": "m", "ignore": ["**/x"], "threshold": 0.5}
        self.assertEqual(quality_profile._validate_semantic_clones({"semanticClones": good}, repo), [])
        bad = {"enabled": "no", "paths": ["no/such/dir"], "scope": "both", "model": "m", "threshold": 1.5, "extra": 1}
        found = quality_profile._validate_semantic_clones({"semanticClones": bad}, repo)
        self.assertIn("semanticClones.enabled: expected bool", found)
        self.assertIn("semanticClones.paths: no/such/dir does not exist", found)
        self.assertIn("semanticClones.scope: must be one of all, same, cross", found)
        self.assertIn("semanticClones.threshold: must be in (0, 1]", found)
        self.assertIn("semanticClones: unknown key: extra", found)
        self.assertEqual(len(quality_profile._validate_semantic_clones({"semanticClones": {}}, repo)), 4)

    def test_the_redefinitions_entry_is_validated(self) -> None:
        base = {"baselineFile": "b.json"}
        good = {**base, "ratchets": [{"name": "a", "countCommand": "x",
                                      "redefinitions": {"files": ["db/*.sql"], "definition": "create (\\w+)"}}]}
        self.assertEqual(quality_profile._validate_ratchets(good), [])
        bad = {**base, "ratchets": [{"name": "a", "countCommand": "x",
                                     "redefinitions": {"files": [], "definition": "create \\w+", "extra": 1}}]}
        found = quality_profile._validate_ratchets(bad)
        self.assertIn("ratchets[0].redefinitions.files: expected non-empty list", found)
        self.assertIn("ratchets[0].redefinitions.definition: needs exactly one capture group (the object name)", found)
        self.assertIn("ratchets[0].redefinitions: unknown key: extra", found)


class CopyGroupTests(unittest.TestCase):
    """`ratchet.py copies`, the third-copy trigger: copy groups that have a copy in the given files."""

    # The `groupsCommand` output shape: `<copies> <lines> <file>:<start>-<end> ...`, one line per copy group.
    GROUPS = [
        "3 11 src/a.ts:10-22 src/b.ts:1-11 src/c.ts:5-15",
        "2 9 src/d.ts:1-9 src/e.ts:1-9",
        "2 9 src/f.ts:1-9 src/g.ts:1-9",
    ]

    def test_parse_group_reads_the_groups_command_shape(self) -> None:
        self.assertEqual(ratchet.parse_group(self.GROUPS[1]), (2, 9, [("src/d.ts", 1, 9), ("src/e.ts", 1, 9)]))
        self.assertIsNone(ratchet.parse_group("copies: none"))
        self.assertIsNone(ratchet.parse_group("2 9 src/d.ts"))

    def test_copies_lists_groups_in_the_given_files_and_the_added_ones(self) -> None:
        repo = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, repo)
        git = lambda *a: subprocess.run(["git", "-C", repo, *a], check=True, capture_output=True)  # noqa: E731
        git("init", "-q")
        git("config", "user.email", "test@example.invalid")
        git("config", "user.name", "test")
        os.makedirs(os.path.join(repo, ".claude"))
        os.makedirs(os.path.join(repo, "src"))
        for name in ("a", "b", "d"):
            with open(os.path.join(repo, "src", f"{name}.ts"), "w", encoding="utf-8") as handle:
                handle.write("".join(f"line {n}\n" for n in range(30)))
        with open(os.path.join(repo, "groups.txt"), "w", encoding="utf-8") as handle:
            handle.write("\n".join(self.GROUPS) + "\n")
        profile = os.path.join(repo, ".claude", "quality-profile.json")
        with open(profile, "w", encoding="utf-8") as handle:
            json.dump({"baselineFile": "b.json", "ratchets": [
                {"name": "dup", "countCommand": "echo 1", "groupsCommand": "cat groups.txt"}]}, handle)
        git("add", "-A")
        git("-c", "commit.gpgsign=false", "commit", "-q", "-m", "base")

        def copies(*args: str) -> tuple[int, str]:
            out = io.StringIO()
            with redirect_stdout(out), redirect_stderr(io.StringIO()):
                code = ratchet.main(["copies", "--profile", profile, *args])
            return code, out.getvalue()

        code, out = copies("--files", "src/b.ts", "--min-copies", "3", "--fail")
        self.assertEqual(code, 1)
        self.assertIn("dup copies=3 lines=11 src/a.ts:10-22 src/b.ts:1-11 src/c.ts:5-15", out)
        code, out = copies("--files", "src/d.ts", "--min-copies", "3", "--fail")
        self.assertEqual(code, 0)
        self.assertIn("copies: 0 group(s) with >= 3 copies in the 1 given file(s)", out)
        self.assertIn("dup copies=2", copies("--files", "src/d.ts")[1])
        # nothing added since HEAD in a.ts: the group is old; an edit inside the copied lines makes it an added copy
        code, out = copies("--files", "src/a.ts", "--min-copies", "3", "--added-since", "HEAD", "--fail")
        self.assertEqual(code, 0, out)
        with open(os.path.join(repo, "src", "a.ts"), "a", encoding="utf-8") as handle:
            handle.write("tail\n")
        self.assertEqual(copies("--files", "src/a.ts", "--min-copies", "3", "--added-since", "HEAD", "--fail")[0], 0)
        with open(os.path.join(repo, "src", "a.ts"), encoding="utf-8") as handle:
            lines = handle.read().splitlines()
        lines[14] = "changed"
        with open(os.path.join(repo, "src", "a.ts"), "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
        code, out = copies("--files", "src/a.ts", "--min-copies", "3", "--added-since", "HEAD", "--fail")
        self.assertEqual(code, 1, out)
        self.assertIn("dup copies=3 lines=11 added src/a.ts:10-22", out)

    def test_copies_needs_files_and_a_groups_command(self) -> None:
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            ratchet.main(["copies"])
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            ratchet.main(["check", "--files", "x"])

    def test_groups_command_is_optional_but_never_empty(self) -> None:
        entry = {"name": "dup", "countCommand": "echo 1", "groupsCommand": ""}
        found = quality_profile.validate({"baselineFile": "b.json", "ratchets": [entry]})
        self.assertIn("ratchets[0].groupsCommand: expected non-empty str", found)


if __name__ == "__main__":
    unittest.main()
