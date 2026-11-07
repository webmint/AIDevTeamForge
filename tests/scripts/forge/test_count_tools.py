#!/usr/bin/env python3
"""Tests for scripts/forge/count-tools.py (stdlib unittest; Python 3.9+).

The clone commands get hand-written jscpd-shaped reports; the redefinition files are tiny files in a throwaway root.
All names are invented.

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
from unittest import mock

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SCRIPTS = os.path.join(REPO, "scripts", "forge")
sys.path.insert(0, SCRIPTS)
import quality_profile  # noqa: E402

_spec = importlib.util.spec_from_file_location("count_tools", os.path.join(SCRIPTS, "count-tools.py"))
count_tools = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(count_tools)
_REAL_REDEFINITION_CONFIG = count_tools.redefinition_config


def write(root: str, rel: str, text: str) -> None:
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


def run_main(*argv: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = count_tools.main(list(argv))
    return code, out.getvalue(), err.getvalue()


class CountToolsTests(unittest.TestCase):
    def test_sum_leaves_ignores_booleans_and_strings(self) -> None:
        self.assertEqual(count_tools.sum_leaves({"a": {"count": 2}, "b": [1, True, "x", {"c": 4}]}), 7)

    def test_sum_under_key_counts_only_that_branch(self) -> None:
        data = {"f1": {"rule/a": {"count": 3}, "rule/b": {"count": 5}}, "f2": {"rule/a": {"count": 1}}}
        self.assertEqual(count_tools.sum_under_key(data, "rule/a"), 4)
        self.assertEqual(count_tools.sum_under_key(data, "rule/none"), 0)

    def test_walk_follows_a_dotted_path_and_rejects_a_missing_one(self) -> None:
        self.assertEqual(count_tools.walk({"a": {"b": 5}}, "a.b"), 5)
        with self.assertRaises(KeyError):
            count_tools.walk({"a": 1}, "a.b")

    def test_json_rows_sorts_by_the_first_field_and_marks_missing_fields(self) -> None:
        data = {"list": [{"n": 2, "f": {"name": "a"}}, {"n": 9, "f": {"name": "b"}}, {"n": 5}]}
        self.assertEqual(count_tools.json_rows(data, "list", ["n", "f.name"]), ["9 b", "5 ?", "2 a"])
        with self.assertRaises(TypeError):
            count_tools.json_rows({"list": {}}, "list", ["n"])

    def test_json_leaves_lists_integer_leaves_largest_first(self) -> None:
        data = {"f1": {"rule": {"count": 1}}, "f2": {"rule": {"count": 4}, "flag": True}}
        self.assertEqual(count_tools.json_leaves(data), [(4, "f2 :: rule :: count"), (1, "f1 :: rule :: count")])

    def test_matches_counts_lines_in_tracked_files_under_the_given_paths(self) -> None:
        repo = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, repo)
        for rel, text in {"in/a.txt": "x\nTODO\nTODO\n", "in/b.txt": "TODO\n", "out/c.txt": "TODO\n"}.items():
            write(repo, rel, text)
        write(repo, "in/untracked.txt", "TODO\n")
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
        subprocess.run(["git", "add", "in/a.txt", "in/b.txt", "out/c.txt"], cwd=repo, check=True)
        previous = os.getcwd()
        os.chdir(repo)
        try:
            self.assertEqual(count_tools.count_matches("TODO", ["in"]), 3)
        finally:
            os.chdir(previous)

    def test_matches_skips_links_and_submodules_and_reads_a_non_utf8_file(self) -> None:
        repo = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, repo)
        sub = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, sub)
        write(repo, "in/real/a.txt", "TODO\n")
        with open(os.path.join(repo, "in", "latin.txt"), "wb") as handle:
            handle.write(b"caf\xe9 TODO\nTODO\n")
        with open(os.path.join(repo, "in", "blob.bin"), "wb") as handle:
            handle.write(b"\x00TODO\n")
        os.symlink("real", os.path.join(repo, "in", "link"))
        os.symlink("real/a.txt", os.path.join(repo, "in", "alias.txt"))
        git = ["git", "-c", "user.email=t@example.invalid", "-c", "user.name=t", "-c", "commit.gpgsign=false",
               "-c", "protocol.file.allow=always"]
        subprocess.run(["git", "init", "-q"], cwd=sub, check=True)
        write(sub, "s.txt", "TODO\n")
        subprocess.run([*git, "add", "-A"], cwd=sub, check=True)
        subprocess.run([*git, "commit", "-q", "-m", "s"], cwd=sub, check=True)
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
        subprocess.run([*git, "submodule", "add", "-q", sub, "in/sub"], cwd=repo, check=True, capture_output=True)
        subprocess.run([*git, "add", "-A"], cwd=repo, check=True)
        previous = os.getcwd()
        os.chdir(repo)
        try:
            # a.txt once, latin.txt twice; the links, the submodule and the binary file carry no countable lines.
            self.assertEqual(count_tools.count_matches("TODO", ["in"]), 3)
        finally:
            os.chdir(previous)

    def test_the_json_commands_print_one_integer_and_bad_input_exits_2(self) -> None:
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root)
        write(root, "s.json", json.dumps({"a": {"n": 2}, "b": {"n": 3}}))
        path = os.path.join(root, "s.json")
        self.assertEqual(run_main("json-sum", path)[:2], (0, "5\n"))
        self.assertEqual(run_main("json-value", path, "b.n")[:2], (0, "3\n"))
        self.assertEqual(run_main("json-value", path, "b.missing")[0], 2)
        self.assertEqual(run_main("no-such-command", path)[0], 2)


class CloneRedefinitionTests(unittest.TestCase):
    """clone-lines / clone-rows: a later file that redefines an object is not a duplicate of the old body."""

    DEFINITION = r"(?i)^\s*create\s+(?:or\s+replace\s+)?(?:function|view)\s+([\w.\"]+)"
    BODY = "  select 1;\n  select 2;\n  select 3;\n"

    def setUp(self) -> None:
        self.repo = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.repo)
        self.write("db/m1.sql", "-- preamble\ncreate function app.total(x int)\n" + self.BODY
                   + "create function app.mirror_a()\n" + self.BODY)
        self.write("db/m2.sql", "create or replace function APP.\"total\"(x int)\n" + self.BODY)
        self.write("db/m3.sql", "create function app.mirror_b()\n" + self.BODY)
        self.write("src/a.ts", "x\n" * 10)
        self.redefs = count_tools.Redefinitions({"files": ["db/*.sql"], "definition": self.DEFINITION}, self.repo)

    def write(self, rel: str, text: str) -> None:
        write(self.repo, rel, text)

    @staticmethod
    def clone(lines: int, first: tuple[str, int, int], second: tuple[str, int, int]) -> dict:
        side = lambda f: {"name": f[0], "start": f[1], "end": f[2]}  # noqa: E731
        return {"lines": lines, "firstFile": side(first), "secondFile": side(second)}

    def report(self) -> dict:
        return {
            "statistics": {"total": {"duplicatedLines": 30}},
            "duplicates": [
                # m2 redefines app.total from m1: a redefinition (jscpd names files relative to the scanned dir).
                self.clone(4, ("m1.sql", 2, 5), ("m2.sql", 1, 4)),
                # two different objects with the same body: real duplication.
                self.clone(4, ("m1.sql", 6, 9), ("m3.sql", 1, 4)),
                # a clone that starts in the preamble: never a redefinition.
                self.clone(5, ("m1.sql", 1, 5), ("m2.sql", 1, 4)),
                # files outside the redefinition globs: counted.
                self.clone(8, ("src/a.ts", 1, 8), ("src/a.ts", 2, 9)),
            ],
        }

    def test_redefinitions_are_subtracted_and_real_duplicates_stay(self) -> None:
        self.assertEqual(count_tools.clone_lines(self.report(), self.redefs), 26)
        rows = count_tools.clone_rows(self.report(), self.redefs)
        self.assertEqual(len(rows), 3)
        self.assertNotIn("4 m1.sql 2 m2.sql 1", rows)
        self.assertIn("4 m1.sql 6 m3.sql 1", rows)

    def test_a_clone_spanning_two_objects_needs_the_same_objects_on_both_sides(self) -> None:
        spanning = {"statistics": {"total": {"duplicatedLines": 6}},
                    "duplicates": [self.clone(6, ("m1.sql", 3, 8), ("m2.sql", 2, 4))]}
        self.assertEqual(count_tools.clone_lines(spanning, self.redefs), 6)

    def test_without_a_redefinitions_entry_every_clone_counts(self) -> None:
        plain = count_tools.Redefinitions(None, self.repo)
        self.assertEqual(count_tools.clone_lines(self.report(), plain), 30)
        self.assertEqual(len(count_tools.clone_rows(self.report(), plain)), 4)
        self.assertEqual(count_tools.clone_lines(self.report(), count_tools.Redefinitions(None, self.repo, True)), 30)

    def test_the_config_is_read_from_the_named_ratchet(self) -> None:
        profile = os.path.join(self.repo, "profile.json")
        entry = {"files": ["db/*.sql"], "definition": self.DEFINITION}
        with open(profile, "w", encoding="utf-8") as handle:
            json.dump({"baselineFile": "b.json", "ratchets": [{"name": "dup", "countCommand": "x", "redefinitions": entry},
                                    {"name": "other", "countCommand": "y"}]}, handle)
        self.assertEqual(count_tools.redefinition_config("dup", profile), entry)
        self.assertIsNone(count_tools.redefinition_config("other", profile))
        with self.assertRaises(KeyError):
            count_tools.redefinition_config("missing", profile)

    def test_unset_ratchets_name_no_ratchet(self) -> None:
        # A clone command runs from a ratchet's command, so an unset `ratchets` key is an unusable input (exit 2).
        profile = os.path.join(self.repo, "profile.json")
        with open(profile, "w", encoding="utf-8") as handle:
            json.dump({"ratchets": [], "baselineFile": ""}, handle)
        with self.assertRaises(KeyError):
            count_tools.redefinition_config("dup", profile)
        report = os.path.join(self.repo, "report.json")
        with open(report, "w", encoding="utf-8") as handle:
            json.dump(self.report(), handle)
        with mock.patch.object(count_tools, "redefinition_config",
                               lambda name: _REAL_REDEFINITION_CONFIG(name, profile)):
            code, out, err = run_main("clone-lines", report, "dup")
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("no ratchet named dup", err)


class SupersededPairTests(unittest.TestCase):
    """--superseded: a pair wholly inside statements a later file redefines is not counted (opt-in, off by default)."""

    DEFINITION = CloneRedefinitionTests.DEFINITION
    BODY = "as $$\n  select 1;\n  select 2;\n$$;\n"  # four lines; the `;` inside the dollar quote ends nothing

    def setUp(self) -> None:
        self.repo = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.repo)

    def write(self, rel: str, text: str) -> None:
        write(self.repo, rel, text)

    def redefs(self, superseded: bool = True) -> "count_tools.Redefinitions":
        return count_tools.Redefinitions({"files": ["db/*.sql"], "definition": self.DEFINITION}, self.repo, superseded)

    @staticmethod
    def clone(first: tuple[str, int, int], second: tuple[str, int, int]) -> dict:
        return CloneRedefinitionTests.clone(first[2] - first[1] + 1, first, second)

    def skipped(self, clone: dict) -> bool:
        return self.redefs().skips(clone)

    def test_a_pair_of_two_superseded_statements_is_not_counted(self) -> None:
        # a and b are each redefined by m3, so both bodies are dead text.
        self.write("db/m1.sql", "create function app.a()\n" + self.BODY)
        self.write("db/m2.sql", "create function app.b()\n" + self.BODY)
        self.write("db/m3.sql", "create or replace function app.a()\nselect 9;\ncreate or replace function app.b()\nselect 9;\n")
        self.assertTrue(self.skipped(self.clone(("m1.sql", 1, 4), ("m2.sql", 1, 4))))

    def test_the_mode_is_off_by_default(self) -> None:
        self.write("db/m1.sql", "create function app.a()\n" + self.BODY)
        self.write("db/m2.sql", "create function app.b()\n" + self.BODY)
        self.write("db/m3.sql", "create or replace function app.a()\nselect 9;\ncreate or replace function app.b()\nselect 9;\n")
        clone = self.clone(("m1.sql", 1, 4), ("m2.sql", 1, 4))
        self.assertFalse(self.redefs(superseded=False).skips(clone))
        plain = count_tools.Redefinitions({"files": ["db/*.sql"], "definition": self.DEFINITION}, self.repo)
        self.assertFalse(plain.skips(clone))

    def test_two_live_definitions_of_different_objects_are_counted(self) -> None:
        self.write("db/m1.sql", "create function app.a()\n" + self.BODY)
        self.write("db/m2.sql", "create function app.b()\n" + self.BODY)
        self.assertFalse(self.skipped(self.clone(("m1.sql", 1, 4), ("m2.sql", 1, 4))))

    def test_a_live_and_a_superseded_definition_of_different_objects_are_counted(self) -> None:
        self.write("db/m1.sql", "create function app.a()\n" + self.BODY)
        self.write("db/m2.sql", "create function app.b()\n" + self.BODY)
        self.write("db/m3.sql", "create or replace function app.a()\nselect 9;\n")
        self.assertFalse(self.skipped(self.clone(("m1.sql", 1, 4), ("m2.sql", 1, 4))))

    def test_a_redefinition_inside_the_same_file_supersedes_nothing(self) -> None:
        self.write("db/m1.sql", "create function app.a()\n" + self.BODY + "create or replace function app.a()\n" + self.BODY)
        self.write("db/m2.sql", "create function app.b()\n" + self.BODY)
        self.assertFalse(self.skipped(self.clone(("m1.sql", 1, 4), ("m2.sql", 1, 4))))

    def test_the_redefinition_rule_still_holds(self) -> None:
        self.write("db/m1.sql", "create function app.a()\n" + self.BODY)
        self.write("db/m2.sql", "create or replace function app.a()\n" + self.BODY)
        clone = self.clone(("m1.sql", 1, 4), ("m2.sql", 1, 4))
        self.assertTrue(self.redefs().is_redefinition(clone))
        report = {"statistics": {"total": {"duplicatedLines": 4}}, "duplicates": [clone]}
        self.assertEqual(count_tools.clone_lines(report, self.redefs()), 0)
        self.assertEqual(count_tools.clone_rows(report, self.redefs()), [])

    def test_a_clone_reaching_live_statements_after_a_superseded_one_is_counted(self) -> None:
        # the clone runs on from the superseded function a into the live table and policy that follow its `;`.
        tail = "create table app.t (x int);\ncreate policy p on app.t using (true);\n"
        self.write("db/m1.sql", "create function app.a()\nreturns int as $$ select 1; $$;\n" + tail)
        self.write("db/m2.sql", "create function app.b()\nreturns int as $$ select 1; $$;\n" + tail)
        self.write("db/m3.sql", "create or replace function app.a()\nselect 9;\n")
        self.write("db/m4.sql", "create or replace function app.b()\nselect 9;\n")
        self.assertFalse(self.skipped(self.clone(("m1.sql", 1, 4), ("m2.sql", 1, 4))))
        # the dollar-quoted `;` inside the body does not end the superseded statement: lines 1-2 alone are hidden.
        self.assertTrue(self.skipped(self.clone(("m1.sql", 1, 2), ("m2.sql", 1, 2))))

    def test_a_live_body_against_its_own_superseded_predecessor_is_not_counted(self) -> None:
        # m2 replaces a; the clone of a's old body runs on from the new a into the function c that follows it,
        # so the object sets differ and the redefinition rule alone would count it.
        self.write("db/m1.sql", "create function app.a()\n" + self.BODY)
        self.write("db/m2.sql", "create or replace function app.a()\n" + self.BODY + "create function app.c()\n" + self.BODY)
        clone = self.clone(("m1.sql", 1, 4), ("m2.sql", 3, 8))
        self.assertFalse(self.redefs().is_redefinition(clone))
        self.assertTrue(self.skipped(clone))

    def test_the_old_body_against_a_helper_extracted_by_the_replacing_change_is_not_counted(self) -> None:
        # m2 replaces a and creates the helper h from a's old text; the old body is the only other copy.
        self.write("db/m1.sql", "create function app.a()\n" + self.BODY)
        self.write("db/m2.sql", "create or replace function app.a()\nselect app.h();\ncreate function app.h()\n" + self.BODY)
        self.assertTrue(self.skipped(self.clone(("m1.sql", 1, 4), ("m2.sql", 3, 6))))

    def test_two_live_bodies_in_the_replacing_change_are_counted(self) -> None:
        # the new a and the new helper h are both live, so their clone is real duplication.
        self.write("db/m1.sql", "create function app.a()\nselect 1;\n")
        self.write("db/m2.sql", "create or replace function app.a()\n" + self.BODY + "create function app.h()\n" + self.BODY)
        self.assertFalse(self.skipped(self.clone(("m2.sql", 1, 4), ("m2.sql", 5, 8))))

    def test_a_superseded_body_against_a_function_of_an_unrelated_change_is_counted(self) -> None:
        # m3 does not replace a, so its function z is another function and keeps counting against a's old body.
        self.write("db/m1.sql", "create function app.a()\n" + self.BODY)
        self.write("db/m2.sql", "create or replace function app.a()\nselect 9;\n")
        self.write("db/m3.sql", "create function app.z()\n" + self.BODY)
        self.assertFalse(self.skipped(self.clone(("m1.sql", 1, 4), ("m3.sql", 1, 4))))

    def test_text_of_an_earlier_change_against_a_superseded_body_is_counted(self) -> None:
        # only a later replacing file excuses a pair; z defined before m2 is not part of that change.
        self.write("db/m1.sql", "create function app.z()\n" + self.BODY)
        self.write("db/m2.sql", "create function app.a()\n" + self.BODY)
        self.write("db/m3.sql", "create or replace function app.a()\nselect 9;\n")
        self.assertFalse(self.skipped(self.clone(("m1.sql", 1, 4), ("m2.sql", 1, 4))))

    def test_statement_ends_skips_quotes_comments_and_dollar_quotes(self) -> None:
        text = (
            "select 'a;b';\n"             # single quote hides the inner `;`
            "select 'it''s;';\n"           # doubled quote is an escape
            "select \"x;y\" from t;\n"     # double-quoted identifier
            "-- note; here\n"              # line comment
            "/* block; */ select 1;\n"     # block comment
            "select $tag$ a; $tag$;\n"     # tagged dollar quote
            "select $1;\n"                 # a parameter, not a dollar quote
        )
        self.write("db/m1.sql", text)
        ends = self.redefs().statement_ends("db/m1.sql")
        lines = [text.count("\n", 0, offset) + 1 for offset in ends]
        self.assertEqual(lines, [1, 2, 3, 5, 6, 7])

    def test_the_flag_reaches_the_clone_commands_and_only_them(self) -> None:
        self.write("db/m1.sql", "create function app.a()\n" + self.BODY)
        self.write("db/m2.sql", "create function app.b()\n" + self.BODY)
        self.write("db/m3.sql", "create or replace function app.a()\nselect 9;\ncreate or replace function app.b()\nselect 9;\n")
        report = {"statistics": {"total": {"duplicatedLines": 8}},
                  "duplicates": [self.clone(("m1.sql", 1, 4), ("m2.sql", 1, 4))]}
        path = os.path.join(self.repo, "report.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(report, handle)
        entry = {"files": ["db/*.sql"], "definition": self.DEFINITION}
        with mock.patch.object(count_tools, "redefinition_config", lambda name: entry), \
                mock.patch.object(quality_profile, "REPO", self.repo):
            self.assertEqual(run_main("clone-lines", path, "dup")[:2], (0, "8\n"))
            self.assertEqual(run_main("clone-lines", path, "dup", "--superseded")[:2], (0, "4\n"))
            self.assertEqual(run_main("clone-groups", path, "dup", "--superseded")[:2], (0, "\n"))
        code, _, err = run_main("json-sum", path, "--superseded")
        self.assertEqual(code, 2)
        self.assertIn("--superseded is valid only with", err)


class NearMissCloneTests(unittest.TestCase):
    """renamed-lines / renamed-rows and kind-pairs / kind-rows: near-miss clones of a jscpd report."""

    DEFINITION = CloneRedefinitionTests.DEFINITION

    def setUp(self) -> None:
        self.repo = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.repo)
        write(self.repo, "db/m1.sql", "create function app.a()\nselect 1;\n")
        write(self.repo, "db/m2.sql", "create or replace function app.a()\nselect 1;\n")
        self.redefs = count_tools.Redefinitions({"files": ["db/*.sql"], "definition": self.DEFINITION}, self.repo)

    @staticmethod
    def pair(kind: str, fmt: str, first: tuple[str, int, int], second: tuple[str, int, int], **extra) -> dict:
        side = lambda f: {"name": f[0], "start": f[1], "end": f[2]}  # noqa: E731
        return {"kind": kind, "format": fmt, "lines": first[2] - first[1] + 1,
                "firstFile": side(first), "secondFile": side(second), **extra}

    def report(self) -> dict:
        return {"duplicates": [
            self.pair("renamed", "typescript", ("a.ts", 1, 10), ("b.ts", 1, 10)),          # 20 lines
            self.pair("renamed", "typescript", ("a.ts", 6, 15), ("c.ts", 1, 10)),          # a.ts 11-15, c.ts 1-10 are new
            self.pair("exact", "typescript", ("a.ts", 1, 3), ("d.ts", 1, 3)),              # a.ts 1-3 counted as exact
            self.pair("renamed", "css", ("a.vue", 1, 9), ("b.vue", 1, 9)),                 # markup sub-block: not counted
            self.pair("renamed", "sql", ("m1.sql", 1, 2), ("m2.sql", 1, 2)),               # a redefinition: not counted
            self.pair("similar", "typescript", ("a.ts", 1, 12), ("b.ts", 1, 12), similarity=0.9),
            self.pair("similar", "typescript", ("e.ts", 1, 20), ("f.ts", 1, 20), similarity=1.0),
            self.pair("exact", "css", ("x.vue", 1, 9), ("y.vue", 1, 9)),
        ]}

    def test_renamed_lines_are_distinct_lines_of_the_counted_formats_without_exact_and_redefinitions(self) -> None:
        # a.ts 1-15 (15) + b.ts 1-10 (10) + c.ts 1-10 (10), minus a.ts 1-3 (exact) and the exact d.ts (not in a renamed pair).
        self.assertEqual(count_tools.renamed_lines(self.report(), self.redefs, {"typescript", "sql"}), 32)

    def test_a_format_that_is_not_listed_is_not_counted(self) -> None:
        self.assertEqual(count_tools.renamed_lines(self.report(), self.redefs, {"sql"}), 0)
        self.assertEqual(count_tools.renamed_lines(self.report(), self.redefs, {"css"}), 18)

    def test_renamed_rows_list_the_counted_pairs_largest_first(self) -> None:
        rows = count_tools.renamed_rows(self.report(), self.redefs, {"typescript", "sql"})
        self.assertEqual(rows, ["10 a.ts 1 b.ts 1", "10 a.ts 6 c.ts 1"])

    def test_kind_pairs_counts_one_kind_and_rows_carry_the_similarity(self) -> None:
        self.assertEqual(count_tools.kind_pairs(self.report(), "similar", set()), 2)
        self.assertEqual(count_tools.kind_pairs(self.report(), "similar", {"sql"}), 0)
        self.assertEqual(count_tools.kind_rows(self.report(), "similar", set()),
                         ["20 1.0 e.ts 1 f.ts 1", "12 0.9 a.ts 1 b.ts 1"])

    def test_the_commands_print_the_figures(self) -> None:
        path = os.path.join(self.repo, "report.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(self.report(), handle)
        code, out, _ = run_main("kind-pairs", path, "similar", "typescript")
        self.assertEqual((code, out.strip()), (0, "2"))
        self.assertEqual(run_main("kind-pairs", path)[0], 2)
        missing = os.path.join(self.repo, ".claude", "quality-profile.json")
        with mock.patch.object(count_tools, "redefinition_config",
                               lambda name: _REAL_REDEFINITION_CONFIG(name, missing)):
            self.assertEqual(run_main("renamed-lines", path, "no-such-ratchet", "sql")[0], 2)


class CloneGroupTests(unittest.TestCase):
    """clone-groups, the input of the third-copy trigger (`ratchet.py copies`)."""

    pair = staticmethod(NearMissCloneTests.pair)

    def report(self) -> dict:
        return {"duplicates": [
            # one block copied three times (a.ts, b.ts, c.ts): two pairs sharing the a.ts side
            self.pair("exact", "typescript", ("src/a.ts", 10, 20), ("src/b.ts", 1, 11)),
            self.pair("exact", "typescript", ("src/a.ts", 12, 22), ("src/c.ts", 5, 15)),
            # a second copy of something else (two copies)
            self.pair("exact", "typescript", ("src/d.ts", 1, 9), ("src/e.ts", 1, 9)),
            self.pair("renamed", "typescript", ("src/f.ts", 1, 9), ("src/g.ts", 1, 9)),
        ]}

    def test_pairs_that_share_a_side_form_one_group(self) -> None:
        redefs = count_tools.Redefinitions(None, "/")
        self.assertEqual(count_tools.clone_groups(self.report(), redefs, set(), set()), [
            "3 11 src/a.ts:10-22 src/b.ts:1-11 src/c.ts:5-15",
            "2 9 src/d.ts:1-9 src/e.ts:1-9",
            "2 9 src/f.ts:1-9 src/g.ts:1-9",
        ])
        self.assertEqual(count_tools.clone_groups(self.report(), redefs, {"renamed"}, set()),
                         ["2 9 src/f.ts:1-9 src/g.ts:1-9"])


if __name__ == "__main__":
    unittest.main()
