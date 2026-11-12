#!/usr/bin/env python3
"""Tests for scripts/forge/closure_check.py and its shared module research_closure.py (stdlib unittest).

The project is the synthetic multi-language fixture in research_fixtures.py (JS, Python, Go, Java). The ctags runs use
a fake `ctags` on PATH that prints recorded Universal Ctags JSON; a real Universal Ctags run is added when one is
installed.

Run: python3 -m unittest discover -s tests/scripts/forge -p 'test_closure_check.py' -v
"""
from __future__ import annotations

import io
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(REPO, "scripts", "forge"))
sys.path.insert(0, HERE)
import closure_check  # noqa: E402
import research_closure as rc  # noqa: E402
import research_fixtures as fx  # noqa: E402

LANGS = ("js", "py", "go", "java")


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.root = os.path.join(self.tmp, "proj")
        fx.write_project(self.root)
        os.makedirs(os.path.join(self.root, "research"))
        self.report = os.path.join(self.root, "research", "2026-11-13-topic.md")
        self.ledger = os.path.join(self.root, "research", "2026-11-13-topic-ledger.md")
        self.out = os.path.join(self.root, "research", "2026-11-13-topic-closure.txt")
        self.path = os.environ.get("PATH", "")
        self.bin = os.path.join(self.tmp, "bin")

    def tearDown(self):
        os.environ["PATH"] = self.path
        shutil.rmtree(self.tmp, ignore_errors=True)

    def fake_ctags(self, tags=None):
        fx.write_fake_ctags(self.bin, tags)
        os.environ["PATH"] = self.bin + os.pathsep + self.path

    def no_ctags(self):
        os.makedirs(self.bin, exist_ok=True)
        os.environ["PATH"] = self.bin  # neither the real nor a fake ctags

    def write(self, path, text):
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)

    def run_check(self, ledger_text, *extra, report=None):
        self.write(self.ledger, ledger_text)
        if report is not None:
            self.write(self.report, report)
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = closure_check.main([self.report, "--root", self.root] + list(extra))
        return code, out.getvalue(), err.getvalue()


class MissedCalleeTest(Base):
    """The calibration case: a path builder calls a normaliser the ledger does not name."""

    def test_complete_ledgers_are_clean_with_ctags(self):
        self.fake_ctags()
        for lang in LANGS:
            with self.subTest(lang=lang):
                code, out, _ = self.run_check(fx.LEDGERS[lang], "--index", "ctags")
                self.assertEqual(code, 0, out)
                self.assertIn("closure-check: 0 blocking, 0 advisory", out)

    def test_missing_callee_blocks_with_ctags(self):
        self.fake_ctags()
        for lang in LANGS:
            name = fx.OMITTED[lang][0]
            with self.subTest(lang=lang):
                code, out, _ = self.run_check(fx.MISSING[lang], "--index", "ctags")
                self.assertEqual(code, 1, out)
                lines = [l for l in out.splitlines() if l.startswith("missed_ref ")]
                self.assertEqual(len(lines), 1, out)
                self.assertIn("uses `%s`" % name, lines[0])
                self.assertIn("index: ctags index", out)

    def test_missing_callee_is_advisory_with_regex(self):
        self.no_ctags()
        for lang in LANGS:
            name = fx.OMITTED[lang][0]
            with self.subTest(lang=lang):
                code, out, _ = self.run_check(fx.MISSING[lang], "--index", "auto")
                self.assertEqual(code, 0, out)
                lines = [l for l in out.splitlines() if l.startswith("advisory missed_ref ")]
                self.assertEqual(len(lines), 1, out)
                self.assertIn("uses `%s`" % name, lines[0])
                self.assertIn("index: regex index", out)

    def test_complete_ledgers_are_clean_with_regex(self):
        for lang in LANGS:
            with self.subTest(lang=lang):
                code, out, _ = self.run_check(fx.LEDGERS[lang], "--index", "regex")
                self.assertEqual(code, 0, out)
                self.assertIn("closure-check: 0 blocking, 0 advisory", out)

    def test_ignored_token_and_exclusion_silence_it(self):
        self.fake_ctags()
        ignored = fx.MISSING["js"].replace("- `join` → external\n",
                                           "- `join` → external\n- `normalizeSegment` → ignored — test only\n")
        code, out, _ = self.run_check(ignored, "--index", "ctags")
        self.assertEqual(code, 0, out)
        report = "# R\n\n## Coverage\n- `normalizeSegment` `src/js/paths.js:3` — excluded — trims only, out of scope\n"
        code, out, _ = self.run_check(fx.MISSING["js"], "--index", "ctags", report=report)
        self.assertEqual(code, 0, out)

    def test_edge_under_another_name_at_the_definition_line_counts(self):
        self.fake_ctags()
        renamed = fx.LEDGERS["js"].replace("- `normalizeSegment` → `src/js/paths.js:3`",
                                           "- `paths.normalise` → `src/js/paths.js:3`")
        code, out, _ = self.run_check(renamed, "--index", "ctags")
        self.assertEqual(code, 0, out)

    def test_no_index(self):
        code, out, _ = self.run_check(fx.MISSING["go"], "--index", "none")
        self.assertEqual(code, 0, out)
        self.assertIn("missed-reference check skipped", out)

    def test_forced_ctags_missing_is_exit_2(self):
        self.no_ctags()
        code, _, err = self.run_check(fx.LEDGERS["js"], "--index", "ctags")
        self.assertEqual(code, 2)
        self.assertIn("Universal Ctags not found", err)

    @unittest.skipUnless(rc.universal_ctags(), "Universal Ctags is not installed")
    def test_real_universal_ctags(self):
        for lang in LANGS:
            with self.subTest(lang=lang):
                code, out, _ = self.run_check(fx.MISSING[lang], "--index", "ctags")
                self.assertEqual(code, 1, out)
                self.assertIn("uses `%s`" % fx.OMITTED[lang][0], out)


class ClosureTest(Base):
    def test_items_depths_and_output_file(self):
        code, out, _ = self.run_check(fx.LEDGERS["js"], "--index", "none")
        self.assertEqual(code, 0, out)
        self.assertIn("D0 `getProfile` src/js/handler.js:4 — read in ledger", out)
        self.assertIn("D1 `buildUserPath` src/js/paths.js:7 — read in ledger", out)
        self.assertIn("D2 `normalizeSegment` src/js/paths.js:3 — leaf (depth 2)", out)
        with open(self.out, encoding="utf-8") as handle:
            self.assertEqual(handle.read(), out)

    def test_not_read_within_depth(self):
        head, tail = fx.LEDGERS["js"].split("### `buildUserPath`")
        ledger = head + "### `checkAccess`" + tail.split("### `checkAccess`")[1]
        code, out, _ = self.run_check(ledger, "--index", "none")
        self.assertEqual(code, 1)
        self.assertIn("not_read D1 `buildUserPath` src/js/paths.js:7", out)
        report = "## Coverage\n- `buildUserPath` `src/js/paths.js:7` — excluded — generated\n"
        code, out, _ = self.run_check(ledger, "--index", "none", report=report)
        self.assertEqual(code, 0, out)

    def test_depth_one_makes_depth_one_items_leaves(self):
        ledger = fx.LEDGERS["js"].split("### `buildUserPath`")[0]  # no entries for the depth-1 items
        code, out, _ = self.run_check(ledger, "--index", "none", "--depth", "1")
        self.assertEqual(code, 0, out)
        self.assertNotIn("normalizeSegment", out)

    def test_cap_lists_over_cap_items(self):
        code, out, _ = self.run_check(fx.LEDGERS["js"], "--index", "none", "--cap", "2")
        self.assertIn("items 4 (2 in cap, 2 over cap)", out)
        self.assertIn("— not covered: over cap", out)

    def test_seed_reached_twice_counts_once_at_its_nearest_depth(self):
        ledger = fx.LEDGERS["js"].replace(
            "- `getProfile` `src/js/handler.js:4` — pass 1 — top-down",
            "- `getProfile` `src/js/handler.js:4` — pass 1 — top-down\n"
            "- `normalizeSegment` `src/js/paths.js:3` — pass 1 — bottom-up")
        code, out, _ = self.run_check(ledger, "--index", "none")
        self.assertEqual(code, 1, out)  # a seed at depth 0 needs its own ledger entry
        self.assertIn("not_read D0 `normalizeSegment`", out)
        self.assertEqual(out.count("`normalizeSegment` src/js/paths.js:3"), 2)  # item line + finding

    def test_python_entry_matched_by_containing_range(self):
        ledger = fx.LEDGERS["py"].replace("`src/py/store.py:8`", "`src/py/store.py:9`")
        code, out, _ = self.run_check(ledger, "--index", "none")
        self.assertEqual(code, 0, out)
        self.assertIn("D1 `object_path` src/py/store.py:9 — read in ledger", out)


class ReviewCasesTest(Base):
    def test_php_and_cpp_arrows_inside_names(self):
        ledger = fx.LEDGERS["js"].replace("- `readFile` → external",
                                          "- `$this->save` → external\n- `ptr->helper()` -> external")
        code, out, _ = self.run_check(ledger, "--index", "none")
        self.assertEqual(code, 0, out)
        ledger = rc.parse_ledger(ledger)
        names = [e.name for e in ledger.entries[0].edges]
        self.assertIn("$this->save", names)
        self.assertIn("ptr->helper()", names)

    def test_edge_to_a_body_line_is_the_same_item(self):
        ledger = fx.LEDGERS["js"].replace("- `buildUserPath` → `src/js/paths.js:7`",
                                          "- `buildUserPath` → `src/js/paths.js:8`\n"
                                          "- `buildUserPath` → `src/js/paths.js:9`")
        code, out, _ = self.run_check(ledger, "--index", "none")
        self.assertEqual(code, 0, out)
        self.assertIn("items 4 (4 in cap", out)
        self.assertIn("D1 `buildUserPath` src/js/paths.js:8 — read in ledger", out)

    def test_over_cap_entries_are_not_checked(self):
        self.fake_ctags()
        code, out, _ = self.run_check(fx.MISSING["js"], "--index", "ctags", "--cap", "2")
        self.assertNotIn("missed_ref", out)

    def test_member_access_to_another_file_is_advisory_with_ctags(self):
        self.fake_ctags()
        handler = os.path.join(self.root, "src", "js", "caller.js")
        self.write(handler, "function callIt(repo) {\n  return repo.get(1);\n}\n")
        ledger = ("## Seeds\n- `callIt` `src/js/caller.js:1` — pass 1 — top-down\n\n"
                  "## Read\n### `callIt` `src/js/caller.js:1-3`\n")
        code, out, _ = self.run_check(ledger, "--index", "ctags")
        self.assertEqual(code, 0, out)
        self.assertIn("advisory missed_ref `callIt`", out)
        self.assertIn("uses `get`", out)
        self.assertIn("member access", out)

    def test_ctags_junk_and_failures(self):
        tags = fx.TAGS + [("x", "y", 1, "function")]
        fx.write_fake_ctags(self.bin, tags)
        with open(os.path.join(self.bin, "tags.jsonl"), "a", encoding="utf-8") as handle:
            handle.write("42\nnull\n[1]\nnot json\n")
        os.environ["PATH"] = self.bin + os.pathsep + self.path
        code, out, _ = self.run_check(fx.MISSING["go"], "--index", "ctags")
        self.assertEqual(code, 1, out)
        self.assertIn("uses `normalizeID`", out)
        exe = os.path.join(self.bin, "ctags")
        with open(exe, "a", encoding="utf-8") as handle:
            handle.write("sys.exit(3)\n")
        code, _, err = self.run_check(fx.MISSING["go"], "--index", "ctags")
        self.assertEqual(code, 2)
        self.assertIn("ctags failed", err)
        code, out, _ = self.run_check(fx.MISSING["go"], "--index", "auto")
        self.assertEqual(code, 0, out)
        self.assertIn("ctags failed", out)
        self.assertIn("regex index", out)
        self.assertIn("advisory missed_ref", out)

    def test_ctags_with_no_definitions_skips(self):
        self.fake_ctags(tags=[])
        code, out, _ = self.run_check(fx.MISSING["js"], "--index", "ctags")
        self.assertEqual(code, 0, out)
        self.assertIn("ctags found no definitions", out)


class ReReviewCasesTest(Base):
    def test_slash_star_in_comments_strings_and_regex_opens_no_block(self):
        lines = [
            "function f(a) {  // joins root/*",
            "  x = 1  # a/*.py",
            "  const g = `lib/*.js`;",
            '  const r = "src/**/*.js";',
            "  return afterAll(a);",
            "}",
        ]
        self.assertIn("afterAll", [t.name for t in rc.body_tokens(lines, 1, len(lines))])

    def test_own_name_on_the_head_is_not_a_use(self):
        self.fake_ctags(fx.TAGS + [("object_path", "src/js/auth.js", 1, "function"),
                                   ("get", "src/js/auth.js", 1, "function")])
        code, out, _ = self.run_check(fx.LEDGERS["py"], "--index", "ctags")
        self.assertEqual(code, 0, out)

    def test_recursive_and_namesake_calls(self):
        lines = ["def get(self, k):", "    return self.cache.get(k) or get(k - 1)"]
        toks = {t.name: t for t in rc.body_tokens(lines, 1, 2, "get")}
        self.assertIn("get", toks)  # the uses after the head still count
        self.assertEqual(toks["get"].line, 2)

    def test_edge_to_a_whole_class_does_not_cover_its_methods(self):
        self.fake_ctags()
        src = "\n".join(["class Svc {", "  run() {", "    return 1;", "  }", "  helperA(x) {",
                          "    return x;", "  }", "}", "function entry(s) {", "  return s.helperA(1) + Svc;", "}"])
        self.write(os.path.join(self.root, "src", "js", "svc.js"), src + "\n")
        tags = fx.TAGS + [("Svc", "src/js/svc.js", 1, "class"), ("run", "src/js/svc.js", 2, "method"),
                          ("helperA", "src/js/svc.js", 5, "method"), ("entry", "src/js/svc.js", 9, "function")]
        self.fake_ctags(tags)
        ledger = ("## Seeds\n- `entry` `src/js/svc.js:9` — pass 1 — top-down\n\n## Read\n"
                  "### `entry` `src/js/svc.js:9-11`\n- `Svc` → `src/js/svc.js:1`\n"
                  "### `Svc` `src/js/svc.js:1-8`\n")
        code, out, _ = self.run_check(ledger, "--index", "ctags")
        self.assertEqual(code, 1, out)  # same-file member call: still blocking
        self.assertIn("uses `helperA`", out)


class RoundThreeCasesTest(Base):
    def test_body_line_edge_does_not_cover_the_next_function(self):
        self.write(os.path.join(self.root, "src", "py", "c.py"),
                   "def helper():\n    x = 1\n    return x\ndef other():\n    return 2\n")
        self.write(os.path.join(self.root, "src", "py", "a.py"), "def run():\n    return helper() + other()\n")
        self.fake_ctags(fx.TAGS + [("helper", "src/py/c.py", 1, "function", "()", 3),
                                   ("other", "src/py/c.py", 4, "function", "()", 5),
                                   ("run", "src/py/a.py", 1, "function", "()", 2)])
        ledger = ("## Seeds\n- `run` `src/py/a.py:1` — pass 1 — top-down\n\n## Read\n"
                  "### `run` `src/py/a.py:1-2`\n- `helper` → `src/py/c.py:2`\n### `helper` `src/py/c.py:1-3`\n")
        code, out, _ = self.run_check(ledger, "--index", "ctags")
        self.assertEqual(code, 1, out)
        self.assertIn("uses `other`", out)
        self.assertNotIn("uses `helper`", out)

    def test_decorator_with_the_own_name(self):
        toks = {t.name: t for t in rc.body_tokens(['@router.get("/x")', "def get(self):", "    return 1"], 1, 3, "get")}
        self.assertTrue(toks["get"].member_only)

    def test_apostrophe_in_an_inline_block_comment(self):
        toks = [t.name for t in rc.body_tokens(["x = 1; /* it's */ normalize_key(\"a'b\")"], 1, 1)]
        self.assertIn("normalize_key", toks)


class LedgerShapeTest(Base):
    def test_bad_edge_and_missing_file(self):
        ledger = fx.LEDGERS["js"] + "### `ghost` `src/js/nope.js:1-2`\n- `x` → somewhere\n"
        code, out, _ = self.run_check(ledger, "--index", "none")
        self.assertEqual(code, 1)
        self.assertIn("ledger_bad_edge", out)
        self.assertIn("ledger_file_missing", out)

    def test_ignored_needs_reason_and_lines_in_range(self):
        ledger = fx.LEDGERS["js"].replace("- `readFile` → external", "- `readFile` → ignored")
        ledger = ledger.replace("`src/js/auth.js:1-3`", "`src/js/auth.js:1-99`")
        code, out, _ = self.run_check(ledger, "--index", "none")
        self.assertEqual(code, 1)
        self.assertIn("ignored without a reason", out)
        self.assertIn("ledger_line_oob", out)

    def test_no_sections(self):
        code, out, _ = self.run_check("# nothing\n", "--index", "none")
        self.assertEqual(code, 1)
        self.assertIn("ledger_no_seeds_section", out)
        self.assertIn("ledger_no_read_section", out)

    def test_missing_ledger_is_exit_2(self):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = closure_check.main([self.report, "--root", self.root, "--index", "none"])
        self.assertEqual(code, 2)
        self.assertIn("cannot read the ledger", err.getvalue())

    def test_arrow_variants(self):
        ledger = fx.LEDGERS["go"].replace("→", "->")
        code, out, _ = self.run_check(ledger, "--index", "none")
        self.assertEqual(code, 0, out)


class TokensAndIndexTest(unittest.TestCase):
    def test_body_tokens_drop_comments_and_strings(self):
        lines = [
            "def f(a):",
            "    # helper_one is mentioned here",
            '    x = "helper_two"',
            "    y = calc(a)  # helper_three",
            '    """',
            "    helper_four in a docstring",
            '    """',
            "    return helper_five(x) // 2",
        ]
        toks = [t.name for t in rc.body_tokens(lines, 1, len(lines))]
        for name in ("helper_one", "helper_two", "helper_three", "helper_four"):
            self.assertNotIn(name, toks)
        self.assertIn("helper_five", toks)
        self.assertIn("calc", toks)

    def test_block_comments_interpolation_and_member_access(self):
        lines = [
            "function f(a) {",
            "  /* helperInBlock",
            "     still helperInBlock2 */ const z = realCall(a);",
            "  const s = `${tmplCall(a)}`;",
            '  const p = f"{bucket}/{pyInterp(key)}";',
            '  const r = "#{rubyInterp(x)}";',
            "  return obj.save(z) + $this->store(p) + Cls::make(r) + maybe?.get(s);",
            "  *ptr = derefHelper(x);",
            "}",
        ]
        toks = {t.name: t for t in rc.body_tokens(lines, 1, len(lines))}
        self.assertNotIn("helperInBlock", toks)
        self.assertNotIn("helperInBlock2", toks)
        for name in ("realCall", "tmplCall", "pyInterp", "rubyInterp", "derefHelper"):
            self.assertIn(name, toks)
            self.assertFalse(toks[name].member_only, name)
        for name in ("save", "store", "make", "get"):
            self.assertTrue(toks[name].member_only, name)

    def test_regex_definitions_across_languages(self):
        cases = {
            "function normalizeSegment(seg) {": "normalizeSegment",
            "export async function load(id) {": "load",
            "const toKey = (s) => s.trim();": "toKey",
            "  toKey: function (s) {": "toKey",
            "def normalize_key(key):": "normalize_key",
            "    async def fetch(self):": "fetch",
            "func normalizeID(id string) string {": "normalizeID",
            "func (l *Loader) Load(id string) string {": "Load",
            "    static String normalize(String id) {": "normalize",
            "    public static String userPath(String root, String id) {": "userPath",
            "  private fun clean(s: String): String {": "clean",
            "pub fn build_path(root: &str) -> String {": "build_path",
            "  def self.call(x)": "call",
            "    public function handle($request) {": "handle",
            "  buildPath(root, id) {": "buildPath",
            "type Loader struct{ Root string }": "Loader",
            "public class UserPaths {": "UserPaths",
        }
        for line, name in cases.items():
            with self.subTest(line=line):
                found = None
                for pat in rc.DEF_PATTERNS:
                    m = pat.match(line)
                    if m:
                        found = m.group("n").rstrip("!?")
                        break
                self.assertEqual(found, name)

    def test_regex_control_lines_are_not_definitions(self):
        for line in ("  if (x) {", "  } else if (y) {", "  for (const a of b) {", "  while (true) {",
                     "  switch (k) {", "  catch (e) {"):
            with self.subTest(line=line):
                names = [m.group("n") for m in (p.match(line) for p in rc.DEF_PATTERNS) if m]
                self.assertTrue(all(n in rc._CONTROL for n in names), names)

    def test_last_segment(self):
        self.assertEqual(rc.last_segment("os.path.join"), "join")
        self.assertEqual(rc.last_segment("App::Paths::build"), "build")
        self.assertEqual(rc.last_segment("Store#get"), "get")
        self.assertEqual(rc.last_segment("$this->save()"), "save")
        self.assertEqual(rc.last_segment("plain"), "plain")


if __name__ == "__main__":
    unittest.main()
