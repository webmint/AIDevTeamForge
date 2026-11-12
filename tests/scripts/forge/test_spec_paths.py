#!/usr/bin/env python3
"""Tests for scripts/forge/spec_paths.py (stdlib unittest; Python 3.9+).

Each test builds a throwaway project dir with invented source files, a spec and optionally a /specify run report.
All data is invented.

Run: python3 -m unittest discover -s tests/scripts/forge -p 'test_spec_paths.py' -v
"""
from __future__ import annotations

import io
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(REPO, "scripts", "forge"))
import spec_paths  # noqa: E402
import spec_refs  # noqa: E402

FEATURE = "specs/900-widget"

SPEC = """# Spec: Widget

## Request (verbatim)

> Fix `src/secret/request_only.py:1` please, see https://example.invalid/docs/page.html

## 2. Current State

- `src/widget/spin.py:10-20` — spins; again `src/widget/spin.py:15-30` and `spin.py:40`.
- `src/widget/spin.py:12, 50-60` and `lib/missing/gone.py:3`.
- Docs at https://example.invalid/a/b.md and www.example.invalid/c/d.js are links; e.g. nothing; `/plan` runs.
- `src/widget/` is a directory; `README.md` is a file; version 1.2.3 and Node.js are not paths.
- The validator trims the id but the DAO keeps the raw value; the cache key is lower-cased.
"""

RUN_REPORT = """# Run report

## What was done

1. Read `src/other/helper.py` and `src/only/elsewhere.py` here but this section is not Sources read.

## Sources read

- `src/other/helper.py:7-9` — the helper
- `src/widget/spin.py:1-5`

## Notes

- Default case handling checked.
"""


class Base(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.feature = os.path.join(self.root, FEATURE)
        spec_refs._WALK_CACHE.clear()
        self.put("src/widget/spin.py", "x = 1\n")
        self.put("src/other/helper.py", "y = 2\n")
        self.put("src/secret/request_only.py", "z = 3\n")
        self.put("README.md", "hi\n")
        self.put("src/only/elsewhere.py", "w = 4\n")
        self.put("src/a/dup.py", "1\n")
        self.put("src/b/dup.py", "2\n")
        self.put(FEATURE + "/spec.md", SPEC)

    def tearDown(self):
        shutil.rmtree(self.root)

    def put(self, rel, text):
        path = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)

    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = spec_paths.main(list(argv) + ["--root", self.root])
        return code, out.getvalue(), err.getvalue()

    def section(self, text, title):
        parts = text.split("## ")
        return next(p for p in parts if p.startswith(title)).split("\n", 1)[1]


class Paths(Base):
    def test_files_merge_ranges_and_skip_request_urls_dirs(self):
        code, out, _e = self.run_cli(FEATURE)
        self.assertEqual(code, 0)
        files = self.section(out, "Files to verify")
        self.assertIn("- src/widget/spin.py (lines 10-20, 12, 15-30, 40, 50-60)", files)
        self.assertIn("- README.md\n", files)
        self.assertNotIn("request_only", files)
        self.assertNotIn("example.invalid", out.split("## Author")[0])
        self.assertEqual(files.count("spin.py"), 1)

    def test_not_found_lists_only_slash_tokens_without_noise(self):
        _c, out, _e = self.run_cli(FEATURE)
        missing = self.section(out, "Cited but not found")
        self.assertIn("- lib/missing/gone.py", missing)
        for noise in ("Node.js", "1.2.3", "/plan", "src/widget/", "e.g"):
            self.assertNotIn(noise, missing)

    def test_ambiguous_basename_lists_candidates_up_to_limit(self):
        self.put(FEATURE + "/spec.md", SPEC + "\nSee `dup.py:1` here.\n")
        files = self.section(self.run_cli(FEATURE)[1], "Files to verify")
        self.assertIn("- src/a/dup.py (lines 1) (one of 2 matches for dup.py)", files)
        self.assertIn("- src/b/dup.py (lines 1) (one of 2 matches for dup.py)", files)
        for i in range(5):
            self.put("pkg{}/dup.py".format(i), "x\n")
        spec_refs._WALK_CACHE.clear()
        files = self.section(self.run_cli(FEATURE)[1], "Files to verify")
        self.assertIn("dup.py ambiguous: 7 files match", files)
        self.assertNotIn("- src/a/dup.py", files)

    def test_default_run_report_adds_sources_read_only(self):
        self.put(FEATURE + "/runs/specify.md", RUN_REPORT)
        out = self.run_cli(FEATURE)[1]
        files = self.section(out, "Files to verify")
        self.assertIn("- src/other/helper.py (lines 7-9)", files)
        self.assertIn("(lines 1-5, 10-20", files)  # the spin.py ranges of both sources are merged
        self.assertNotIn("elsewhere.py", out.split("## Cited")[0])  # named only outside `## Sources read`
        notes = self.section(out, "Author's notes")
        self.assertIn("specs/900-widget/runs/specify.md:", notes)

    def test_without_run_report_the_spec_alone(self):
        out = self.run_cli(FEATURE)[1]
        self.assertNotIn("helper.py", out)

    def test_explicit_run_report_and_missing_one(self):
        self.put("elsewhere/report.md", RUN_REPORT)
        out = self.run_cli(FEATURE, "--run-report", "elsewhere/report.md")[1]
        self.assertIn("src/other/helper.py", out)
        code, _o, err = self.run_cli(FEATURE, "--run-report", "nope.md")
        self.assertEqual(code, 2)
        self.assertIn("nope.md", err)

    def test_notes_cover_spec_lines_with_keywords_not_the_request(self):
        out = self.run_cli(FEATURE)[1]
        notes = self.section(out, "Author's notes")
        self.assertIn("specs/900-widget/spec.md:13: - The validator trims the id", notes)
        self.assertNotIn("Fix `src/secret", notes)

    def test_long_note_lines_are_cut(self):
        self.put(FEATURE + "/spec.md", SPEC + "\nThe default is " + "x" * 600 + "\n")
        notes = self.section(self.run_cli(FEATURE)[1], "Author's notes")
        self.assertIn("...", notes)
        self.assertNotIn("x" * 500, notes)

    def test_security_focus_and_output_file(self):
        code, out, _e = self.run_cli(FEATURE)
        self.assertIn("## Security focus", out)
        self.assertIn("data-addressing", out)
        with open(os.path.join(self.feature, "gates", "reviewer-inputs.txt"), encoding="utf-8") as handle:
            self.assertEqual(handle.read(), out)
        self.assertEqual([n for n in os.listdir(os.path.join(self.feature, "gates"))], ["reviewer-inputs.txt"])

    def test_spec_without_paths_prints_none(self):
        self.put(FEATURE + "/spec.md", "# Spec\n\n## 1. Overview\n\nNothing cited.\n")
        out = self.run_cli(FEATURE)[1]
        self.assertEqual(self.section(out, "Files to verify").strip(), "(none)")
        self.assertEqual(self.section(out, "Cited but not found").strip(), "(none)")

    def test_directories_and_extensionless_plain_text_are_not_reported(self):
        self.put("src/pkg/inner.py", "q\n")
        self.put(FEATURE + "/spec.md", "# S\n\n## 1. O\n\nSee `src/pkg`, pkg/inner, read/write, `x/y` and a/b.js.\n")
        missing = self.section(self.run_cli(FEATURE)[1], "Cited but not found")
        self.assertNotIn("src/pkg", missing)
        self.assertNotIn("read/write", missing)
        self.assertNotIn("pkg/inner", missing)
        self.assertIn("- x/y", missing)  # a code span
        self.assertIn("- a/b.js", missing)  # a file extension

    def test_source_root_directory_is_not_reported_and_files_resolve(self):
        self.put(".claude/project-config.json", '{"SOURCE_ROOT": "app"}')
        self.put("app/src/core/main.py", "m\n")
        self.put(FEATURE + "/spec.md", "# S\n\n## 1. O\n\nSee `src/core/main.py:2-3` and `src/core`.\n")
        out = self.run_cli(FEATURE)[1]
        self.assertIn("- app/src/core/main.py (lines 2-3)", self.section(out, "Files to verify"))
        self.assertNotIn("src/core", self.section(out, "Cited but not found"))

    def test_nested_repo_files_resolve_and_worktree_files_do_not(self):
        self.put("sub/.git/HEAD", "ref\n")
        self.put("sub/lib/nested.py", "n\n")
        self.put("wt/.git", "gitdir: elsewhere\n")
        self.put("wt/lib/hidden.py", "h\n")
        self.put(FEATURE + "/spec.md", "# S\n\n## 1. O\n\nSee `lib/nested.py:1` and `lib/hidden.py:1`.\n")
        out = self.run_cli(FEATURE)[1]
        self.assertIn("- sub/lib/nested.py (lines 1)", out)
        self.assertIn("- lib/hidden.py", self.section(out, "Cited but not found"))

    def test_feature_dir_relative_path_wins_over_the_suffix_search(self):
        self.put(FEATURE + "/brief.md", "b\n")
        self.put("other/brief.md", "x\n")
        self.put("more/brief.md", "x\n")
        self.put(FEATURE + "/spec.md", "# S\n\n## 1. O\n\nSee `brief.md:1` and `@ap/common`, `@scope/pkg`.\n")
        out = self.run_cli(FEATURE)[1]
        self.assertIn("- specs/900-widget/brief.md (lines 1)", out)
        self.assertNotIn("other/brief.md", out)
        self.assertNotIn("@", self.section(out, "Cited but not found"))

    def test_en_dash_range_keeps_both_ends(self):
        self.put(FEATURE + "/spec.md", "# S\n\n## 1. O\n\nSee `src/widget/spin.py:10–20`.\n")
        self.assertIn("- src/widget/spin.py (lines 10-20)", self.run_cli(FEATURE)[1])

    def test_unreadable_run_report_is_exit_two(self):
        self.put(FEATURE + "/runs/specify.md", RUN_REPORT)
        path = os.path.join(self.feature, "runs", "specify.md")
        os.chmod(path, 0)
        try:
            if os.access(path, os.R_OK):
                self.skipTest("running as a user that can read mode-0 files")
            code, _o, err = self.run_cli(FEATURE)
        finally:
            os.chmod(path, 0o644)
        self.assertEqual(code, 2)
        self.assertIn("specify.md", err)

    def test_output_file_keeps_its_mode(self):
        self.run_cli(FEATURE)
        out = os.path.join(self.feature, "gates", "reviewer-inputs.txt")
        os.chmod(out, 0o640)
        self.run_cli(FEATURE)
        self.assertEqual(os.stat(out).st_mode & 0o777, 0o640)

    def test_missing_spec_is_exit_two(self):
        code, _o, err = self.run_cli("specs/999-none")
        self.assertEqual(code, 2)
        self.assertIn("spec.md", err)


if __name__ == "__main__":
    unittest.main()
