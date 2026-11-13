#!/usr/bin/env python3
"""Tests for scripts/forge/research_query.py and research_check.py (stdlib unittest), on research_fixtures.py.

Run: python3 -m unittest discover -s tests/scripts/forge -p 'test_research_query.py' -v
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

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(REPO, "scripts", "forge"))
sys.path.insert(0, HERE)
import research_check  # noqa: E402
import research_fixtures as fx  # noqa: E402
import research_query  # noqa: E402


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.root = os.path.join(self.tmp, "proj")
        fx.write_project(self.root)
        os.makedirs(os.path.join(self.root, "research"))
        self.report = os.path.join(self.root, "research", "2026-11-13-topic.md")
        self.ledger = os.path.join(self.root, "research", "2026-11-13-topic-ledger.md")
        self.path = os.environ.get("PATH", "")
        self.config = os.environ.get("CLAUDE_CONFIG_DIR")

    def tearDown(self):
        os.environ["PATH"] = self.path
        if self.config is None:
            os.environ.pop("CLAUDE_CONFIG_DIR", None)
        else:
            os.environ["CLAUDE_CONFIG_DIR"] = self.config
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write(self, path, text):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)

    def query(self, *args, index="regex"):
        argv = list(args) + ["--root", self.root]
        if args[0] != "trace":
            argv += ["--index", index]
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = research_query.main(argv)
        return code, out.getvalue(), err.getvalue()


class BodiesTest(Base):
    def test_one_call_prints_every_body_with_its_ledger_heading(self):
        code, out, _ = self.query("bodies", "src/js/paths.js:3", "normalize_key", "src/go/paths.go:6",
                                  "`src/java/UserPaths.java:4`")
        self.assertEqual(code, 0, out)
        self.assertIn("### `normalizeSegment` `src/js/paths.js:3-5`  (end: brace)", out)
        self.assertIn("### `normalize_key` `src/py/store.py:4-5`  (end: indent)", out)
        self.assertIn("### `normalizeID` `src/go/paths.go:5-7`  (end: brace)", out)  # a body line finds its head
        self.assertIn("### `normalize` `src/java/UserPaths.java:4-6`  (end: brace)", out)
        self.assertIn("     4    return seg.trim().toLowerCase();", out)

    def test_ctags_end_and_cut(self):
        tags = [t if t[0] != "UserPath" else ("UserPath", "src/go/paths.go", 10, "func", "", 12) for t in fx.TAGS]
        bin_dir = os.path.join(self.tmp, "bin")
        fx.write_fake_ctags(bin_dir, tags)
        os.environ["PATH"] = bin_dir + os.pathsep + self.path
        code, out, _ = self.query("bodies", "UserPath", "--max-lines", "2", index="ctags")
        self.assertEqual(code, 0, out)
        self.assertIn("### `UserPath` `src/go/paths.go:10-12`  (end: ctags)", out)
        self.assertIn("cut at 2 lines: read `src/go/paths.go:12-12`", out)

    def test_a_body_line_names_its_own_function_not_the_next(self):
        self.write(os.path.join(self.root, "src", "py", "q.py"),
                   "def a(x):\n    y = 1\n    return helper(x)\n\ndef b():\n    return 2\n")
        code, out, _ = self.query("bodies", "src/py/q.py:3")
        self.assertIn("### `a` `src/py/q.py:1-3`", out)

    def test_a_line_above_a_head_belongs_to_it_only_through_attributes(self):
        self.write(os.path.join(self.root, "src", "js", "t.ts"),
                   "export type Name = string;\n\n@Get()\nfunction f() {\n  return 1;\n}\n")
        code, out, _ = self.query("bodies", "src/js/t.ts:3", "src/js/t.ts:1")
        self.assertIn("### `f` `src/js/t.ts:4-6`", out)
        self.assertIn("### `Name` `src/js/t.ts:1-1`", out)  # not f: a code line sits between

    def test_annotation_lines_above_an_allman_head(self):
        self.write(os.path.join(self.root, "src", "java", "C.java"), "\n".join([
            "class C {", "  @A", "  @B(1)", "  @C", "  @D", "  void run()", "  {", "    go();", "  }", "}"]) + "\n")
        code, out, _ = self.query("bodies", "src/java/C.java:2")  # the regex set does not index `void run()`
        self.assertIn("`src/java/C.java:2-9`  (end: brace)", out)  # the rule walks past the annotations
        bin_dir = os.path.join(self.tmp, "bin")
        fx.write_fake_ctags(bin_dir, fx.TAGS + [("C", "src/java/C.java", 1, "class"),
                                                ("run", "src/java/C.java", 6, "method", "()", 9)])
        os.environ["PATH"] = bin_dir + os.pathsep + self.path
        code, out, _ = self.query("bodies", "src/java/C.java:2", index="ctags")
        self.assertIn("### `run` `src/java/C.java:6-9`  (end: ctags)", out)

    def test_unknown_items(self):
        code, out, _ = self.query("bodies", "noSuchThing", "src/none.js:1")
        self.assertEqual(code, 0)
        self.assertIn("!! noSuchThing: no definition named `noSuchThing`", out)
        self.assertIn("!! src/none.js:1: file not found", out)


class PendingTest(Base):
    def test_pending_lists_entries_then_leaves_once(self):
        ledger = fx.LEDGERS["js"].split("### `buildUserPath`")[0]
        self.write(self.ledger, ledger)
        code, out, _ = self.query("pending", self.report)
        self.assertEqual(code, 0, out)
        self.assertIn("pending: 2 need a ledger entry, 0 containers need an entry, 0 depth-2 items need a Coverage "
                      "row; showing 2 entries", out)
        self.assertIn("### `buildUserPath` `src/js/paths.js:7-10`", out)
        self.assertIn("### `checkAccess` `src/js/auth.js:1-3`", out)
        self.write(self.ledger, ledger + "\n## Excluded\n- `checkAccess` `src/js/auth.js:1` — out of scope\n")
        code, out, _ = self.query("pending", self.report)
        self.assertIn("pending: 1 need a ledger entry", out)
        self.assertNotIn("checkAccess", out.split("\n\n", 1)[1])
        self.write(self.ledger, fx.LEDGERS["js"])
        code, out, _ = self.query("pending", self.report)
        self.assertIn("depth 0–1 is done: run `pending --leaves` once for the 1 depth-2 items", out)
        self.assertNotIn("###", out)
        code, out, _ = self.query("pending", self.report, "--leaves")
        self.assertIn("D2 [data] from the ledger as `normalizeSegment` `src/js/paths.js:3`", out)
        self.write(self.report, "## Coverage\n- `normalizeSegment` `src/js/paths.js:3` — excluded — trivial\n")
        code, out, _ = self.query("pending", self.report, "--leaves")
        self.assertIn("0 depth-2 items need a Coverage row", out)

    def test_leaves_are_never_cut_by_batch(self):
        self.write(self.ledger, fx.LEDGERS["js"])
        code, out, _ = self.query("pending", self.report, "--leaves", "--batch", "1")
        self.assertIn("showing 1 depth-2 items", out)
        self.assertEqual(out.count("### "), 1)

    def test_pending_names_containers_without_entry(self):
        self.write(self.ledger,
                   "## Seeds\n- `Store` `src/py/store.py:13` — pass 1 — bottom-up [container]\n\n## Read\n")
        code, out, _ = self.query("pending", self.report)
        self.assertIn("container without entry: `Store` `src/py/store.py:13` — list its members with `siblings "
                      "src/py/store.py:13`", out)
        self.assertNotIn("depth 0–1 is done", out)

    def test_items_prints_the_item_list_and_writes_nothing(self):
        self.write(self.ledger, fx.LEDGERS["js"])
        code, out, _ = self.query("items", self.report)
        self.assertEqual(code, 0, out)
        self.assertIn("items: 4 (0 over budget)", out)
        self.assertIn("D2 `normalizeSegment` src/js/paths.js:3 [data] — leaf", out)
        self.assertEqual(sorted(os.listdir(os.path.dirname(self.report))), ["2026-11-13-topic-ledger.md"])

    def test_missing_ledger_is_exit_2(self):
        code, _, err = self.query("pending", self.report)
        self.assertEqual(code, 2)
        self.assertIn("cannot read the ledger", err)


class CallersSiblingsTest(Base):
    def test_callers_are_grouped_by_enclosing_definition(self):
        code, out, _ = self.query("callers", "normalize_key")
        self.assertEqual(code, 0, out)
        self.assertIn("callers of `normalize_key`: 1 uses in 1 definitions", out)
        self.assertIn("- `object_path` `src/py/store.py:8` — 1 use: L10", out)
        code, out, _ = self.query("callers", "paths.normalizeSegment")
        self.assertIn("`buildUserPath` `src/js/paths.js:7` — 1 use: L8", out)
        self.assertIn("(top level) `src/js/paths.js` — 1 use: L12", out)

    def test_comments_and_strings_are_not_uses(self):
        self.write(os.path.join(self.root, "src", "js", "x.js"),
                   'function a() {\n  // normalizeSegment here\n  return "normalizeSegment";\n}\n')
        code, out, _ = self.query("callers", "normalizeSegment")
        self.assertNotIn("x.js", out)

    def test_siblings_with_terms(self):
        code, out, _ = self.query("siblings", "src/py/store.py:10", "--terms", "bucket,open")
        self.assertEqual(code, 0, out)
        self.assertIn("siblings of `src/py/store.py:8`", out)
        self.assertIn("- `normalize_key` `src/py/store.py:4-5` (2 lines, end: indent)\n", out)
        self.assertIn("- `Store` `src/py/store.py:13-16` (4 lines, end: indent) [container] "
                      "[mentions: bucket, open]", out)
        self.assertIn("- `get` `src/py/store.py:14-16` (3 lines, end: indent) [mentions: bucket, open]", out)
        self.assertNotIn("`object_path` `src/py/store.py:8", out.split("\n\n", 1)[1])

    def test_siblings_of_a_container_head_are_its_members(self):
        code, out, _ = self.query("siblings", "src/py/store.py:13")
        body = out.split("\n\n", 1)[1]
        self.assertIn("`get` `src/py/store.py:14-16`", body)
        self.assertNotIn("normalize_key", body)

    def test_siblings_needs_a_path(self):
        code, _, err = self.query("siblings", "object_path")
        self.assertEqual(code, 2)
        self.assertIn("takes a `path:N`", err)


class TraceTest(Base):
    def transcript(self, folder, name, lines):
        path = os.path.join(folder, name)
        self.write(path, "".join(json.dumps(l) + "\n" for l in lines))
        return path

    @staticmethod
    def asst(mid, ctx, tool_input=None):
        content = [{"type": "text", "text": "x"}]
        if tool_input is not None:
            content.append({"type": "tool_use", "name": "Write", "input": tool_input})
        return {"type": "assistant", "message": {"id": mid, "content": content,
                                                 "usage": {"input_tokens": 10, "cache_read_input_tokens": ctx,
                                                           "cache_creation_input_tokens": 0}}}

    def test_trace_counts_turns_and_peak_from_the_ledger_writer(self):
        config = os.path.join(self.tmp, "cfg")
        os.environ["CLAUDE_CONFIG_DIR"] = config
        folder = research_query.transcript_dirs(self.root)[0]
        ledger_input = {"file_path": self.ledger, "content": "## Seeds"}
        self.transcript(folder, "main.jsonl", [
            {"type": "user", "message": {"content": "older work"}},
            self.asst("m0", 500000),
            {"type": "user", "message": {"content": "<command-name>/research</command-name> topic"}},
            self.asst("m1", 1000), self.asst("m1", 1000),  # one response, two transcript lines
            self.asst("m2", 50000, ledger_input),
            self.asst("m3", 120000),
        ])
        self.transcript(os.path.join(folder, "s", "subagents"), "agent-x.jsonl", [self.asst("e1", 999999)])
        code, out, _ = self.query("trace", self.report)
        self.assertEqual(code, 0, out)
        self.assertIn("trace: 3 turns, peak context 120k tokens, 0.2M context tokens in all\ntranscript: ", out)

    def test_a_read_or_a_namesake_is_not_a_ledger_write(self):
        os.environ["CLAUDE_CONFIG_DIR"] = os.path.join(self.tmp, "cfg")
        folder = research_query.transcript_dirs(self.root)[0]
        writer = self.transcript(folder, "runner.jsonl", [self.asst("w1", 1000, {"file_path": self.ledger})])
        read = self.asst("r1", 9000, {"file_path": self.ledger})
        read["message"]["content"][1]["name"] = "Read"
        other = self.asst("o1", 9000, {"file_path": self.ledger.replace("topic-ledger", "old-topic-ledger")})
        newer = self.transcript(folder, "newer.jsonl", [read, other])
        os.utime(writer, (1, os.path.getmtime(newer) - 10))
        code, out, _ = self.query("trace", self.report)
        self.assertIn("transcript: %s" % writer, out)
        shell = self.asst("s1", 5, None)
        shell["message"]["content"].append({"type": "tool_use", "name": "Bash",
                                            "input": {"command": "cat > research/2026-11-13-topic-ledger.md <<'E'"}})
        self.assertTrue(research_query._writes_ledger(shell, "2026-11-13-topic-ledger.md"))
        shell["message"]["content"][-1]["input"]["command"] = "echo '- a -> research/2026-11-13-topic-ledger.md' >> n"
        self.assertFalse(research_query._writes_ledger(shell, "2026-11-13-topic-ledger.md"))

    def test_trace_unavailable(self):
        os.environ["CLAUDE_CONFIG_DIR"] = os.path.join(self.tmp, "none")
        code, out, _ = self.query("trace", self.report)
        self.assertEqual(code, 0)
        self.assertIn("trace: unavailable (no transcript dir", out)


class ResearchCheckTest(Base):
    def run_check(self, *extra):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = research_check.main([self.report, "--root", self.root, "--index", "regex"] + list(extra))
        return code, out.getvalue(), err.getvalue()

    def test_one_command_runs_both(self):
        self.write(self.ledger, fx.LEDGERS["js"])
        code, out, _ = self.run_check()
        self.assertEqual(code, 0, out)
        self.assertIn("closure-check: 0 blocking", out)
        self.assertIn("research-check: closure 0 blocking, lint skipped (no report yet)", out)
        self.write(self.report, "# R\n")
        code, out, _ = self.run_check()
        self.assertEqual(code, 1, out)
        self.assertIn("no_coverage_section", out)
        self.assertIn("research-check: closure 0 blocking, lint ", out)
        for suffix in ("-closure.txt", "-research-lint.txt"):
            self.assertTrue(os.path.isfile(self.report[:-3] + suffix))

    def test_missing_ledger_is_exit_2(self):
        code, _, err = self.run_check()
        self.assertEqual(code, 2)
        self.assertIn("cannot read the ledger", err)


if __name__ == "__main__":
    unittest.main()
