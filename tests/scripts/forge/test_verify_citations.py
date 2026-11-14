#!/usr/bin/env python3
"""Tests for scripts/forge/verify_citations.py and its shared module scripts/forge/spec_refs.py (stdlib unittest).

Each test builds a throwaway project dir with invented source files and a gate report or spec. All data is invented.

Run: python3 -m unittest discover -s tests/scripts/forge -p 'test_verify_citations.py' -v
"""
from __future__ import annotations

import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SCRIPTS = os.path.join(REPO, "scripts", "forge")
sys.path.insert(0, SCRIPTS)
import spec_refs  # noqa: E402
import verify_citations as vc  # noqa: E402

WIDGET = "\n".join([
    "class Widget:",              # 1
    "    def spin(self, rate):",  # 2
    "        return rate * 2",    # 3
    "",                           # 4
    "    def stop(self):",        # 5
    "        self.rate = 0",      # 6
    '        say("hi there")',    # 7
    "        return None",        # 8
]) + "\n"


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.root = os.path.join(self.tmp, "proj")
        self.write("src/widget.py", WIDGET)
        spec_refs._WALK_CACHE.clear()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def write(self, rel, text):
        path = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        return path

    def run_main(self, mode, path):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = vc.main([mode, path, "--root", self.root])
        return code, out.getvalue(), err.getvalue()

    def report(self, body, name="spec-gate"):
        return self.write("specs/f1/gates/%s.md" % name, body)

    def lines(self, text):
        return text.rstrip("\n").split("\n")


class ParseTests(unittest.TestCase):
    def cites(self, text):
        return list(spec_refs.iter_citations(text))

    def test_code_span_quote_with_separators(self):
        for sep in (" — ", " – ", " - ", ": ", " "):
            c = self.cites("see `a/b.py:3`%s`return rate`" % sep)
            self.assertEqual((c[0].path, c[0].start, c[0].end, c[0].quote), ("a/b.py", 3, None, "return rate"), sep)

    def test_double_and_curly_quotes(self):
        self.assertEqual(self.cites('`a.py:3` — "x y"')[0].quote, "x y")
        self.assertEqual(self.cites("`a.py:3` — “x y”")[0].quote, "x y")

    def test_quote_with_double_quote_in_code_span(self):
        c = self.cites('`a.py:7` — `say("hi there")`')
        self.assertEqual(c[0].quote, 'say("hi there")')

    def test_double_backtick_span(self):
        c = self.cites("`a.py:2-3` — `` x = `y` ``")
        self.assertEqual(c[0].quote, "x = `y`")
        self.assertEqual(c[0].end, 3)

    def test_unclosed_run_is_literal(self):
        self.assertEqual(self.cites("`a.py:3` — ``oops`"), [spec_refs.Citation(1, "a.py", 3, None, None, True)])

    def test_unquoted_and_non_citations(self):
        c = self.cites("`a.py:3` and `localhost:3000` and `:12` and `plain`")
        self.assertEqual([x.path for x in c], ["a.py"])
        self.assertIsNone(c[0].quote)

    def test_backslash_escaped_backtick_is_literal(self):
        self.assertEqual(self.cites("\\`a.py:3` `return rate * 2`"), [])

    def test_url_is_not_a_citation(self):
        self.assertEqual(self.cites("`http://x.com/a.py:3` `return rate * 2`"), [])

    def test_unquoted_shapes(self):
        c = self.cites("`localhost:3000` and `127.0.0.1:80` and `HH:30` and `Makefile:3` and `a/b:4` and `main.py:5`")
        self.assertEqual([x.path for x in c], ["a/b", "main.py"])
        c = self.cites("`Makefile:3` — `all: build`")
        self.assertEqual((c[0].path, c[0].quote), ("Makefile", "all: build"))

    def test_escaped_pipe_in_quote(self):
        self.assertEqual(self.cites("| `a.py:3` — `x \\| y` |")[0].quote, "x | y")
        self.assertEqual(self.cites("  | `a.py:3` — `x \\| y` |")[0].quote, "x | y")
        # outside a table row the backslash stays: a shell quote
        self.assertEqual(self.cites("`a.py:3` — `grep 'foo\\|bar' file.txt`")[0].quote, "grep 'foo\\|bar' file.txt")

    def test_unclosed_run_after_span_flagged(self):
        c = self.cites("`a.py:3` — `oops")
        self.assertTrue(c[0].unclosed)
        self.assertFalse(self.cites("`a.py:3` and later `x`")[0].unclosed)

    def test_fence_info_string_and_closing_rules(self):
        fu = spec_refs.fence_update
        self.assertEqual(fu(None, "```python"), "```")
        self.assertIsNone(fu(None, "```not `a` fence"))  # a backtick fence's info string has no backtick
        self.assertEqual(fu(None, "~~~ a `b`"), "~~~")
        self.assertEqual(fu("```", "``` trailing"), "```")  # trailing text: not a closer
        self.assertIsNone(fu("```", "```   "))
        self.assertEqual(fu("```", "~~~"), "```")

    def test_fence_closes_only_on_long_enough_run(self):
        text = "````\n## not\n```\n## still not\n````\n## Real\nx\n"
        self.assertEqual([s.title for s in spec_refs.split_sections(text)], ["", "Real"])
        self.assertEqual([s.title for s in spec_refs.split_sections("   ## Indented\nx\n    ## Code\n")], ["Indented"])

    def test_line_numbers(self):
        c = self.cites("x\n\n`a.py:1` `not a quote at all`\n")
        self.assertEqual(c[0].line, 3)

    def test_split_sections(self):
        text = "intro\n## One\na\n```\n## not\n```\n## Two\nb\n"
        secs = spec_refs.split_sections(text)
        self.assertEqual([(s.title, s.line, s.first) for s in secs], [("", 0, 1), ("One", 2, 3), ("Two", 7, 8)])
        self.assertIn("## not", secs[1].body)


class QuoteTests(unittest.TestCase):
    L = WIDGET.split("\n")[:-1]

    def check(self, start, end, quote):
        return spec_refs.check_quote(self.L, start, end, quote)

    def test_range_is_inside_window(self):
        self.assertIsNone(self.check(2, 3, "return rate * 2"))
        self.assertIsNone(self.check(2, 3, "def spin(self, rate): return"))  # whitespace-normalised, spans lines
        self.assertEqual(self.check(2, 3, "self.rate = 0"), spec_refs.REASON_QUOTE_MISMATCH)

    def test_single_line_starts_on_n_and_runs_on(self):
        self.assertIsNone(self.check(2, None, "def spin(self, rate): return rate * 2"))
        # "def spin(self" is on line 2 only: a single `path:3` needs the quote to START on line 3
        self.assertEqual(self.check(3, None, "def spin(self"), spec_refs.REASON_QUOTE_MISMATCH)
        self.assertEqual(self.check(4, None, "def stop(self)"), spec_refs.REASON_QUOTE_MISMATCH)  # blank line N

    def test_single_line_window_is_50_lines(self):
        lines = ["start here"] + ["filler"] * 60 + ["far away"]
        self.assertIsNone(spec_refs.check_quote(lines, 1, None, "start here filler"))
        self.assertEqual(spec_refs.check_quote(lines, 1, None, "start here far away"), spec_refs.REASON_QUOTE_MISMATCH)

    def test_ellipsis_fragments_in_order(self):
        self.assertIsNone(self.check(1, 8, "class Widget: … return None"))
        self.assertIsNone(self.check(1, 8, "class Widget: ... def stop"))
        self.assertEqual(self.check(1, 8, "return None … class Widget:"), spec_refs.REASON_QUOTE_MISMATCH)
        self.assertEqual(self.check(1, 3, "class Widget: … return None"), spec_refs.REASON_QUOTE_MISMATCH)

    def test_repeated_fragment_needs_two_occurrences(self):
        lines = ["one spin only here"]
        self.assertEqual(spec_refs.check_quote(lines, 1, 1, "spin … spin"), spec_refs.REASON_QUOTE_MISMATCH)
        self.assertIsNone(spec_refs.check_quote(["spin and spin"], 1, 1, "spin … spin"))

    def test_window_boundary_lines_50_and_51(self):
        lines = ["start here"] + ["filler"] * 48 + ["alpha-in", "omega-out"]  # lines 50 and 51
        self.assertIsNone(spec_refs.check_quote(lines, 1, None, "start here … alpha-in"))
        self.assertEqual(spec_refs.check_quote(lines, 1, None, "start here … omega-out"), spec_refs.REASON_QUOTE_MISMATCH)

    def test_leading_and_trailing_ellipsis_dropped(self):
        self.assertIsNone(self.check(2, 3, "... return rate * 2"))
        self.assertIsNone(self.check(2, 3, "def spin(self, rate): …"))
        self.assertEqual(self.check(2, 3, "… ..."), spec_refs.REASON_QUOTE_EMPTY)

    def test_ellipsis_without_spaces_literal_then_gap(self):
        lines = ["call spin(...) now", "other(111, 222)"]
        self.assertIsNone(spec_refs.check_quote(lines, 1, None, "call spin(...) now"))  # literal
        self.assertIsNone(spec_refs.check_quote(lines, 2, None, "other(...222)"))  # gap retry
        self.assertEqual(spec_refs.check_quote(lines, 2, None, "other(...999)"), spec_refs.REASON_QUOTE_MISMATCH)

    def test_gap_retry_needs_long_fragments(self):
        self.assertEqual(spec_refs.check_quote(["a e e e"], 1, None, "a...e...e...e"), spec_refs.REASON_QUOTE_TOO_SHORT)
        # tiny gap fragments are dropped, the rest is matched
        self.assertIsNone(spec_refs.check_quote(["def spin(self, n):"], 1, None, "def spin(...):"))
        self.assertEqual(spec_refs.check_quote(["def other(self, n):"], 1, None, "def spin(...):"), spec_refs.REASON_QUOTE_MISMATCH)

    def test_min_quote_chars_boundary(self):
        lines = ["abcdefgh ijk"]
        self.assertEqual(spec_refs.check_quote(lines, 1, None, "abcdefg"), spec_refs.REASON_QUOTE_TOO_SHORT)  # 7
        self.assertIsNone(spec_refs.check_quote(lines, 1, None, "abcdefgh"))  # 8
        self.assertEqual(spec_refs.MIN_QUOTE_CHARS, 8)

    def test_too_short(self):
        for q in ("rate", "def x", "return rate … ab"):
            self.assertEqual(self.check(1, 8, q), spec_refs.REASON_QUOTE_TOO_SHORT, q)
        self.assertIsNone(self.check(1, 8, "return rate"))

    def test_range_too_wide(self):
        self.assertIsNone(spec_refs.check_lines(1000, 1, 301))
        self.assertEqual(spec_refs.check_lines(1000, 1, 302), spec_refs.REASON_RANGE_TOO_WIDE)

    def test_ellipsis_without_spaces_is_literal(self):
        self.assertEqual(self.check(1, 8, "class…Widget"), spec_refs.REASON_QUOTE_MISMATCH)

    def test_empty_quotes(self):
        for q in ("", "   ", "..."):
            self.assertEqual(self.check(1, 8, q), spec_refs.REASON_QUOTE_EMPTY, repr(q))

    def test_check_lines(self):
        self.assertIsNone(spec_refs.check_lines(8, 8, None))
        for s, e in ((0, None), (9, None), (3, 2), (5, 9)):
            self.assertEqual(spec_refs.check_lines(8, s, e), spec_refs.REASON_LINE_OOB)


class ResolveTests(Base):
    def test_direct_and_missing(self):
        self.assertEqual(spec_refs.resolve("src/widget.py", self.root), [os.path.join(self.root, "src/widget.py")])
        self.assertEqual(spec_refs.resolve("src/none.py", self.root), [])

    def test_basename_unique_suffix(self):
        self.assertEqual(spec_refs.resolve("widget.py", self.root), [os.path.join(self.root, "src/widget.py")])

    def test_ambiguous_suffix(self):
        self.write("other/widget.py", "x\n")
        self.assertEqual(len(spec_refs.resolve("widget.py", self.root)), 2)

    def test_suffix_needs_a_path_boundary(self):
        self.write("src/mywidget.py", "x\n")
        self.assertEqual(spec_refs.resolve("widget.py", self.root), [os.path.join(self.root, "src/widget.py")])

    def test_dot_slash_prefix(self):
        self.assertEqual(spec_refs.resolve("./src/widget.py", self.root), [os.path.join(self.root, "src/widget.py")])

    def test_source_root_hit_is_final_despite_twin(self):
        self.write("app/core/engine.py", "x\n")
        self.write("other/core/engine.py", "x\n")
        self.write(".claude/project-config.json", json.dumps({"SOURCE_ROOT": "app"}))
        self.assertEqual(spec_refs.resolve("core/engine.py", self.root), [os.path.join(self.root, "app/core/engine.py")])

    def test_cr_line_endings(self):
        for sep in ("\r", "\r\n"):
            path = self.write("src/cr.py", sep.join(["a = 1", "b = 2", "c = 3"]) + sep)
            self.assertEqual(spec_refs.read_lines(path), ["a = 1", "b = 2", "c = 3"])

    def test_inside_is_a_path_boundary_check(self):
        self.assertTrue(spec_refs._inside("/root/a", "/root"))
        self.assertTrue(spec_refs._inside("/root", "/root"))
        self.assertFalse(spec_refs._inside("/root-other/a", "/root"))

    def test_symlink_out_of_root_dropped(self):
        outside = os.path.join(self.tmp, "outside.py")
        with open(outside, "w") as handle:
            handle.write("x\n")
        os.symlink(outside, os.path.join(self.root, "src", "link.py"))
        self.assertEqual(spec_refs.resolve("src/link.py", self.root), [])
        self.assertEqual(spec_refs.resolve("link.py", self.root), [])

    def test_more_pruned_dirs_and_git_file(self):
        for d in (".venv", "venv", "target", ".tox"):
            self.write("%s/lib_%s.py" % (d, d.strip(".")), "x\n")
            self.assertEqual(spec_refs.resolve("lib_%s.py" % d.strip("."), self.root), [], d)
        spec_refs._WALK_CACHE.clear()
        self.write("wt/.git", "gitdir: elsewhere\n")
        self.write("wt/inwt.py", "x\n")
        self.write("nested/.git/HEAD", "ref\n")
        self.write("nested/innested.py", "x\n")
        self.assertEqual(spec_refs.resolve("inwt.py", self.root), [])
        self.assertEqual(len(spec_refs.resolve("innested.py", self.root)), 1)

    def test_pruned_dirs_not_searched(self):
        self.write("node_modules/pkg/lib.py", "x\n")
        self.write(".git/hooks/lib2.py", "x\n")
        self.assertEqual(spec_refs.resolve("lib.py", self.root), [])
        self.assertEqual(spec_refs.resolve("lib2.py", self.root), [])

    def test_source_root(self):
        self.write("app/core/engine.py", "x\n")
        self.write(".claude/project-config.json", json.dumps({"SOURCE_ROOT": "app"}))
        self.assertEqual(spec_refs.resolve("core/engine.py", self.root), [os.path.join(self.root, "app/core/engine.py")])

    def test_broken_source_root_is_no_source_root(self):
        self.write(".claude/project-config.json", json.dumps({"SOURCE_ROOT": "nowhere"}))
        self.assertEqual(len(spec_refs.resolve("widget.py", self.root)), 1)  # suffix search still works
        self.write(".claude/project-config.json", "not json")
        self.assertEqual(spec_refs.resolve("src/widget.py", self.root), [os.path.join(self.root, "src/widget.py")])

    def test_ambiguous_passes_when_any_candidate_passes(self):
        self.write("other/widget.py", "different\n" * 8)
        cit = spec_refs.Citation(1, "widget.py", 3, None, "return rate * 2")
        reason, cands = spec_refs.verify_citation(cit, self.root)
        self.assertIsNone(reason)
        self.assertEqual(len(cands), 2)


class ReportTests(Base):
    def run_report(self, body):
        code, out, _err = self.run_main("report", self.report(body))
        return code, self.lines(out)

    def test_clean_report(self):
        code, out = self.run_report(
            "## Warning\n\n### W-1 title\n- `src/widget.py:3` — `return rate * 2`\n\n## Dispositions\n- W-1: fixed\n")
        self.assertEqual((code, out), (0, ["citations: 1 checked, 0 failed"]))

    def test_each_fail_reason(self):
        code, out = self.run_report(
            "## Critical\n### C-1 a\n- `nope/x.py:3` — `not a quote at all`\n"
            "### C-2 b\n- `src/widget.py:99` — `not a quote at all`\n"
            "### C-3 c\n- `src/widget.py:3` — `not there at all`\n"
            "### C-4 d\n- `src/widget.py:3` — `...`\n"
            "### C-5 e\n- `src/widget.py:3` is cited without a quote\n")
        self.assertEqual(code, 1)
        self.assertEqual(out, [
            "C-1 file_missing nope/x.py:3",
            "C-2 line_oob src/widget.py:99",
            "C-3 quote_mismatch src/widget.py:3",
            "C-4 quote_empty src/widget.py:3",
            "C-5 no_quoted_citation -",
            "citations: 5 checked, 5 failed",
        ])

    def test_finding_without_any_citation(self):
        code, out = self.run_report("## Warning\n### W-1 a\nno evidence here\n")
        self.assertEqual((code, out[0]), (1, "W-1 no_quoted_citation -"))

    def test_floor_under_suggestion(self):
        code, out = self.run_report(
            "## Suggestion\n### S-1 [security-floor] leak\n- `src/widget.py:3` — `return rate * 2`\n")
        self.assertEqual((code, out[0]), (1, "S-1 floor_in_suggestion -"))

    def test_floor_under_warning_is_fine(self):
        code, _ = self.run_report("## Warning\n### W-1 [security-floor] x\n- `src/widget.py:3` — `return rate * 2`\n")
        self.assertEqual(code, 0)

    def test_floor_disposition_needs_verified_citation(self):
        body = ("## Warning\n### W-1 [security-floor] x\n- `src/widget.py:3` — `return rate * 2`\n\n## Dispositions\n"
                "- W-1: rejected — it is fine\n")
        code, out = self.run_report(body)
        self.assertEqual((code, out[0]), (1, "W-1 floor_disposition_unverified -"))
        code, out = self.run_report(body.replace("it is fine", "see `src/widget.py:6` — `self.rate = 0`"))
        self.assertEqual(code, 0)
        code, out = self.run_report(body.replace("it is fine", "see `src/widget.py:6` — `nothing like it`"))
        self.assertEqual(code, 1)
        self.assertEqual(out[0], "W-1 quote_mismatch src/widget.py:6")
        self.assertIn("W-1 floor_disposition_unverified -", out)

    def test_floor_disposition_continuation_line_and_other_words(self):
        body = ("## Warning\n### W-1 [security-floor] x\n- `src/widget.py:3` — `return rate * 2`\n\n## Dispositions\n"
                "- W-1: deferred — later\n  evidence: `src/widget.py:8` — `return None`\n")
        self.assertEqual(self.run_report(body)[0], 0)
        self.assertEqual(self.run_report(body.replace("deferred", "fixed").replace("  evidence", "  note"))[0], 0)

    def test_recheck_citations_attributed_to_id(self):
        code, out = self.run_report(
            "## Warning\n### W-1 a\n- `src/widget.py:3` — `return rate * 2`\n\n## Re-check\n### W-1: still open\n"
            "- `src/widget.py:3` — `nothing like it`\n")
        self.assertEqual((code, out[0]), (1, "W-1 quote_mismatch src/widget.py:3"))

    def test_one_good_one_bad_citation(self):
        code, out = self.run_report(
            "## Warning\n### W-1 a\n- `src/widget.py:3` — `return rate * 2`\n- `src/widget.py:6` — `no such text`\n")
        self.assertEqual(out, ["W-1 quote_mismatch src/widget.py:6", "citations: 2 checked, 1 failed"])

    def test_unquoted_citation_in_finding_is_range_checked(self):
        code, out = self.run_report(
            "## Warning\n### W-1 a\n- `src/widget.py:3` — `return rate * 2`\n- also `src/widget.py:99`, `gone/x.py:1`\n")
        self.assertEqual(out[:2], ["W-1 line_oob src/widget.py:99", "W-1 file_missing gone/x.py:1"])

    def test_quote_unclosed(self):
        code, out = self.run_report("## Warning\n### W-1 a\n- `src/widget.py:3` — `return rate\n")
        self.assertIn("W-1 quote_unclosed src/widget.py:3", out)
        self.assertIn("W-1 no_quoted_citation -", out)

    def test_finding_not_heading_and_no_findings(self):
        code, out = self.run_report("## Warning\n### W-1 a\n- `src/widget.py:3` — `return rate * 2`\n- **W-2** bullet\n")
        self.assertEqual(out[0], "W-2 finding_not_heading -")
        code, out = self.run_report("## Critical\n#### C-1 deep\n- `src/widget.py:3` — `return rate * 2`\n")
        self.assertIn("C-1 finding_not_heading -", out)
        code, out = self.run_report("### Critical\n#### C-1 deep\n")
        self.assertEqual(out, ["C-1 finding_not_heading -", "report no_findings_parsed -", "citations: 0 checked, 2 failed"])
        code, out = self.run_report("# Gate\n**Result**: C0 W0 S0.\n")
        self.assertEqual((code, out), (0, ["citations: 0 checked, 0 failed"]))
        code, out = self.run_report("# Gate\nnothing\n")
        self.assertEqual((code, out[0]), (1, "report no_findings_parsed -"))

    def test_duplicate_id_ors_floor_flag(self):
        code, out = self.run_report(
            "## Warning\n### W-1 [security-floor] a\n- `src/widget.py:3` — `return rate * 2`\n"
            "## Suggestion\n### W-1 plain\n- `src/widget.py:3` — `return rate * 2`\n"
            "## Dispositions\n- W-1: rejected — nope\n")
        self.assertEqual(out[:2], ["W-1 duplicate_id -", "W-1 floor_disposition_unverified -"])

    def test_floor_tag_case_insensitive(self):
        code, out = self.run_report(
            "## Suggestion\n### S-1 [Security-Floor] a\n- `src/widget.py:3` — `return rate * 2`\n")
        self.assertEqual(out[0], "S-1 floor_in_suggestion -")

    FLOOR = "## Warning\n### W-1 [security-floor] x\n- `src/widget.py:3` — `return rate * 2`\n\n## Dispositions\n"

    def test_last_disposition_decides(self):
        cite = "see `src/widget.py:6` — `self.rate = 0`"
        code, out = self.run_report(self.FLOOR + "- W-1: rejected — no\n- W-1: rejected — " + cite + "\n")
        self.assertEqual(code, 0)
        code, out = self.run_report(self.FLOOR + "- W-1: rejected — " + cite + "\n- W-1: rejected — no\n")
        self.assertEqual(out[0], "W-1 floor_disposition_unverified -")

    def test_floor_disposition_citation_must_be_in_cited_file(self):
        self.write("src/other.py", "something quotable here\n")
        code, out = self.run_report(self.FLOOR + "- W-1: rejected — `src/other.py:1` — `something quotable`\n")
        self.assertEqual(out[0], "W-1 floor_disposition_unverified -")

    def test_floor_disposition_grouped_backticked_and_words(self):
        cite = " — `src/widget.py:6` — `self.rate = 0`"
        body = ("## Warning\n### W-1 [security-floor] x\n- `src/widget.py:3` — `return rate * 2`\n"
                "### W-2 [security-floor] y\n- `src/widget.py:3` — `return rate * 2`\n\n## Dispositions\n")
        self.assertEqual(self.run_report(body + "- W-1, W-2: rejected" + cite + "\n")[0], 0)
        self.assertEqual(self.run_report(body + "- `W-1`, `W-2`: deferred" + cite + "\n")[0], 0)
        code, out = self.run_report(body + "- W-1, W-2: rejected but also accepted\n")
        self.assertEqual(out[:2], ["W-1 floor_disposition_unverified -", "W-2 floor_disposition_unverified -"])
        self.assertEqual(self.run_report(body + "- W-1, W-2: accepted — rejected later\n")[0], 0)  # word before the dash

    def test_floor_disposition_unparsed(self):
        code, out = self.run_report(self.FLOOR + "W-1 was rejected, see notes\n")
        self.assertEqual(out[0], "W-1 floor_disposition_unparsed -")
        code, out = self.run_report(self.FLOOR + "- W-1: see notes\n")
        self.assertEqual(out[0], "W-1 floor_disposition_unparsed -")

    def test_disposition_word_is_the_first_token(self):
        for text in ("not fixed — recorded for later", "will be fixed in /plan; recorded — later", "fixed? no: rejected — fine"):
            code, out = self.run_report(self.FLOOR + "- W-1: " + text + "\n")
            self.assertEqual(out[0], "W-1 floor_disposition_unparsed -", text)
        for text in ("**rejected** — fine", "`recorded` later"):
            code, out = self.run_report(self.FLOOR + "- W-1: " + text + "\n")
            self.assertEqual(out[0], "W-1 floor_disposition_unverified -", text)
        self.assertEqual(self.run_report(self.FLOOR + "- W-1: fixed — done\n")[0], 0)

    def test_text_before_first_heading_in_severity_section(self):
        good = "### W-1 a\n- `src/widget.py:3` — `return rate * 2`\n"
        for pre in ("1. W-1 numbered", "+ W-1 plus", "| W-1 | table |", "- an id-less bullet", "free prose"):
            code, out = self.run_report("## Warning\n" + pre + "\n" + good)
            self.assertEqual(out[0], "report finding_not_heading -", pre)
        for pre in ("", "None", "None.", "\n"):
            code, out = self.run_report("## Warning\n" + pre + "\n" + good)
            self.assertEqual(code, 0, repr(pre))
        # once per section even with several lines
        code, out = self.run_report("## Warning\nfoo\nbar\n" + good)
        self.assertEqual(out.count("report finding_not_heading -"), 1)

    def test_id_heading_in_a_non_finding_section(self):
        good = "## Warning\n### W-1 a\n- `src/widget.py:3` — `return rate * 2`\n"
        code, out = self.run_report(good + "## Checked and passing\n### W-9 nothing\n")
        self.assertEqual(out[0], "W-9 finding_not_heading -")
        code, out = self.run_report("# t\n**Result**: C0 W0 S0\n## Notes\n### C-1 oops\n")
        self.assertEqual(out[0], "C-1 finding_not_heading -")  # C0 W0 S0 does not excuse it
        code, out = self.run_report(good + "## Re-check\n### W-1: still open\n")
        self.assertEqual(code, 0)

    def test_finding_line_in_a_non_finding_section(self):
        code, out = self.run_report("## Critical\nNone.\n## Other notes\n- **W-1** [security-floor] a leak\n")
        self.assertEqual(out[0], "W-1 finding_not_heading -")
        # dispositions and re-check keep their own id lines
        code, out = self.run_report("## Critical\nNone.\n## Dispositions\n- C-1: fixed\n")
        self.assertEqual(code, 0)

    def test_finding_line_forms_after_a_heading(self):
        good = "## Suggestion\n### S-1 a\n- `src/widget.py:3` — `return rate * 2`\n"
        for line in ("1. **S-2 [security-floor]** numbered", "2) **S-2** numbered", "+ S-2 plus", "**S-2** bold alone"):
            code, out = self.run_report(good + line + "\n")
            self.assertEqual(out[0], "S-2 finding_not_heading -", line)
        code, out = self.run_report(good + "1. S-2 numbered prose\n")
        self.assertEqual(code, 0)

    def test_none_variants_in_preamble(self):
        good = "### W-1 a\n- `src/widget.py:3` — `return rate * 2`\n"
        for pre in ("_None._", "*None*", "(none)", "**None**"):
            self.assertEqual(self.run_report("## Warning\n" + pre + "\n" + good)[0], 0, pre)

    def test_prose_starting_with_an_id_is_not_flagged(self):
        code, out = self.run_report(
            "## Warning\n### W-1 a\n- `src/widget.py:3` — `return rate * 2`\nW-2 is related to this.\n")
        self.assertEqual(code, 0)

    def test_unclosed_fence(self):
        code, out = self.run_report(
            "## Warning\n### W-1 a\n- `src/widget.py:3` — `return rate * 2`\n```\ncode\n")
        self.assertEqual(out[0], "report unclosed_fence -")

    def test_fenced_lines_are_skipped(self):
        code, out = self.run_report(
            "## Warning\n### W-1 a\n- `src/widget.py:3` — `return rate * 2`\n```\n- W-2 in a fence\n### W-3 in a fence\n```\n")
        self.assertEqual(code, 0)
        code, out = self.run_report("## Warning\n```\nin a fence before the first heading\n```\n### W-1 a\n- `src/widget.py:3` — `return rate * 2`\n")
        self.assertEqual(out[0], "report finding_not_heading -")  # a fence is still non-blank text there

    def test_indented_heading_and_crlf(self):
        text = "## Warning\r\n  ### W-1 a\r\n- `src/widget.py:3` — `return rate * 2`\r\n"
        res = vc.check_report(text, self.root)
        self.assertEqual((res.failures, res.checked), ([], 1))

    def test_unclosed_in_recheck_and_dispositions(self):
        body = ("## Warning\n### W-1 a\n- `src/widget.py:3` — `return rate * 2`\n\n")
        code, out = self.run_report(body + "## Re-check\n### W-1: open\n- `src/widget.py:3` — `oops\n")
        self.assertEqual(out[0], "W-1 quote_unclosed src/widget.py:3")
        code, out = self.run_report(body + "## Dispositions\n- W-1: fixed — `src/widget.py:3` — `oops\n")
        self.assertEqual(out[0], "W-1 quote_unclosed src/widget.py:3")

    def test_output_file(self):
        path = self.report("## Warning\n### W-1 a\n- `src/widget.py:3` — `nothing like it`\n")
        code, out, _ = self.run_main("report", path)
        written = os.path.join(os.path.dirname(path), "spec-gate.citations.txt")
        with open(written, encoding="utf-8") as handle:
            self.assertEqual(handle.read(), out)
        self.assertEqual(code, 1)

    def test_ambiguous_failure_and_note(self):
        self.write("other/widget.py", "different\n" * 8)
        code, out = self.run_report(
            "## Warning\n### W-1 a\n- `widget.py:3` — `return rate * 2`\n### W-2 b\n- `widget.py:3` — `zzz zzz zzz`\n")
        self.assertEqual(code, 1)
        self.assertEqual(out[0], "W-2 quote_mismatch widget.py:3 (ambiguous: 2 candidates, none passes)")
        self.assertIn("note W-1 widget.py:3 ambiguous: 2 candidates, one passes", out)


class SnapshotTests(Base):
    """Finding citations of the gate's own spec verify against the spec as reviewed (gates/spec.reviewed-*.md)."""
    REVIEWED = "# Spec\n\n## 3. Desired Behavior\n\nThe widget stops at the limit.\n"
    FIXED = "# Spec\n\n## 1. Added\n\nNew text.\n\n## 3. Desired Behavior\n\nThe widget halts at the cap.\n"

    def setUp(self):
        super().setUp()
        self.write("specs/f1/spec.md", self.FIXED)

    def run_report(self, body):
        code, out, _err = self.run_main("report", self.report(body))
        return code, self.lines(out)

    def test_moved_spec_line_verifies_against_the_snapshot(self):
        self.write("specs/f1/gates/spec.reviewed-0123456789ab.md", self.REVIEWED)
        code, out = self.run_report("## Warning\n### W-1 a\n- `specs/f1/spec.md:5` — `The widget stops at the limit.`\n")
        self.assertEqual(code, 0)
        self.assertEqual(out, [
            "note W-1 specs/f1/spec.md:5 verified against the reviewed spec spec.reviewed-0123456789ab.md",
            "citations: 1 checked, 0 failed"])

    def test_current_spec_is_tried_first(self):
        self.write("specs/f1/gates/spec.reviewed-0123456789ab.md", self.REVIEWED)
        code, out = self.run_report("## Warning\n### W-1 a\n- `specs/f1/spec.md:9` — `The widget halts at the cap.`\n")
        self.assertEqual((code, out), (0, ["citations: 1 checked, 0 failed"]))

    def test_a_quote_in_no_version_still_fails(self):
        self.write("specs/f1/gates/spec.reviewed-0123456789ab.md", self.REVIEWED)
        code, out = self.run_report("## Warning\n### W-1 a\n- `specs/f1/spec.md:5` — `The widget never stops.`\n")
        self.assertEqual((code, out), (1, ["W-1 quote_mismatch specs/f1/spec.md:5", "citations: 1 checked, 1 failed"]))

    def test_no_snapshot_no_fallback(self):
        code, out = self.run_report("## Warning\n### W-1 a\n- `specs/f1/spec.md:5` — `The widget stops at the limit.`\n")
        self.assertEqual(code, 1)

    def test_a_code_citation_never_uses_a_snapshot(self):
        self.write("specs/f1/gates/spec.reviewed-0123456789ab.md", WIDGET)
        code, out = self.run_report("## Warning\n### W-1 a\n- `src/widget.py:3` — `not in the code at all`\n")
        self.assertEqual(out[0], "W-1 quote_mismatch src/widget.py:3")

    def test_an_ambiguous_suffix_never_uses_a_snapshot(self):
        self.write("specs/f2/spec.md", self.FIXED)
        self.write("specs/f1/gates/spec.reviewed-0123456789ab.md", self.REVIEWED)
        code, out = self.run_report("## Warning\n### W-1 a\n- `spec.md:5` — `The widget stops at the limit.`\n")
        self.assertEqual(code, 1)

    def test_a_symlinked_snapshot_is_skipped(self):
        outside = os.path.join(self.tmp, "outside.md")
        with open(outside, "w", encoding="utf-8") as handle:
            handle.write(self.REVIEWED)
        os.makedirs(os.path.join(self.root, "specs/f1/gates"), exist_ok=True)
        os.symlink(outside, os.path.join(self.root, "specs/f1/gates/spec.reviewed-0123456789ab.md"))
        code, out = self.run_report("## Warning\n### W-1 a\n- `specs/f1/spec.md:5` — `The widget stops at the limit.`\n")
        self.assertEqual(code, 1)

    def test_snapshot_end_to_end_with_spec_lint_record(self):
        import importlib.util
        spec_file = os.path.join(SCRIPTS, "spec_lint.py")
        loader = importlib.util.spec_from_file_location("spec_lint_e2e", spec_file)
        sl = importlib.util.module_from_spec(loader)
        loader.loader.exec_module(sl)
        self.write("specs/f1/spec.md", self.REVIEWED)
        self.report("# Gate\n\n## Warning\n### W-1 a\n- `specs/f1/spec.md:5` — `The widget stops at the limit.`\n")
        with redirect_stdout(io.StringIO()):
            self.assertEqual(sl.main(["hash", "specs/f1", "--record", "--root", self.root]), 0)
        self.write("specs/f1/spec.md", self.FIXED)
        code, out, _err = self.run_main("report", os.path.join(self.root, "specs/f1/gates/spec-gate.md"))
        self.assertEqual(code, 0)
        self.assertTrue(self.lines(out)[0].startswith("note W-1 specs/f1/spec.md:5 verified against the reviewed spec"))


class SpecTests(Base):
    def spec(self, body):
        return self.write("specs/f1/spec.md", body)

    def test_spec_mode_and_request_skipped(self):
        path = self.spec(
            "# Spec\n## Request (verbatim)\n`ghost.py:1` `x`\n## Context\n"
            "unquoted `src/widget.py:3` fine, `src/widget.py:1-8` fine, `src/widget.py:3` — `return rate * 2` fine\n"
            "bad `ghost.py:1` and `src/widget.py:20` and `src/widget.py:3` — `nothing like it`\n")
        code, out, _ = self.run_main("spec", path)
        self.assertEqual(code, 1)
        self.assertEqual(self.lines(out), [
            "L6 file_missing ghost.py:1",
            "L6 line_oob src/widget.py:20",
            "L6 quote_mismatch src/widget.py:3",
            "citations: 6 checked, 3 failed",
        ])
        written = os.path.join(self.root, "specs/f1/gates/spec.citations.txt")
        with open(written, encoding="utf-8") as handle:
            self.assertEqual(handle.read(), out)

    def test_spec_clean_creates_gates_dir(self):
        path = self.spec("## Context\n`src/widget.py:2-3`\n")
        code, out, _ = self.run_main("spec", path)
        self.assertEqual((code, out), (0, "citations: 1 checked, 0 failed\n"))
        self.assertTrue(os.path.isdir(os.path.join(self.root, "specs/f1/gates")))


class UsageTests(Base):
    def test_missing_file_is_2(self):
        code, _out, err = self.run_main("report", os.path.join(self.root, "nope.md"))
        self.assertEqual(code, 2)
        self.assertIn("cannot read", err)

    def test_bad_mode_and_root(self):
        with redirect_stderr(io.StringIO()):
            self.assertEqual(vc.main(["bogus", "x"]), 2)
            self.assertEqual(vc.main([]), 2)
        path = self.spec_path = self.write("s.md", "x\n")
        with redirect_stderr(io.StringIO()):
            self.assertEqual(vc.main(["spec", path, "--root", os.path.join(self.tmp, "none")]), 2)


if __name__ == "__main__":
    unittest.main()
