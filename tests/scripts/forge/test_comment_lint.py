#!/usr/bin/env python3
"""Tests for scripts/forge/comment_lint.py (stdlib unittest; Python 3.9+).

Each test builds a throwaway git repository: a base commit, then the change in the working tree. All code is invented.

Run: python3 -m unittest discover -s tests/scripts/forge -v
"""
from __future__ import annotations

import importlib.util
import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SCRIPT = os.path.join(REPO, "scripts", "forge", "comment_lint.py")
_spec = importlib.util.spec_from_file_location("comment_lint", SCRIPT)
cl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cl)


def doc(lines, indent=""):
    return indent + "/**\n" + "".join(f"{indent} * {l}\n" for l in lines) + indent + " */\n"


class Case(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.root = os.path.join(self.tmp, "proj")
        os.makedirs(self.root)
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.email", "t@example.invalid")
        self.git("config", "user.name", "t")
        self.write("README.md", "x\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "base")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def git(self, *args):
        subprocess.run(["git", "-C", self.root, *args], check=True, capture_output=True)

    def write(self, rel, text):
        path = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)

    def commit(self):
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "more")

    def config(self, **values):
        self.write(".claude/project-config.json", json.dumps(values))

    def run_lint(self, *extra, base="HEAD"):
        out, err = io.StringIO(), io.StringIO()
        if "--ratio" not in extra and "stats" not in extra:
            extra = extra + ("--ratio", "100")  # A2 is tested on its own
        args = list(extra) + ["--base", base, "--profile", os.path.join(self.root, ".claude", "quality-profile.json")]
        with redirect_stdout(out), redirect_stderr(err):
            code = cl.main(args)
        return code, out.getvalue().splitlines(), err.getvalue()

    def codes(self, lines, path=None):
        found = []
        for line in lines[:-1]:
            loc, rest = line.split(": ", 1)
            if path is None or loc.startswith(path + ":"):
                found.append((int(loc.rsplit(":", 1)[1]), rest.split(" ", 1)[0]))
        return found


class IdsAndMarkers(Case):
    def test_ids_paragraph_signs_dates_and_branches_in_new_comments(self):
        self.write("src/a.js", "\n".join([
            "// Limits from AC-3 apply here.",               # 1 C1
            "// See plan K14 and decision Q11.",              # 2 C1
            "// The rule of spec 054 §3.3.",                  # 3 C1 + C2
            "// Mirrors the API, verified 2026-09-23.",       # 4 C3
            "// Dates look like 2026-01-31 in the payload.",  # 5 nothing
            "// Copied from feature/PROJ-1194 on the backend.", # 6 C3
            "// Phase 2 of the merge keeps the order.",       # 7 nothing (phase is not a cue word)
            "// Split out on spec/PROJ-1305-user-report.",    # 8 C3 (a ticket-named spec branch)
            "const x = 1;",
            "",
        ]))
        code, out, _e = self.run_lint()
        self.assertEqual(code, 1)
        blocking = [(n, c) for n, c in self.codes(out) if c.startswith("C")]
        self.assertEqual(blocking, [(1, "C1"), (2, "C1"), (3, "C1"), (3, "C2"), (4, "C3"), (6, "C3"), (8, "C3")])
        self.assertIn((1, "A5"), self.codes(out))  # seven comment lines in a row
        self.assertTrue(out[-1].startswith("comment-lint: C7 "))

    def test_every_label_blocks_in_a_comment(self):
        self.write("src/l.js", "\n".join([
            "// Follows DEC-2.",            # 1 C1
            "// Answers Q-1.",              # 2 C1
            "// Guards RISK-3.",            # 3 C1
            "// Fixes CRIT-1 and WARN-2.",  # 4 C1
            "// From NOTE-3.",              # 5 C1
            "// NOTE: keep the order.",     # 6 nothing
            "const z = 1;",
            "",
        ]))
        code, out, _e = self.run_lint()
        self.assertEqual(code, 1)
        self.assertEqual([(n, c) for n, c in self.codes(out) if c.startswith("C")],
                         [(1, "C1"), (2, "C1"), (3, "C1"), (4, "C1"), (5, "C1")])

    def test_markers_inside_strings_and_test_titles_are_not_comments(self):
        self.write("test/a.test.js", "\n".join([
            "const url = 'http://example.invalid/AC-1';",
            "it('AC-23 keeps the order', () => {});",
            "// AC-23: keeps the order",                       # 3 banner: C1
            "it('AC-23 [spec-002]: keeps the order', () => {});",
            "",
        ]))
        code, out, _e = self.run_lint()
        self.assertEqual(self.codes(out), [(3, "C1")])

    def test_project_key_pattern_with_a_prefix_is_blocking_and_generic_keys_are_advisory(self):
        self.config(ISSUE_KEY_PATTERN="PROJ-[0-9]+")
        self.commit()
        self.write("src/b.js", "// Added for PROJ-1302.\n// Uses SHA-256 and UTF-8.\nconst y = 2;\n")
        code, out, _e = self.run_lint()
        self.assertEqual(self.codes(out), [(1, "C1")])
        self.config(ISSUE_KEY_PATTERN="[A-Z][A-Z0-9]+-[0-9]+")  # generic: not used
        self.commit()
        self.write("src/b2.js", "// Added for PROJ-1302.\n// Uses SHA-256 and UTF-8.\nconst y = 3;\n")
        code, out, _e = self.run_lint()
        self.assertEqual(code, 0)
        self.assertEqual(self.codes(out), [(1, "A7")])

    def test_history_and_dependency_paths_are_advisory(self):
        self.write("src/c.js", "// Previously this threw.\n// See node_modules/x/lib/y.js for the cause.\nz();\n")
        code, out, _e = self.run_lint()
        self.assertEqual((code, self.codes(out)), (0, [(1, "A3"), (2, "A4")]))

    def test_spec_tags_block_and_lookalikes_do_not(self):
        self.write("src/t.js", "\n".join([
            "// Covers [spec-007].",                   # 1 C1
            "// Same as spec-007 above.",              # 2 C1
            "// Per spec-PROJ-1305.",                    # 3 C1
            "// See ecma-spec-262 for the grammar.",   # 4 nothing
            "// Checked by [spec-lint].",              # 5 nothing
            "// A spec-compliant parser.",             # 6 nothing
            "const t = 1;",
            "// Implements spec 7 of the protocol.",   # 8 C1: a number after `spec`; the reviewer marks it
            "const u = 2;",
            "",
        ]))
        code, out, _e = self.run_lint()
        self.assertEqual(code, 1)
        self.assertEqual(self.codes(out), [(1, "C1"), (2, "C1"), (3, "C1"), (8, "C1")])

    def test_forge_document_with_a_section_number_blocks(self):
        self.write("src/k.js", "\n".join([
            "// Filtered as contracts.md 5.2 says.",                     # 1 C2
            "// The rule of spec.md \u00a73.",                            # 2 C2 (once)
            "// See specs/001-a/plan.md#4-data.",                         # 3 C2
            "// As tasks/003-add-x.md step 2 does.",                      # 4 C2
            "// constitution.md:42",                                      # 5 C2
            "const k = 1;",
            "// https://example.invalid/blob/main/spec.md#3 is the RFC.", # 7 nothing: a URL
            "// Touches plan.md, 2 more files.",                          # 8 nothing: no section
            "// Reads api.spec.md 3 times.",                              # 9 nothing: another file
            "// See HISTORY.md 1.2.",                                     # 10 nothing: upper case
            "// The format is in spec.md.",                               # 11 nothing: no number
            "const m = 2;",
            "",
        ]))
        code, out, _e = self.run_lint()
        self.assertEqual(code, 1)
        self.assertEqual([(n, c) for n, c in self.codes(out) if c != "A5"],
                         [(1, "C2"), (2, "C2"), (3, "C2"), (4, "C2"), (5, "C2")])
        self.assertIn("src/k.js:1: C2 contracts.md 5.2", out)
        self.assertIn("src/k.js:2: C2 spec.md \u00a73", out)


class ProductMarkdown(Case):
    """Wrapper mode: the source repository `app/` is nested in the workspace."""

    def wrapper(self):
        app = os.path.join(self.root, "app")
        os.makedirs(app)
        for args in (("init", "-q", "-b", "main"), ("config", "user.email", "t@example.invalid"),
                     ("config", "user.name", "t")):
            subprocess.run(["git", "-C", app, *args], check=True, capture_output=True)
        self.write("app/README.md", "# App\n\nOld text with AC-1.\n")
        self.write("app/src/a.js", "const a = 1;\n")
        subprocess.run(["git", "-C", app, "add", "-A"], check=True, capture_output=True)
        subprocess.run(["git", "-C", app, "commit", "-q", "-m", "base"], check=True, capture_output=True)
        self.config(SOURCE_ROOT="app", ISSUE_KEY_PATTERN="PROJ-[0-9]+")

    def test_ids_and_citations_block_tickets_pass_and_the_paragraph_sign_is_advisory(self):
        self.wrapper()
        self.write("app/README.md", "\n".join([
            "# App",
            "",
            "Old text with AC-1.",                           # 3 old: not judged
            "Built for PROJ-1234.",                            # 4 nothing: a ticket key
            "Rule AC-3 holds.",                              # 5 C1
            "Tested by [spec-007].",                         # 6 C1
            "See [the plan](../specs/001-a/plan.md#4).",     # 7 C1 (the folder) + C2
            "Per \u00a7 4 of the terms.",                     # 8 A8
            "As spec.md \u00a7 3 says.",                      # 9 C2 only
            "Released on 2026-01-01; no longer beta.",       # 10 nothing: dates and history are not judged
            "Writes are queued (constitution \u00a72.1: services enqueue).",  # 11 C2
            "Kept as review.md \u00a7 Test Assessment says.",  # 12 C2
            "Dropped, see contracts.md \u00a7 Rejected.",      # 13 C2
            "Tokens follow OAuth spec section 4.1.",         # 14 nothing
            "",
        ]))
        self.write("app/src/a.js", "const a = 1;\n// For PROJ-1234.\n")  # code keeps the key check
        code, out, _e = self.run_lint()
        self.assertEqual(code, 1)
        self.assertEqual(self.codes(out, "README.md"), [(5, "C1"), (6, "C1"), (7, "C1"), (7, "C2"), (8, "A8"), (9, "C2"),
                                                        (11, "C2"), (12, "C2"), (13, "C2")])
        self.assertEqual(self.codes(out, "src/a.js"), [(2, "C1")])
        self.assertIn("README.md:5: C1 AC-3 (in a product document)", out)
        self.assertIn("README.md:8: A8 \u00a7 in a product document: blocks if it cites a Forge document", out)
        self.assertIn("README.md:11: C2 constitution \u00a72.1 (in a product document)", out)
        self.assertEqual(out[-1], "comment-lint: C9 A1 files=2")

    def test_spec_folder_paths_block_in_wrapper_mode_only(self):
        lines = "\n".join([
            " * Closes the gap left open in specs/014-data-explorer/review.md:",  # 1 C1 (wrapper)
            " * specs/034-students-api/data-model.md for the field contracts.",   # 2 C1 (wrapper)
            " * (see specs/028-cross-tab-session/contracts.md).",                 # 3 C1 (wrapper)
            " * Mirrors specs/PROJ-1305-user-report.",                            # 4 C1 (wrapper)
            " * Spec: https://example.invalid/specs/001-a/plan.md here.",         # 5 nothing: a URL
            " * Split out on spec/011-review-fixes.",                             # 6 C3: a branch, not a path
            " * Fixtures live in tests/specs/ and my-specs/001-a.",              # 7 nothing
            " * Runs tests/specs/001-login.cy.ts against src/specs/001-users.yaml.",  # 8 nothing: product files
            " * Steps in specs/001-login.feature; see ../specs/006-provider-failure-codes.",  # 9 C1 (the second)
            "",
        ])
        text = "/*\n" + lines + " */\nconst p = 1;\n"
        self.wrapper()
        self.write("app/src/p.js", text)
        code, out, _e = self.run_lint()
        self.assertEqual([(n, c) for n, c in self.codes(out) if c.startswith("C")],
                         [(2, "C1"), (3, "C1"), (4, "C1"), (5, "C1"), (7, "C3"), (10, "C1")])
        self.assertIn("src/p.js:2: C1 specs/014-data-explorer/review.md", out)
        self.assertIn("src/p.js:10: C1 specs/006-provider-failure-codes", out)
        self.write("src/p.js", text)  # the same comment in a standalone project
        os.remove(os.path.join(self.root, ".claude", "project-config.json"))
        code, out, _e = self.run_lint()
        self.assertEqual([(n, c) for n, c in self.codes(out, "src/p.js") if c.startswith("C")], [(7, "C3")])

    def test_a_long_document_has_no_length_findings_and_is_not_measured(self):
        self.wrapper()
        self.write("app/docs/guide.md", "Plain prose.\n" * 40)
        code, out, _e = self.run_lint("--ratio", "1")
        self.assertEqual((code, out), (0, ["comment-lint: C0 A0 files=1"]))
        code, out, _e = self.run_lint("stats")
        self.assertEqual(out[0], "source: added=0 comment=0 share=0% in_blocks_6plus=0 id_lines=0 doc_blocks=0")

    def test_standalone_project_skips_markdown(self):
        self.write("docs/x.md", "AC-3 and spec.md#3 and [spec-007].\n")
        code, out, _e = self.run_lint()
        self.assertEqual((code, out[-1]), (0, "comment-lint: C0 A0 files=0 skipped=md"))


class DocComments(Case):
    def test_doc_length_counts_description_lines_only(self):
        self.write("src/d.js", doc(["Line"] * 7) + "export function a() {}\n"
                   + doc(["One", "Two", "Three"]) + "export function b() {}\n"
                   + doc(["One", "Two", "@param {string} x - The x.", "@returns {number} The y.", "  more"])
                   + "export function c(x) {}\n")
        code, out, _e = self.run_lint()
        self.assertEqual(code, 1)
        self.assertEqual(self.codes(out), [(1, "C4"), (11, "A1")])

    def test_typescript_doc_comment_carries_no_types(self):
        self.write("src/e.ts", doc(["Adds one.", "@param {number} n - The number."]) +
                   "export const inc = (n: number) => n + 1;\n")
        code, out, _e = self.run_lint()
        self.assertEqual(self.codes(out), [(3, "C4")])

    def test_python_docstring_sections_do_not_count(self):
        body = '    """Summary line.\n\n    More text.\n\n    Args:\n' + "".join(f"        a{i}: thing.\n" for i in range(9)) \
            + '    """\n    return 1\n'
        long_doc = '    """' + "\n".join(["    Line."] * 8) + '\n    """\n    return 2\n'
        text = "def f(a):\n" + body + "\n\ndef g():\n" + long_doc + 'S = """# not a comment"""\n'
        self.write("pkg/m.py", text)
        code, out, _e = self.run_lint()
        self.assertEqual([c for _n, c in self.codes(out)], ["C4"])

    def test_go_doc_block_above_a_declaration(self):
        block = "".join(f"// Line {i}.\n" for i in range(8))
        self.write("cmd/main.go", "package main\n\n" + block + "func Run() {}\n\nfunc x() {\n" + block + "\ty := 1\n}\n")
        code, out, _e = self.run_lint()
        self.assertEqual(self.codes(out), [(3, "C4"), (14, "A5")])

    def test_vue_script_and_template(self):
        self.write("ui/W.vue", '<template>\n  <!-- AC-2: the empty state -->\n  <p/>\n</template>\n'
                   '<script setup lang="ts">\n' + doc(["Opens.", "@param {string} id - Id."]) +
                   "function open(id: string) {}\n</script>\n")
        code, out, _e = self.run_lint()
        self.assertEqual(self.codes(out), [(2, "C1"), (8, "C4")])

    def test_sql_comments_and_strings(self):
        self.write("db/v.sql", "-- Checked on 2026-02-01 against prod.\nSELECT '--not a comment' AS x;\n")
        code, out, _e = self.run_lint()
        self.assertEqual(self.codes(out), [(1, "C3")])

    def test_licence_header_is_skipped(self):
        self.write("src/f.js", "/*\n * Copyright 2026 Example. Licensed under MIT.\n * See AC-1 nowhere.\n"
                   + "".join(" * filler\n" for _ in range(8)) + " */\nconst a = 1;\n")
        code, out, _e = self.run_lint()
        self.assertEqual((code, self.codes(out)), (0, []))


class ChangedLinesOnly(Case):
    def test_old_lines_are_not_judged_and_an_edited_old_doc_is_advisory(self):
        self.write("src/g.js", doc(["Old line"] * 8 + ["See AC-9."]) + "export function g() {}\n")
        self.commit()
        self.write("src/g.js", doc(["Old line"] * 7 + ["New line", "See AC-9."]) + "export function g() {}\n")
        code, out, _e = self.run_lint()
        self.assertEqual((code, self.codes(out)), (0, [(1, "A6")]))

    def test_untracked_file_counts_as_added(self):
        self.write("src/new.js", "// From AC-4.\nconst n = 1;\n")
        code, out, _e = self.run_lint()
        self.assertEqual(self.codes(out), [(1, "C1")])

    def test_ratio_flag_and_threshold(self):
        self.write("src/h.js", "// a why\n" * 9 + "\n" + "const h = 1;\n" * 11)
        code, out, _e = self.run_lint("--ratio", "35")
        self.assertEqual(self.codes(out), [(1, "A2"), (1, "A5")])
        code, out, _e = self.run_lint("--ratio", "50")
        self.assertEqual(self.codes(out), [(1, "A5")])
        self.write("src/h.js", "// a why\n// still why\nconst h = 1;\n")  # under 20 added lines: no A2
        code, out, _e = self.run_lint("--ratio", "35")
        self.assertEqual(self.codes(out), [])


class Lexical(Case):
    """The reviewer's probes: each was a missed or a false comment before."""

    def test_python_docstring_after_a_multiline_signature_a_decorator_and_a_header_comment(self):
        long_doc = "".join(f"    Line {i}.\n" for i in range(8))
        self.write("pkg/p.py", "@decorator\ndef f(\n    a,\n    b,\n):  # note\n    \"\"\"\n" + long_doc
                   + "    \"\"\"\n    return a\n")
        code, out, _e = self.run_lint()
        self.assertEqual(self.codes(out), [(6, "C4")])

    def test_go_comment_with_a_blank_line_before_the_declaration_is_not_a_doc(self):
        block = "".join(f"// Line {i}.\n" for i in range(8))
        self.write("cmd/g.go", "package main\n\n" + block + "\nfunc Run() {}\n")
        code, out, _e = self.run_lint()
        self.assertEqual(self.codes(out), [(3, "A5")])

    def test_path_with_a_space_in_a_tracked_file(self):
        self.write("sp ace/a.c", "int a;\n")
        self.commit()
        self.write("sp ace/a.c", "int a;\n// From AC-6.\n")
        code, out, _e = self.run_lint()
        self.assertEqual(self.codes(out), [(2, "C1")])

    def test_form_feed_does_not_shift_line_numbers(self):
        self.write("src/ff.c", "int a;\x0c int b;\nint c; // From AC-1.\n")
        code, out, _e = self.run_lint()
        self.assertEqual(self.codes(out), [(2, "C1")])

    def test_crlf_and_empty_files(self):
        self.write("src/crlf.js", "const a = 1;\r\n// From AC-2.\r\n")
        self.write("src/empty.js", "")
        code, out, _e = self.run_lint()
        self.assertEqual(self.codes(out), [(2, "C1")])

    def test_non_utf8_file_is_read_with_replacement(self):
        path = os.path.join(self.root, "src", "latin.js")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as handle:
            handle.write(b"const s = '\xe9';\n// From AC-3.\n")
        code, out, _e = self.run_lint()
        self.assertEqual(self.codes(out), [(2, "C1")])

    def test_deleted_file_is_skipped(self):
        self.write("src/gone.js", "// From AC-4.\n")
        self.commit()
        os.remove(os.path.join(self.root, "src", "gone.js"))
        code, out, _e = self.run_lint()
        self.assertEqual((code, out[-1]), (0, "comment-lint: C0 A0 files=0"))

    def test_rust_lifetimes_template_escapes_text_blocks_and_css_urls(self):
        self.write("src/r.rs", "fn f<'a>(x: &'a str) -> &'a str { x } // From AC-5.\n")
        self.write("src/t.js", "const t = `a \\` b`; // From AC-6.\n")
        self.write("src/k.kt", 'val s = """\nsee http://example.invalid\n"""\n')
        self.write("src/s.css", "a { background: url(http://example.invalid/AC-9.png); }\n")
        code, out, _e = self.run_lint()
        self.assertEqual(self.codes(out), [(1, "C1"), (1, "C1")])
        self.assertTrue(all(l.split(":")[0] in ("src/r.rs", "src/t.js") for l in out[:-1]))

    def test_vue_one_line_script_does_not_swallow_the_rest(self):
        self.write("ui/V.vue", '<script src="./v.js"></script>\n<template>\n  <!-- AC-1: x -->\n</template>\n')
        code, out, _e = self.run_lint()
        self.assertEqual(self.codes(out), [(3, "C1")])

    def test_blank_lines_inside_a_block_comment_count(self):
        blocks, _ts = cl.comment_blocks("a.js", "/* a\n\n b\n\n c\n\n d */\nx();\n")
        self.assertEqual([n for n, _t in blocks[0].lines], [1, 2, 3, 4, 5, 6, 7])

    def test_block_comment_followed_by_code_is_not_a_whole_line(self):
        blocks, _ts = cl.comment_blocks("a.js", "/** y */ foo();\n")
        self.assertEqual([b.whole for b in blocks], [False])


class Cli(Case):
    def test_bad_base_is_a_usage_error(self):
        for base in ("no-such-rev", "--output=x", ""):
            code, _out, err = self.run_lint(base=base)
            self.assertEqual(code, 2, base)
        self.assertFalse(os.path.exists(os.path.join(self.root, "x")))

    def test_stats_exit_code_on_a_bad_base(self):
        code, _out, _err = self.run_lint("stats", base="no-such-rev")
        self.assertEqual(code, 2)

    def test_stats_split_source_and_test(self):
        self.write("src/s.js", "// why\nconst s = 1;\n")
        self.write("test/s.test.js", "it('x', () => {});\n")
        code, out, _e = self.run_lint("stats")
        self.assertEqual(code, 0)
        self.assertEqual(out[0], "source: added=2 comment=1 share=50% in_blocks_6plus=0 id_lines=0 doc_blocks=0")
        self.assertEqual(out[1], "test: added=1 comment=0 share=0% in_blocks_6plus=0 id_lines=0 doc_blocks=0")

    def test_unknown_extension_is_skipped_and_named(self):
        self.write("data/x.zzz", "AC-1\n")
        code, out, _e = self.run_lint()
        self.assertEqual((code, out[-1]), (0, "comment-lint: C0 A0 files=0 skipped=zzz"))

    def test_no_base_and_no_profile_is_a_usage_error(self):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = cl.main(["--profile", os.path.join(self.root, ".claude", "quality-profile.json")])
        self.assertEqual(code, 2)
        self.assertIn("pass --base", err.getvalue())


if __name__ == "__main__":
    unittest.main()
