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
import re
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

    def run_check(self, ledger_text, *extra, report=None, tag=True):
        self.write(self.ledger, fx.tagged(ledger_text) if tag else ledger_text)
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

    def test_universal_ctags_later_on_path_is_found(self):
        first, second = os.path.join(self.tmp, "bin1"), os.path.join(self.tmp, "bin2")
        other = fx.write_fake_other_ctags(first)
        uni = fx.write_fake_ctags(second)
        os.environ["PATH"] = first + os.pathsep + second
        self.assertEqual(rc.ctags_candidates(), [other, uni])
        self.assertEqual(rc.universal_ctags(), uni)
        code, out, _ = self.run_check(fx.MISSING["go"], "--index", "auto")
        self.assertEqual(code, 1, out)
        self.assertIn("index: ctags index", out)
        self.assertIn(uni, out)
        self.assertIn("missed_ref `UserPath`", out)

    def test_other_ctags_names_are_tried(self):
        fx.write_fake_other_ctags(self.bin)
        uni = fx.write_fake_ctags(self.bin, name="uctags")
        os.environ["PATH"] = self.bin
        self.assertEqual(rc.universal_ctags(), uni)
        os.remove(uni)
        uni = fx.write_fake_ctags(self.bin, name="universal-ctags")
        self.assertEqual(rc.universal_ctags(), uni)

    def test_only_a_non_universal_ctags_falls_back_and_says_so(self):
        other = fx.write_fake_other_ctags(self.bin)
        os.environ["PATH"] = self.bin
        self.assertIsNone(rc.universal_ctags())
        code, out, _ = self.run_check(fx.MISSING["js"], "--index", "auto")
        self.assertEqual(code, 0, out)
        self.assertIn("index: regex index", out)
        self.assertIn("no Universal Ctags on PATH (checked: %s)" % other, out)
        code, _, err = self.run_check(fx.MISSING["js"], "--index", "ctags")
        self.assertEqual(code, 2)
        self.assertIn("Universal Ctags not found on PATH (checked: %s)" % other, err)

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
        self.assertIn("D0 `getProfile` src/js/handler.js:4 [other] — read in ledger", out)
        self.assertIn("D1 `buildUserPath` src/js/paths.js:7 [data] — read in ledger", out)
        self.assertIn("D1 `checkAccess` src/js/auth.js:1 [access] — read in ledger", out)
        self.assertIn("D2 `normalizeSegment` src/js/paths.js:3 [data] — leaf (depth 2)", out)
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

    def test_data_leaf_stays_in_with_no_budget(self):
        code, out, _ = self.run_check(fx.LEDGERS["js"], "--index", "none", "--budget-share", "0")
        self.assertEqual(code, 0, out)
        self.assertIn("items 4 (0 over budget)", out)
        self.assertIn("D2 `normalizeSegment` src/js/paths.js:3 [data] — leaf", out)
        other = fx.LEDGERS["js"].replace("`src/js/paths.js:3` [data]", "`src/js/paths.js:3`")
        code, out, _ = self.run_check(other, "--index", "none", "--budget-share", "0")
        self.assertIn("D2 `normalizeSegment` src/js/paths.js:3 [other] — not covered: over budget (3 lines)", out)

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
        self.assertIn("D1 `object_path` src/py/store.py:9 [data] — read in ledger", out)


SVC = "\n".join([
    "def entry(x):",                    # 1
    "    y = helper(x)",                # 2
    "    return y",                     # 3
    "",                                 # 4
    "def helper(x):",                   # 5
    "    a = tiny(x)",                  # 6
    "    b = large(x)",                 # 7
    "    c = key_path(x)",              # 8
    "    d = 1",                        # 9
    "    return a + b + c + d",         # 10
    "",                                 # 11
    "def tiny(x):",                     # 12
    "    return x",                     # 13
    "",                                 # 14
    "def large(x):",                    # 15
    "    x = x + 1",                    # 16
    "    x = x + 2",                    # 17
    "    x = x + 3",                    # 18
    "    x = x + 4",                    # 19
    "    return x",                     # 20
    "",                                 # 21
    "def key_path(x):",                 # 22
    '    p = "users/" + x',             # 23
    "    p = p.strip()",                # 24
    "    p = p.lower()",                # 25
    '    p = p.replace(" ", "")',       # 26
    '    p = p.replace("/", "_")',      # 27
    '    p = p + "!"',                  # 28
    "    q = p",                        # 29
    "    return q",                     # 30
]) + "\n"

SVC_LEDGER = """## Seeds
- `entry` `src/py/svc.py:1` — pass 1 — top-down [other]

## Read
### `entry` `src/py/svc.py:1-3` [other]
- `helper` → `src/py/svc.py:5`
### `helper` `src/py/svc.py:5-10` [other]
- `tiny` → `src/py/svc.py:12`
- `large` → `src/py/svc.py:15`
- `key_path` → `src/py/svc.py:22` [data]
"""


class BudgetTest(Base):
    def setUp(self):
        super().setUp()
        self.write(os.path.join(self.root, "src", "py", "svc.py"), SVC)

    def test_smallest_other_first_and_data_always_in(self):
        code, out, _ = self.run_check(SVC_LEDGER, "--index", "none")
        self.assertEqual(code, 0, out)
        self.assertIn("budget: depth-2 `other` items get 4 lines (0.50 × 9 depth<2 entry lines); used 2", out)
        self.assertIn("D2 `tiny` src/py/svc.py:12 [other] — leaf", out)
        self.assertIn("D2 `large` src/py/svc.py:15 [other] — not covered: over budget (6 lines)", out)
        self.assertIn("D2 `key_path` src/py/svc.py:22 [data] — leaf", out)
        code, out, _ = self.run_check(SVC_LEDGER, "--index", "none", "--budget-share", "2")
        self.assertIn("items 5 (0 over budget)", out)

    def test_access_tag_on_a_seed_wins_over_other(self):
        ledger = SVC_LEDGER.replace("- `entry` `src/py/svc.py:1` — pass 1 — top-down [other]",
                                    "- `entry` `src/py/svc.py:1` — pass 1 — top-down [other]\n"
                                    "- `large` `src/py/svc.py:15` — pass 1 — bottom-up [access]")
        ledger += "### `large` `src/py/svc.py:15-20` [access]\n"
        code, out, _ = self.run_check(ledger, "--index", "none")
        self.assertEqual(code, 0, out)
        self.assertIn("D0 `large` src/py/svc.py:15 [access] — read in ledger", out)

    def test_budget_sizes_come_from_ctags_ends(self):
        self.fake_ctags(fx.TAGS + [("entry", "src/py/svc.py", 1, "function", "(x)", 3),
                                   ("helper", "src/py/svc.py", 5, "function", "(x)", 10),
                                   ("tiny", "src/py/svc.py", 12, "function", "(x)", 20),
                                   ("large", "src/py/svc.py", 15, "function", "(x)", 16),
                                   ("key_path", "src/py/svc.py", 22, "function", "(x)", 30)])
        code, out, _ = self.run_check(SVC_LEDGER, "--index", "ctags")
        self.assertIn("D2 `tiny` src/py/svc.py:12 [other] — not covered: over budget (9 lines)", out)
        self.assertIn("D2 `large` src/py/svc.py:15 [other] — leaf", out)

    def test_role_is_required_on_seeds_and_entries(self):
        code, out, _ = self.run_check(SVC_LEDGER.replace(" [other]", ""), "--index", "none", tag=False)
        self.assertEqual(code, 1)
        self.assertEqual(out.count("ledger_no_role"), 3, out)


class ContainerTest(Base):
    LEDGER = """## Seeds
- `Store` `src/py/store.py:13` — pass 1 — bottom-up [container]

## Read
### `Store` `src/py/store.py:13-16` [container]
- `get` → `src/py/store.py:14` [data]
"""

    def test_container_members_are_items_of_their_own(self):
        code, out, _ = self.run_check(self.LEDGER, "--index", "none")
        self.assertEqual(code, 1, out)
        self.assertIn("D0 `Store` src/py/store.py:13 [container] — container: its members are the items", out)
        self.assertIn("not_read D0 `get` src/py/store.py:14", out)  # a member stands at its container's depth
        ledger = self.LEDGER + ("### `Store.get` `src/py/store.py:14-16` [data]\n"
                                "- `object_path` → `src/py/store.py:8`\n")
        code, out, _ = self.run_check(ledger, "--index", "none")
        self.assertIn("D0 `get` src/py/store.py:14 [data] — read in ledger", out)
        self.assertIn("not_read D1 `object_path` src/py/store.py:8", out)
        self.assertIn("(0.50 × 3 depth<2 entry lines)", out)  # the container's 4 lines are not counted

    def test_untagged_container_from_the_index(self):
        self.fake_ctags()
        ledger = self.LEDGER.replace("[container]", "[other]")
        code, out, _ = self.run_check(ledger, "--index", "ctags")
        self.assertIn("D0 `Store` src/py/store.py:13 [container]", out)
        self.assertIn("not_read D0 `get` src/py/store.py:14", out)
        code, out, _ = self.run_check(ledger, "--index", "none")  # no index, no tag: the old whole-body entry
        self.assertEqual(code, 0, out)
        self.assertNotIn("`get`", out.split("closure-check")[0].split("index:")[1])

    def test_container_without_entry_blocks_until_excluded(self):
        ledger = "## Seeds\n- `Store` `src/py/store.py:13` — pass 1 — bottom-up [container]\n\n## Read\n"
        code, out, _ = self.run_check(ledger, "--index", "none")
        self.assertEqual(code, 1, out)
        self.assertIn("container_no_entry D0 `Store` src/py/store.py:13", out)
        report = "## Coverage\n- `Store` `src/py/store.py:13` — excluded — a plain record, no behaviour\n"
        code, out, _ = self.run_check(ledger, "--index", "none", report=report)
        self.assertEqual(code, 0, out)

    def test_container_at_the_last_depth_still_reaches_its_members(self):
        ledger = ("## Seeds\n- `Store.get` `src/py/store.py:14` — pass 1 — top-down [data]\n\n## Read\n"
                  "### `Store.get` `src/py/store.py:14-16` [data]\n- `object_path` → `src/py/store.py:8` [data]\n"
                  "### `object_path` `src/py/store.py:8-10` [data]\n- `Store` → `src/py/store.py:13` [container]\n"
                  "### `Store` `src/py/store.py:13-16` [container]\n- `normalize_key` → `src/py/store.py:4` [data]\n")
        code, out, _ = self.run_check(ledger, "--index", "none")
        self.assertEqual(code, 0, out)
        self.assertIn("D2 `Store` src/py/store.py:13 [container]", out)
        self.assertIn("D2 `normalize_key` src/py/store.py:4 [data] — leaf", out)


class ClosureOrderTest(Base):
    def test_container_member_depth_does_not_depend_on_edge_order(self):
        self.write(os.path.join(self.root, "src", "py", "c.py"),
                   "def x():\n    return C().m()\n\nclass C:\n    def m(self):\n        return 1\n\n"
                   "def s():\n    x()\n    return C()\n")
        base = ("## Seeds\n- `s` `src/py/c.py:8` — pass 1 — top-down [other]\n\n## Read\n"
                "### `s` `src/py/c.py:8-10` [other]\n%s\n"
                "### `x` `src/py/c.py:1-2` [other]\n- `C.m` → `src/py/c.py:5`\n"
                "### `C` `src/py/c.py:4-6` [container]\n- `m` → `src/py/c.py:5`\n")
        edges = ["- `x` → `src/py/c.py:1`", "- `C` → `src/py/c.py:4` [container]"]
        outs = []
        for order in (edges, edges[::-1]):
            code, out, _ = self.run_check(base % "\n".join(order), "--index", "none")
            lines = [re.sub(r"`[^`]+` ", "", l) for l in out.splitlines() if l.startswith(("D", "not_read"))]
            outs.append((code, sorted(lines)))  # the symbol is the name of the edge seen first
        self.assertEqual(outs[0], outs[1])
        self.assertIn("not_read D1 src/py/c.py:5 — no ledger entry and not excluded", outs[0][1])

    def test_planned_exclusions_in_the_ledger(self):
        head, tail = fx.LEDGERS["js"].split("### `buildUserPath`")
        ledger = head + "### `checkAccess`" + tail.split("### `checkAccess`")[1]
        ledger += "\n## Excluded\n- `buildUserPath` `src/js/paths.js:7` — generated code\n"
        code, out, _ = self.run_check(ledger, "--index", "none")
        self.assertEqual(code, 0, out)
        self.assertIn("D1 `buildUserPath` src/js/paths.js:7 [data] — excluded", out)
        code, out, _ = self.run_check(ledger + "- `x` no reference\n", "--index", "none")
        self.assertIn("ledger_bad_exclusion", out)
        code, out, _ = self.run_check(ledger.replace("— generated code", "- generated code") +
                                      "- `y` `src/js/paths.js:6` – a blank line\n", "--index", "none")
        self.assertNotIn("ledger_bad_exclusion", out)
        self.assertIn("advisory excluded_not_in_closure", out)


class SeedKindTest(unittest.TestCase):
    def test_seed_kinds_and_reasons(self):
        ledger = rc.parse_ledger("""## Seeds
- `a` `x.py:1` — pass 1 — duplicate of the key rule [data]
- `b` `x.py:2` — pass 2 — caller of `save` — behaviour changes [other]
- `c` `x.py:3` — pass 1 — sibling of `load` [data]
- `d` `x.py:4` — pass 1 — test infra [other]
- `e` `x.py:5` — pass 1 — facet 9 [other]
- `f` `x.py:6` — pass 1 — facet 8 [other]
- `g` `x.py:7` — pass 1 — top-down [access]

## Read
""")
        self.assertEqual([s.kind for s in ledger.seeds],
                         ["duplicate", "caller", "sibling", "test infra", "duplicate", "test infra", ""])
        self.assertEqual(ledger.seeds[1].source, "caller of `save` — behaviour changes")
        self.assertEqual(ledger.seeds[6].role, "access")
        self.assertEqual(ledger.problems, [])

    def test_role_inside_a_code_span_is_not_a_tag(self):
        self.assertEqual(rc.role_tag("### `arr[data]` `x.py:1-2`"), "")
        self.assertEqual(rc.role_tag("### `arr[data]` `x.py:1-2` [Data]"), "data")


class BodyEndTest(unittest.TestCase):
    def test_language_neutral_end_rule(self):
        cases = [
            (["function f(a) {", "  if (a) { return 1; }", '  return "}";', "}", "x"], (4, "brace")),
            (["function f({a, b}) {", "  return a;", "}"], (3, "brace")),
            (["def f(x={}) -> dict:", "    y = {1: 2}", "    return y", "", "def g():"], (3, "indent")),
            (["def foo(a)", "  a + 1", "end", "def bar; end"], (3, "indent")),
            (["type Loader struct{ Root string }", "func x() {"], (1, "brace")),
            (["const f = (x) => x.trim();", "const g = 1;"], (1, "line")),
            (["fun f(x: Int) = x + 1", "fun g() {}"], (1, "line")),
            (["public static String userPath(", "    String root,", "    String id) {", "  return root;", "}"],
             (5, "brace")),
            (["function f() {", "  const s = `}`; // }", "  /* } */", "  return 1;", "}"], (5, "brace")),
            (["function f() {", "  return 1;"], (2, "uncertain")),
            (["public int Get(int a)", "{", "    return a;", "}", "x"], (4, "brace")),            # Allman, C, C#
            (["    public function x()", "    {", "        return 1;", "    }"], (4, "brace")),  # PHP PSR-12
            (["fn f<T>(a: T) -> T", "where", "    T: Clone,", "{", "    a", "}"], (6, "brace")),
            (["def c():", '    q = """', "SELECT *", "FROM t", '"""', "# note", "    return q", "", "def d():"],
             (7, "indent")),
            (["def f(x)", "# only a comment", "y = 1"], (1, "line")),
            (["def run(x) do", "  {a, b} = split(x)", "  combine(a, b)", "end"], (4, "indent")),  # a body `{`
            (["def config", "  { a: 1,", "  }.merge(other_call)", "  more_call", "end"], (5, "indent")),
            (["abstract fun foo(): Int", "fun bar(): Int", "{", "  1", "}"], (1, "line")),
            (["def f(self):", '    """Doc', '    more."""'], (3, "indent")),
            (["def f():", '    return """', "text", '"""'], (4, "indent")),
            (["Foo::Foo(int a)", "    : a_{a}, b_{0}", "{", "  x();", "}"], (5, "brace")),
            (["type ID string", "// Foo does x", "func Foo() {}"], (1, "line")),
        ]
        for lines, want in cases:
            with self.subTest(head=lines[0]):
                self.assertEqual(rc.body_end(lines, 1), want)

    def test_item_end_prefers_the_index(self):
        idx = rc.Index("ctags", {}, "", {("/x", 1): 9})
        self.assertEqual(rc.item_end("/x", 1, idx), (9, "ctags"))


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
        self.assertIn("items 4 (0 over budget)", out)
        self.assertIn("D1 `buildUserPath` src/js/paths.js:8 [data] — read in ledger", out)

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
