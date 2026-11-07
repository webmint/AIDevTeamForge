#!/usr/bin/env python3
"""Tests for scripts/forge/new-exports.py and the profile key newExports (stdlib unittest; Python 3.9+).

A throwaway git repository holds invented sources in two languages and a component file. The base commit declares
some names; the working tree adds, redefines and moves others, so the test can tell new exports from old ones. The
languages are fixture data only: the script ships no patterns. All names are invented.

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

_spec = importlib.util.spec_from_file_location("new_exports", os.path.join(SCRIPTS, "new-exports.py"))
new_exports = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(new_exports)

PATTERNS = [
    {"files": ["src/**/*.ts"], "exclude": ["**/*.spec.ts"],
     "regex": r"^\s*export\s+(?:const|function|interface|type)\s+([A-Za-z_]\w*)"},
    {"files": ["src/**/*.vue"], "kind": "file"},
    {"files": ["db/*.sql"], "regex": r"(?i)^\s*create\s+(?:or\s+replace\s+)?(?:function|view)\s+([\w.]+)"},
]


def new_exports_entries(profile_path: str) -> list[dict]:
    with open(profile_path, encoding="utf-8") as handle:
        return json.load(handle)["newExports"]["patterns"]


class NewExportsCase(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = tempfile.mkdtemp(prefix="new-exports-")
        self.addCleanup(shutil.rmtree, self.repo)
        self.git("init", "-q")
        self.git("config", "user.email", "fixture@example.test")
        self.git("config", "user.name", "Fixture")
        self.write("src/billing/total.ts", "export function invoiceTotal() {}\nexport const RATE = 1;\n")
        self.write("src/billing/Card.vue", "<template><div /></template>\n")
        self.write("db/001_init.sql", "create function app.total() returns int as $$ select 1 $$;\n")
        self.write("other/ignored.ts", "export const OUTSIDE = 1;\n")
        self.commit("base")
        self.git("branch", "-M", "main")
        self.base = self.git("rev-parse", "HEAD").strip()
        self.write(".claude/quality-profile.json", json.dumps({"newExports": {"patterns": PATTERNS}}))

    def commit(self, message: str) -> None:
        self.git("add", "-A")
        self.git("-c", "commit.gpgsign=false", "commit", "-q", "-m", message)

    def git(self, *args: str) -> str:
        return subprocess.run(["git", "-C", self.repo, *args], capture_output=True, text=True, check=True).stdout

    def write(self, rel: str, text: str) -> None:
        path = os.path.join(self.repo, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)

    def names(self) -> list[str]:
        return [name for _path, _line, name in new_exports.new_exports(self.repo, self.base, PATTERNS)]

    def test_new_declarations_files_and_sql_objects_are_listed(self) -> None:
        self.write("src/billing/total.ts", "export function invoiceTotal() {}\nexport const RATE = 1;\nexport type Tax = number;\n")
        self.write("src/orders/Row.vue", "<template><tr /></template>\n")
        self.write("db/002_more.sql", "create or replace function app.fee() returns int as $$ select 2 $$;\n")
        self.assertEqual(sorted(self.names()), ["Row", "Tax", "app.fee"])

    def test_redefinitions_moves_tests_and_other_directories_are_not_new(self) -> None:
        self.write("db/002_redefine.sql", "create or replace function app.total() returns int as $$ select 3 $$;\n")
        self.write("src/reports/total.ts", "export function invoiceTotal() {}\n")
        self.write("src/billing/total.spec.ts", "export const fixture = 1;\n")
        self.write("other/more.ts", "export const ELSEWHERE = 2;\n")
        self.write("src/reports/Card.vue", "<template><span /></template>\n")
        self.assertEqual(self.names(), [])

    def test_committed_and_uncommitted_changes_both_count_with_their_lines(self) -> None:
        self.write("src/billing/committed.ts", "// header\nexport interface Line {}\n")
        self.commit("next")
        self.write("src/billing/loose.ts", "export const LOOSE = 1;\n")
        found = new_exports.new_exports(self.repo, self.base, PATTERNS)
        self.assertEqual(sorted(found), [("src/billing/committed.ts", 2, "Line"), ("src/billing/loose.ts", 1, "LOOSE")])

    def test_paths_with_spaces_quotes_and_non_ascii_are_read(self) -> None:
        # git ends a `+++` path holding a space with a tab, and quotes a path holding `"` (or, without
        # core.quotepath=off, a non-ASCII byte); ls-files and ls-tree print such names quoted unless -z is given.
        self.write("src/old name.ts", "export const KNOWN = 1;\n")
        self.write("src/my mod.ts", "export const SPACED = 1;\n")
        self.commit("names")
        self.base = self.git("rev-parse", "HEAD").strip()
        self.write("src/my mod.ts", "export const SPACED = 1;\nexport const SPACE_ADDED = 2;\n")
        self.write("src/caf\u00e9.ts", "export const CAFE = 1;\n")
        self.write('src/say"hi".ts', "export const QUOTED = 1;\n")
        self.git("add", "-A")
        self.write("src/new file.ts", "export const UNTRACKED = 1;\nexport const KNOWN = 1;\n")
        self.write("src/caf\u00e9 \u00fcber.ts", "export const LOOSE_UNICODE = 1;\n")
        found = sorted(new_exports.new_exports(self.repo, self.base, PATTERNS))
        self.assertEqual(found, [("src/caf\u00e9 \u00fcber.ts", 1, "LOOSE_UNICODE"), ("src/caf\u00e9.ts", 1, "CAFE"),
                                 ("src/my mod.ts", 2, "SPACE_ADDED"), ("src/new file.ts", 1, "UNTRACKED"),
                                 ('src/say"hi".ts', 1, "QUOTED")])

    def test_unquote_reads_git_c_style_quoting(self) -> None:
        self.assertEqual(new_exports.unquote('"b/src/caf\\303\\251.ts"'), "b/src/caf\u00e9.ts")
        self.assertEqual(new_exports.unquote('"b/a\\"q\\"\\tz"'), 'b/a"q"\tz')
        self.assertEqual(new_exports.unquote("b/plain name.ts\t"), "b/plain name.ts")

    def moved_profile(self) -> str:
        """Commit a base profile whose SQL pattern covers db/, then bind the working tree to schemas/ (same regex)."""
        profile = os.path.join(self.repo, ".claude", "quality-profile.json")
        self.commit("profile")
        self.base = self.git("rev-parse", "HEAD").strip()
        moved = [dict(p) for p in PATTERNS]
        moved[2]["files"] = ["schemas/*.sql"]
        self.write(".claude/quality-profile.json", json.dumps({"newExports": {"patterns": moved}}))
        return profile

    def test_a_function_moved_to_another_file_set_is_not_new_but_a_new_one_is(self) -> None:
        """The base declares app.total (and a quoted one) under db/; schemas/ re-declares them and adds app.fresh."""
        self.write("db/002_quoted.sql", 'create function "app"."keep"() returns int as $$ select 1 $$;\n')
        self.git("add", "-A")
        profile = self.moved_profile()
        self.write("schemas/all.sql", "create function app.total() returns int as $$ select 1 $$;\n"
                   'create function "app"."keep"() returns int as $$ select 1 $$;\n'
                   "create function app.fresh() returns int as $$ select 9 $$;\n")
        found = new_exports.new_exports(self.repo, self.base, new_exports_entries(profile), profile)
        self.assertEqual([name for _p, _l, name in found], ["app.fresh"])

    def test_an_unreadable_base_profile_falls_back_to_the_branch_globs(self) -> None:
        profile = self.moved_profile()
        self.write("schemas/all.sql", "create function app.total() returns int as $$ select 1 $$;\n")
        entries = new_exports_entries(profile)
        self.assertEqual(new_exports.base_names(self.repo, self.base, [":(glob)schemas/*.sql"], entries, None)[2], set())
        self.assertEqual(new_exports.base_names(self.repo, self.base, [":(glob)schemas/*.sql"], entries, profile)[2],
                         {"app.total"})

    def test_cli_prints_the_list_and_the_count(self) -> None:
        self.write("src/billing/extra.ts", "export const EXTRA = 1;\n")
        out = io.StringIO()
        with redirect_stdout(out):
            code = new_exports.main(["--base", self.base, "--profile", os.path.join(self.repo, ".claude", "quality-profile.json")])
        self.assertEqual(code, 0)
        self.assertEqual(out.getvalue().splitlines(), ["src/billing/extra.ts:1: EXTRA", "new-exports=1"])

    def test_cli_defaults_the_base_to_the_merge_base_with_the_integration_ref(self) -> None:
        profile = os.path.join(self.repo, ".claude", "quality-profile.json")
        self.write(".claude/quality-profile.json", json.dumps({"integrationRef": "main", "newExports": {"patterns": PATTERNS}}))
        self.git("switch", "-q", "-c", "feature")
        self.write("src/billing/branch.ts", "export const BRANCH = 1;\n")
        self.commit("feature work")
        out = io.StringIO()
        with redirect_stdout(out):
            code = new_exports.main(["--profile", profile])
        self.assertEqual(code, 0)
        self.assertEqual(out.getvalue().splitlines(), ["src/billing/branch.ts:1: BRANCH", "new-exports=1"])

    def test_an_unset_binding_says_so_on_one_line_and_exits_0(self) -> None:
        profile = os.path.join(self.repo, ".claude", "quality-profile.json")
        for binding in ({"newExports": {}}, {"newExports": {"patterns": []}}, {}):
            with self.subTest(binding=binding):
                self.write(".claude/quality-profile.json", json.dumps(binding))
                out, err = io.StringIO(), io.StringIO()
                with redirect_stdout(out), redirect_stderr(err):
                    code = new_exports.main(["--base", self.base, "--profile", profile])
                self.assertEqual(code, 0)
                self.assertEqual(err.getvalue(), "")
                self.assertEqual(out.getvalue().splitlines(), [
                    "new-exports: newExports.patterns is unset; list the new exports from the diff by hand"])

    def test_a_missing_binding_is_unset_and_a_bad_base_exits_2(self) -> None:
        out = io.StringIO()
        with redirect_stderr(io.StringIO()), redirect_stdout(out):
            missing = new_exports.main(["--profile", os.path.join(self.repo, ".claude", "absent.json")])
            bad_base = new_exports.main(["--base", "no-such-rev", "--profile",
                                         os.path.join(self.repo, ".claude", "quality-profile.json")])
        self.assertEqual((missing, bad_base), (0, 2))
        self.assertEqual(out.getvalue(), "new-exports: no .claude/quality-profile.json; run python3 scripts/forge/quality_profile.py init\n")

    def test_glob_reads_like_a_git_pathspec(self) -> None:
        self.assertTrue(new_exports.glob_regex("src/**/*.ts").match("src/a.ts"))
        self.assertTrue(new_exports.glob_regex("src/**/*.ts").match("src/x/y/a.ts"))
        self.assertFalse(new_exports.glob_regex("src/*.ts").match("src/x/a.ts"))
        self.assertEqual(new_exports.literal_root("packages/*/src/**/*.ts"), "packages")
        self.assertEqual(new_exports.literal_root("*.ts"), ".")


class NewExportsBindingTests(unittest.TestCase):
    def problems(self, section: object) -> list[str]:
        return quality_profile.validate({"newExports": section}, repo=SCRIPTS)

    def test_a_valid_section_passes(self) -> None:
        self.assertEqual(self.problems({"patterns": PATTERNS}), [])

    def test_each_entry_needs_files_and_exactly_one_of_regex_or_file_kind(self) -> None:
        found = self.problems({"patterns": [{"regex": "x"}, {"files": ["a/*.ts"]}, {"files": ["a/*.ts"], "kind": "file", "regex": "(x)"}]})
        self.assertIn("newExports.patterns[0].files: missing", found)
        self.assertIn("newExports.patterns[0].regex: needs a capture group for the exported name", found)
        self.assertIn('newExports.patterns[1]: give either a regex or "kind": "file"', found)
        self.assertIn('newExports.patterns[2]: give either a regex or "kind": "file"', found)

    def test_a_regex_that_does_not_compile_or_an_unknown_key_fails(self) -> None:
        found = self.problems({"patterns": [{"files": ["a/*.ts"], "regex": "(", "lang": "ts"}], "tool": "x"})
        self.assertIn("newExports: unknown key: tool", found)
        self.assertIn("newExports.patterns[0]: unknown key: lang", found)
        self.assertTrue(any(p.startswith("newExports.patterns[0].regex: does not compile") for p in found))


if __name__ == "__main__":
    unittest.main()
