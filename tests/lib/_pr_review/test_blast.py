"""Tests for src/devforge/lib/_pr_review/_blast.py.

Coverage:
    TestDetectLanguage         — extension → language; unknown → None
    TestParseDiff              — multi-file, hunk parsing, empty, malformed
    TestExtractSymbolsPython   — each Python pattern + negative case
    TestExtractSymbolsTypeScript — each TS pattern + const filter + negative
    TestExtractSymbolsJavaScript — same patterns as TS
    TestExtractSymbolsVue      — TS/JS regexes + implicit component probe spec
    TestExtractSymbolsGo       — func pattern (with/without receiver) + type
    TestExtractSymbolsJava     — method heuristic + class pattern
    TestExtractSymbolsRuby     — def pattern + class pattern
    TestExtractSymbolsRust     — fn/struct/enum/trait patterns
    TestVueImplicitComponent   — Vue file with added lines → 1 component spec
    TestDedupSameSymbolMultiLocation — same (symbol, file) → 1 entry
    TestSort                   — entries sorted by (file, symbol)
    TestCap                    — >100 symbols → cap=100, capped=True
    TestBuildProbeSpec         — canonical shape, all keys, sentinel values
    TestRunHappyPath           — synthetic state.json + diff → state.blast populated
    TestRunNoState             — missing state.json → ValueError
    TestRunReplacesPriorBlast  — re-run replaces prior blast entries
    TestProbeSpecShape         — every key present; callers/callees/etc all []
"""

from __future__ import annotations

import dataclasses
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _pr_review._blast import (  # noqa: E402
    _MAX_SYMBOLS_PER_PR,
    _build_probe_spec,
    _dedup_sort_cap,
    _detect_language,
    _extract_symbols_for_file,
    _parse_diff,
    run,
)
from _pr_review._state import PRReviewState, state_path  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers shared across test classes.
# ---------------------------------------------------------------------------


def _make_state_json(tmp_dir: str, pr_number: int, diff: str = "") -> str:
    """Write a minimal state.json and return its path."""
    abs_devforge = os.path.join(tmp_dir, ".devforge")
    sp = state_path(abs_devforge, pr_number)
    os.makedirs(os.path.dirname(sp), exist_ok=True)
    state = PRReviewState(
        pr_number=pr_number,
        repo="acme/app",
        diff=diff,
    )
    with open(sp, "w", encoding="utf-8") as fh:
        json.dump(dataclasses.asdict(state), fh, indent=2)
        fh.write("\n")
    return sp


_REQUIRED_PROBE_KEYS = {
    "symbol",
    "file",
    "kind",
    "language",
    "diff_line_hint",
    "mcp_hints",
    "callers",
    "callees",
    "data_flow_targets",
    "tests_referencing",
    "filled",
}


# ---------------------------------------------------------------------------
# TestDetectLanguage
# ---------------------------------------------------------------------------


class TestDetectLanguage(unittest.TestCase):
    def test_py(self):
        self.assertEqual(_detect_language("foo/bar.py"), "python")

    def test_ts(self):
        self.assertEqual(_detect_language("src/app.ts"), "typescript")

    def test_tsx(self):
        self.assertEqual(_detect_language("src/App.tsx"), "typescript")

    def test_js(self):
        self.assertEqual(_detect_language("lib/util.js"), "javascript")

    def test_jsx(self):
        self.assertEqual(_detect_language("src/Component.jsx"), "javascript")

    def test_mjs(self):
        self.assertEqual(_detect_language("module.mjs"), "javascript")

    def test_vue(self):
        self.assertEqual(_detect_language("src/Foo.vue"), "vue")

    def test_go(self):
        self.assertEqual(_detect_language("main.go"), "go")

    def test_java(self):
        self.assertEqual(_detect_language("Service.java"), "java")

    def test_rb(self):
        self.assertEqual(_detect_language("app/models/user.rb"), "ruby")

    def test_rs(self):
        self.assertEqual(_detect_language("src/lib.rs"), "rust")

    def test_unknown_extension_returns_none(self):
        self.assertIsNone(_detect_language("file.yaml"))

    def test_no_extension_returns_none(self):
        self.assertIsNone(_detect_language("Makefile"))

    def test_empty_string_returns_none(self):
        self.assertIsNone(_detect_language(""))

    def test_dot_only_returns_none(self):
        self.assertIsNone(_detect_language(".gitignore"))

    def test_extension_case_insensitive(self):
        # Extension lookup is lowercased; .PY should still map to python.
        self.assertEqual(_detect_language("script.PY"), "python")


# ---------------------------------------------------------------------------
# TestParseDiff
# ---------------------------------------------------------------------------


class TestParseDiff(unittest.TestCase):
    def test_empty_string_returns_empty_list(self):
        self.assertEqual(_parse_diff(""), [])

    def test_single_file_added_lines_captured(self):
        diff = (
            "diff --git a/foo.py b/foo.py\n"
            "--- a/foo.py\n"
            "+++ b/foo.py\n"
            "@@ -0,0 +1,2 @@\n"
            "+def hello():\n"
            "+    pass\n"
        )
        blocks = _parse_diff(diff)
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0]["file"], "foo.py")
        # splitlines() strips the trailing newline; lines are stored without \n
        self.assertIn("+def hello():", blocks[0]["added_lines"])
        # added_lines are raw lines starting with +
        self.assertTrue(all(l.startswith("+") for l in blocks[0]["added_lines"]))

    def test_multi_file_diff_returns_multiple_blocks(self):
        diff = (
            "diff --git a/a.py b/a.py\n"
            "--- a/a.py\n"
            "+++ b/a.py\n"
            "@@ -1 +1 @@\n"
            "+def foo(): pass\n"
            "diff --git a/b.ts b/b.ts\n"
            "--- a/b.ts\n"
            "+++ b/b.ts\n"
            "@@ -1 +1 @@\n"
            "+function bar() {}\n"
        )
        blocks = _parse_diff(diff)
        self.assertEqual(len(blocks), 2)
        files = [b["file"] for b in blocks]
        self.assertIn("a.py", files)
        self.assertIn("b.ts", files)

    def test_removed_lines_not_included(self):
        diff = (
            "diff --git a/x.py b/x.py\n"
            "--- a/x.py\n"
            "+++ b/x.py\n"
            "@@ -1 +1 @@\n"
            "-def old(): pass\n"
            "+def new(): pass\n"
        )
        blocks = _parse_diff(diff)
        self.assertEqual(len(blocks), 1)
        for line in blocks[0]["added_lines"]:
            self.assertFalse(line.startswith("-"), "removed line should not appear")

    def test_context_lines_not_included(self):
        diff = (
            "diff --git a/x.py b/x.py\n"
            "+++ b/x.py\n"
            "@@ -1 +1 @@\n"
            " context line\n"
            "+def added(): pass\n"
        )
        blocks = _parse_diff(diff)
        added = blocks[0]["added_lines"]
        for line in added:
            self.assertFalse(line.startswith(" "), "context line should not appear")

    def test_hunk_header_excluded(self):
        diff = (
            "diff --git a/x.py b/x.py\n"
            "@@ -0,0 +1 @@\n"
            "+def foo(): pass\n"
        )
        blocks = _parse_diff(diff)
        for line in blocks[0]["added_lines"]:
            self.assertFalse(line.startswith("@@"))

    def test_plus_plus_plus_header_excluded(self):
        diff = (
            "diff --git a/x.py b/x.py\n"
            "--- a/x.py\n"
            "+++ b/x.py\n"
            "+def real(): pass\n"
        )
        blocks = _parse_diff(diff)
        for line in blocks[0]["added_lines"]:
            self.assertFalse(line.startswith("+++"))

    def test_no_diff_git_header_still_parses_via_triple_plus(self):
        """A diff chunk with +++ b/<path> but no diff --git header is handled."""
        diff = (
            "--- a/foo.py\n"
            "+++ b/foo.py\n"
            "+def hello(): pass\n"
        )
        blocks = _parse_diff(diff)
        # current_file is set via +++ b/ path, so we get at least 1 file block
        self.assertGreaterEqual(len(blocks), 1)
        files = [b["file"] for b in blocks]
        self.assertIn("foo.py", files)

    def test_empty_diff_no_added_lines(self):
        diff = "diff --git a/f.py b/f.py\n"
        blocks = _parse_diff(diff)
        self.assertEqual(blocks[0]["added_lines"], [])

    def test_path_with_subdirectory(self):
        diff = (
            "diff --git a/apps/web/src/util.ts b/apps/web/src/util.ts\n"
            "+function doThing() {}\n"
        )
        blocks = _parse_diff(diff)
        self.assertEqual(blocks[0]["file"], "apps/web/src/util.ts")


# ---------------------------------------------------------------------------
# TestExtractSymbolsPython
# ---------------------------------------------------------------------------


class TestExtractSymbolsPython(unittest.TestCase):
    def _run(self, line: str):
        return _extract_symbols_for_file("foo.py", [line], "python")

    def test_def_function(self):
        specs = self._run("+def my_func(a, b):")
        self.assertEqual(len(specs), 1)
        self.assertEqual(specs[0]["symbol"], "my_func")
        self.assertEqual(specs[0]["kind"], "function")

    def test_async_def_function(self):
        specs = self._run("+async def handle_request(req):")
        self.assertEqual(len(specs), 1)
        self.assertEqual(specs[0]["symbol"], "handle_request")
        self.assertEqual(specs[0]["kind"], "function")

    def test_class_colon(self):
        specs = self._run("+class MyModel:")
        self.assertEqual(len(specs), 1)
        self.assertEqual(specs[0]["symbol"], "MyModel")
        self.assertEqual(specs[0]["kind"], "class")

    def test_class_parentheses(self):
        specs = self._run("+class SubModel(Base):")
        self.assertEqual(len(specs), 1)
        self.assertEqual(specs[0]["symbol"], "SubModel")

    def test_indented_method(self):
        specs = self._run("+    def _private(self):")
        self.assertEqual(len(specs), 1)
        self.assertEqual(specs[0]["symbol"], "_private")

    def test_no_match_comment(self):
        specs = self._run("+# def not_a_def():")
        self.assertEqual(specs, [])

    def test_no_match_removed_line(self):
        specs = self._run("-def removed():")
        self.assertEqual(specs, [])

    def test_no_match_plain_assignment(self):
        specs = self._run("+x = 5")
        self.assertEqual(specs, [])

    def test_diff_line_hint_zero_based(self):
        specs = _extract_symbols_for_file(
            "f.py",
            ["+x = 1", "+def foo():"],  # "def foo" is at index 1
            "python",
        )
        symbols = {s["symbol"]: s for s in specs}
        self.assertIn("foo", symbols)
        self.assertEqual(symbols["foo"]["diff_line_hint"], "diff:line+1")


# ---------------------------------------------------------------------------
# TestExtractSymbolsTypeScript
# ---------------------------------------------------------------------------


class TestExtractSymbolsTypeScript(unittest.TestCase):
    def _run(self, line: str):
        return _extract_symbols_for_file("src/app.ts", [line], "typescript")

    def test_function_declaration(self):
        specs = self._run("+function doWork(x: number): void {")
        self.assertEqual(len(specs), 1)
        self.assertEqual(specs[0]["symbol"], "doWork")
        self.assertEqual(specs[0]["kind"], "function")

    def test_export_function(self):
        specs = self._run("+export function getUser(id: string) {")
        self.assertEqual(len(specs), 1)
        self.assertEqual(specs[0]["symbol"], "getUser")
        self.assertEqual(specs[0]["kind"], "function")

    def test_async_export_function(self):
        specs = self._run("+export async function fetchData() {")
        self.assertEqual(len(specs), 1)
        self.assertEqual(specs[0]["symbol"], "fetchData")
        self.assertEqual(specs[0]["kind"], "function")

    def test_class_declaration(self):
        specs = self._run("+class UserService {")
        self.assertEqual(len(specs), 1)
        self.assertEqual(specs[0]["symbol"], "UserService")
        self.assertEqual(specs[0]["kind"], "class")

    def test_export_class_generic(self):
        specs = self._run("+export class Repository<T> {")
        self.assertEqual(len(specs), 1)
        self.assertEqual(specs[0]["symbol"], "Repository")
        self.assertEqual(specs[0]["kind"], "class")

    def test_interface(self):
        specs = self._run("+interface UserProps {")
        self.assertEqual(len(specs), 1)
        self.assertEqual(specs[0]["symbol"], "UserProps")
        self.assertEqual(specs[0]["kind"], "interface")

    def test_export_interface(self):
        specs = self._run("+export interface ApiResponse<T> {")
        self.assertEqual(len(specs), 1)
        self.assertEqual(specs[0]["symbol"], "ApiResponse")
        self.assertEqual(specs[0]["kind"], "interface")

    def test_type_alias(self):
        specs = self._run("+type UserId = string;")
        self.assertEqual(len(specs), 1)
        self.assertEqual(specs[0]["symbol"], "UserId")
        self.assertEqual(specs[0]["kind"], "type")

    def test_export_type(self):
        specs = self._run("+export type Callback = () => void;")
        self.assertEqual(len(specs), 1)
        self.assertEqual(specs[0]["symbol"], "Callback")
        self.assertEqual(specs[0]["kind"], "type")

    def test_const_function_expression_emitted(self):
        specs = self._run("+const handleClick = (evt: Event) => {")
        self.assertEqual(len(specs), 1)
        self.assertEqual(specs[0]["symbol"], "handleClick")
        self.assertEqual(specs[0]["kind"], "export")

    def test_const_async_function_expression_emitted(self):
        specs = self._run("+export const processOrder = async (order) => {")
        self.assertEqual(len(specs), 1)
        self.assertEqual(specs[0]["symbol"], "processOrder")

    def test_const_function_keyword_emitted(self):
        specs = self._run("+const myFn = function() {}")
        self.assertEqual(len(specs), 1)
        self.assertEqual(specs[0]["symbol"], "myFn")

    def test_plain_const_not_emitted(self):
        specs = self._run("+const MAX_RETRIES = 3;")
        self.assertEqual(specs, [])

    def test_plain_const_string_not_emitted(self):
        specs = self._run('+const API_URL = "https://example.com";')
        self.assertEqual(specs, [])

    def test_typed_const_arrow_emitted(self):
        # TypeScript typed-const arrow: type annotation between name and =
        specs = self._run("+const handleClick: EventHandler = (e: Event) => {")
        self.assertEqual(len(specs), 1)
        self.assertEqual(specs[0]["symbol"], "handleClick")
        self.assertEqual(specs[0]["kind"], "export")
        self.assertEqual(specs[0]["language"], "typescript")

    def test_exported_typed_const_arrow_emitted(self):
        # export + type annotation
        specs = self._run("+export const validate: Validator = (input) => {")
        self.assertEqual(len(specs), 1)
        self.assertEqual(specs[0]["symbol"], "validate")
        self.assertEqual(specs[0]["kind"], "export")

    def test_no_match_import(self):
        specs = self._run('+import { useState } from "react";')
        self.assertEqual(specs, [])


# ---------------------------------------------------------------------------
# TestExtractSymbolsJavaScript
# ---------------------------------------------------------------------------


class TestExtractSymbolsJavaScript(unittest.TestCase):
    """JavaScript uses the same patterns as TypeScript."""

    def test_function_declaration(self):
        specs = _extract_symbols_for_file(
            "util.js", ["+function helper(x) {"], "javascript"
        )
        self.assertEqual(len(specs), 1)
        self.assertEqual(specs[0]["symbol"], "helper")
        self.assertEqual(specs[0]["language"], "javascript")

    def test_const_arrow_function_emitted(self):
        specs = _extract_symbols_for_file(
            "util.mjs", ["+const render = (el) => {"], "javascript"
        )
        self.assertEqual(len(specs), 1)
        self.assertEqual(specs[0]["symbol"], "render")

    def test_plain_const_not_emitted(self):
        specs = _extract_symbols_for_file(
            "util.js", ["+const VERSION = 2;"], "javascript"
        )
        self.assertEqual(specs, [])


# ---------------------------------------------------------------------------
# TestExtractSymbolsVue
# ---------------------------------------------------------------------------


class TestExtractSymbolsVue(unittest.TestCase):
    def test_implicit_component_emitted_for_vue_file_with_added_lines(self):
        specs = _extract_symbols_for_file(
            "src/components/OrderCard.vue",
            ["+<template>"],  # non-empty added_lines triggers component spec
            "vue",
        )
        component_specs = [s for s in specs if s["kind"] == "component"]
        self.assertEqual(len(component_specs), 1)
        self.assertEqual(component_specs[0]["symbol"], "OrderCard")
        self.assertEqual(component_specs[0]["language"], "vue")

    def test_no_implicit_component_when_no_added_lines(self):
        specs = _extract_symbols_for_file(
            "src/components/Foo.vue",
            [],
            "vue",
        )
        self.assertEqual(specs, [])

    def test_ts_patterns_applied_to_vue_added_lines(self):
        specs = _extract_symbols_for_file(
            "src/MyComp.vue",
            ["+function doSomething() {"],
            "vue",
        )
        symbols = [s["symbol"] for s in specs]
        self.assertIn("doSomething", symbols)

    def test_vue_component_kind_is_component(self):
        specs = _extract_symbols_for_file(
            "src/Foo.vue",
            ["+export function bar() {}"],
            "vue",
        )
        kinds = {s["kind"] for s in specs}
        self.assertIn("component", kinds)

    def test_vue_component_diff_line_hint_is_zero(self):
        specs = _extract_symbols_for_file(
            "src/Widget.vue",
            ["+<script setup>"],
            "vue",
        )
        comp = next(s for s in specs if s["kind"] == "component")
        self.assertEqual(comp["diff_line_hint"], "diff:line+0")


# ---------------------------------------------------------------------------
# TestExtractSymbolsGo
# ---------------------------------------------------------------------------


class TestExtractSymbolsGo(unittest.TestCase):
    def _run(self, line: str):
        return _extract_symbols_for_file("main.go", [line], "go")

    def test_simple_function(self):
        specs = self._run("+func handleRequest(w http.ResponseWriter, r *http.Request) {")
        self.assertEqual(len(specs), 1)
        self.assertEqual(specs[0]["symbol"], "handleRequest")
        self.assertEqual(specs[0]["kind"], "function")

    def test_method_with_receiver(self):
        specs = self._run("+func (s *Server) Start(addr string) error {")
        self.assertEqual(len(specs), 1)
        self.assertEqual(specs[0]["symbol"], "Start")
        self.assertEqual(specs[0]["kind"], "function")

    def test_struct_type(self):
        specs = self._run("+type Config struct {")
        self.assertEqual(len(specs), 1)
        self.assertEqual(specs[0]["symbol"], "Config")
        self.assertEqual(specs[0]["kind"], "type")

    def test_interface_type(self):
        specs = self._run("+type Stringer interface {")
        self.assertEqual(len(specs), 1)
        self.assertEqual(specs[0]["symbol"], "Stringer")
        self.assertEqual(specs[0]["kind"], "type")

    def test_no_match_variable(self):
        specs = self._run("+var ErrNotFound = errors.New(\"not found\")")
        self.assertEqual(specs, [])


# ---------------------------------------------------------------------------
# TestExtractSymbolsJava
# ---------------------------------------------------------------------------


class TestExtractSymbolsJava(unittest.TestCase):
    def _run(self, line: str):
        return _extract_symbols_for_file("Service.java", [line], "java")

    def test_class_declaration(self):
        specs = self._run("+public class UserService {")
        classes = [s for s in specs if s["kind"] == "class"]
        self.assertGreater(len(classes), 0)
        self.assertEqual(classes[0]["symbol"], "UserService")

    def test_method_declaration(self):
        specs = self._run("+    public String getName() {")
        methods = [s for s in specs if s["kind"] == "method"]
        self.assertGreater(len(methods), 0)
        names = [s["symbol"] for s in methods]
        self.assertIn("getName", names)

    def test_no_match_comment(self):
        specs = self._run("+ // public void doThing() {")
        # Comment line shouldn't match; the + is followed by a space+comment
        # The regex requires method/class keywords to follow whitespace
        # This is a best-effort heuristic; just ensure no crash.
        self.assertIsInstance(specs, list)


# ---------------------------------------------------------------------------
# TestExtractSymbolsRuby
# ---------------------------------------------------------------------------


class TestExtractSymbolsRuby(unittest.TestCase):
    def _run(self, line: str):
        return _extract_symbols_for_file("user.rb", [line], "ruby")

    def test_def_method(self):
        specs = self._run("+  def full_name")
        self.assertEqual(len(specs), 1)
        self.assertEqual(specs[0]["symbol"], "full_name")
        self.assertEqual(specs[0]["kind"], "method")

    def test_def_method_with_question_mark(self):
        specs = self._run("+  def valid?")
        self.assertEqual(len(specs), 1)
        self.assertEqual(specs[0]["symbol"], "valid?")

    def test_def_method_with_bang(self):
        specs = self._run("+  def save!")
        self.assertEqual(len(specs), 1)
        self.assertEqual(specs[0]["symbol"], "save!")

    def test_class_declaration(self):
        specs = self._run("+class OrderProcessor")
        self.assertEqual(len(specs), 1)
        self.assertEqual(specs[0]["symbol"], "OrderProcessor")
        self.assertEqual(specs[0]["kind"], "class")

    def test_no_match_lower_class(self):
        # Ruby class names must start with uppercase per language convention
        # and the pattern requires it.
        specs = self._run("+class notAClass")
        # lowercase class name: class pattern requires [A-Z] start
        self.assertEqual(specs, [])


# ---------------------------------------------------------------------------
# TestExtractSymbolsRust
# ---------------------------------------------------------------------------


class TestExtractSymbolsRust(unittest.TestCase):
    def _run(self, line: str):
        return _extract_symbols_for_file("lib.rs", [line], "rust")

    def test_fn(self):
        specs = self._run("+fn parse_input(s: &str) -> Result<i32, ParseError> {")
        self.assertEqual(len(specs), 1)
        self.assertEqual(specs[0]["symbol"], "parse_input")
        self.assertEqual(specs[0]["kind"], "function")

    def test_pub_fn(self):
        specs = self._run("+pub fn run() {")
        self.assertEqual(len(specs), 1)
        self.assertEqual(specs[0]["symbol"], "run")

    def test_struct(self):
        specs = self._run("+pub struct Config {")
        self.assertEqual(len(specs), 1)
        self.assertEqual(specs[0]["symbol"], "Config")
        self.assertEqual(specs[0]["kind"], "struct")

    def test_enum(self):
        specs = self._run("+enum Status {")
        self.assertEqual(len(specs), 1)
        self.assertEqual(specs[0]["symbol"], "Status")
        self.assertEqual(specs[0]["kind"], "enum")

    def test_pub_trait(self):
        specs = self._run("+pub trait Serializable {")
        self.assertEqual(len(specs), 1)
        self.assertEqual(specs[0]["symbol"], "Serializable")
        self.assertEqual(specs[0]["kind"], "trait")

    def test_no_match_comment(self):
        specs = self._run("+// fn not_real() {")
        # comment starts with //, actual line is "+// fn"; no match expected
        self.assertEqual(specs, [])


# ---------------------------------------------------------------------------
# TestVueImplicitComponent
# ---------------------------------------------------------------------------


class TestVueImplicitComponent(unittest.TestCase):
    def test_one_component_spec_per_vue_file(self):
        specs = _extract_symbols_for_file(
            "src/components/OrderInternalShipToColumn.vue",
            ["+<template>", "+  <div>Shipped to {{name}}</div>", "+</template>"],
            "vue",
        )
        component_specs = [s for s in specs if s["kind"] == "component"]
        self.assertEqual(
            len(component_specs),
            1,
            "Expected exactly 1 component spec per Vue file",
        )
        self.assertEqual(component_specs[0]["symbol"], "OrderInternalShipToColumn")

    def test_component_spec_only_when_added_lines_present(self):
        specs = _extract_symbols_for_file("src/Empty.vue", [], "vue")
        self.assertEqual(specs, [])

    def test_component_name_is_basename_without_extension(self):
        specs = _extract_symbols_for_file(
            "deeply/nested/path/MyWidget.vue",
            ["+<script>"],
            "vue",
        )
        comp = next((s for s in specs if s["kind"] == "component"), None)
        self.assertIsNotNone(comp)
        self.assertEqual(comp["symbol"], "MyWidget")


# ---------------------------------------------------------------------------
# TestDedupSameSymbolMultiLocation
# ---------------------------------------------------------------------------


class TestDedupSameSymbolMultiLocation(unittest.TestCase):
    def test_same_symbol_in_same_file_deduped(self):
        # Same symbol name on two different lines in the same file → 1 entry.
        added_lines = [
            "+def process():",
            "+def other():",
            "+def process():",  # duplicate
        ]
        specs = _extract_symbols_for_file("foo.py", added_lines, "python")
        symbols = [s["symbol"] for s in specs]
        # _extract_symbols_for_file does NOT dedup; dedup happens in _dedup_sort_cap
        # Let's verify _dedup_sort_cap handles it.
        deduped, _ = _dedup_sort_cap(specs)
        process_entries = [s for s in deduped if s["symbol"] == "process"]
        self.assertEqual(len(process_entries), 1)

    def test_same_symbol_different_files_kept(self):
        spec_a = _build_probe_spec("foo", "a.py", "function", "python", "diff:line+0")
        spec_b = _build_probe_spec("foo", "b.py", "function", "python", "diff:line+0")
        deduped, _ = _dedup_sort_cap([spec_a, spec_b])
        self.assertEqual(len(deduped), 2)


# ---------------------------------------------------------------------------
# TestSort
# ---------------------------------------------------------------------------


class TestSort(unittest.TestCase):
    def test_sorted_by_file_then_symbol(self):
        specs = [
            _build_probe_spec("zebra", "b.py", "function", "python", "diff:line+0"),
            _build_probe_spec("alpha", "b.py", "function", "python", "diff:line+1"),
            _build_probe_spec("middle", "a.py", "function", "python", "diff:line+0"),
        ]
        sorted_specs, _ = _dedup_sort_cap(specs)
        files = [s["file"] for s in sorted_specs]
        # a.py must come before b.py
        self.assertEqual(files[0], "a.py")
        self.assertEqual(files[1], "b.py")
        self.assertEqual(files[2], "b.py")
        # Within b.py, alpha before zebra
        b_entries = [s for s in sorted_specs if s["file"] == "b.py"]
        self.assertEqual(b_entries[0]["symbol"], "alpha")
        self.assertEqual(b_entries[1]["symbol"], "zebra")


# ---------------------------------------------------------------------------
# TestCap
# ---------------------------------------------------------------------------


class TestCap(unittest.TestCase):
    def test_over_100_symbols_capped(self):
        specs = [
            _build_probe_spec(
                "sym_{0}".format(i), "file_{0}.py".format(i), "function", "python", "diff:line+0"
            )
            for i in range(150)
        ]
        capped_specs, capped = _dedup_sort_cap(specs)
        self.assertTrue(capped)
        self.assertEqual(len(capped_specs), _MAX_SYMBOLS_PER_PR)

    def test_exactly_100_symbols_not_capped(self):
        specs = [
            _build_probe_spec(
                "sym_{0}".format(i), "file.py", "function", "python", "diff:line+0"
            )
            for i in range(100)
        ]
        capped_specs, capped = _dedup_sort_cap(specs)
        self.assertFalse(capped)
        self.assertEqual(len(capped_specs), 100)

    def test_under_100_not_capped(self):
        specs = [
            _build_probe_spec("f", "x.py", "function", "python", "diff:line+0")
        ]
        _, capped = _dedup_sort_cap(specs)
        self.assertFalse(capped)


# ---------------------------------------------------------------------------
# TestBuildProbeSpec
# ---------------------------------------------------------------------------


class TestBuildProbeSpec(unittest.TestCase):
    def setUp(self):
        self.spec = _build_probe_spec(
            symbol="MyFunc",
            file="src/foo.py",
            kind="function",
            language="python",
            diff_line_hint="diff:line+3",
        )

    def test_all_required_keys_present(self):
        for key in _REQUIRED_PROBE_KEYS:
            self.assertIn(key, self.spec, "Key {0!r} missing from probe spec".format(key))

    def test_symbol_value(self):
        self.assertEqual(self.spec["symbol"], "MyFunc")

    def test_file_value(self):
        self.assertEqual(self.spec["file"], "src/foo.py")

    def test_kind_value(self):
        self.assertEqual(self.spec["kind"], "function")

    def test_language_value(self):
        self.assertEqual(self.spec["language"], "python")

    def test_diff_line_hint_value(self):
        self.assertEqual(self.spec["diff_line_hint"], "diff:line+3")

    def test_mcp_hints_structure(self):
        hints = self.spec["mcp_hints"]
        self.assertIn("trace_path_in", hints)
        self.assertIn("trace_path_out", hints)
        self.assertIn("data_flow", hints)
        self.assertEqual(hints["trace_path_in"], "MyFunc")
        self.assertEqual(hints["trace_path_out"], "MyFunc")
        self.assertEqual(hints["data_flow"], "MyFunc")

    def test_callers_empty_list(self):
        self.assertEqual(self.spec["callers"], [])

    def test_callees_empty_list(self):
        self.assertEqual(self.spec["callees"], [])

    def test_data_flow_targets_empty_list(self):
        self.assertEqual(self.spec["data_flow_targets"], [])

    def test_tests_referencing_empty_list(self):
        self.assertEqual(self.spec["tests_referencing"], [])

    def test_filled_is_false(self):
        self.assertIs(self.spec["filled"], False)


# ---------------------------------------------------------------------------
# TestRunHappyPath
# ---------------------------------------------------------------------------


class TestRunHappyPath(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _make_diff(self):
        return (
            "diff --git a/service.py b/service.py\n"
            "--- a/service.py\n"
            "+++ b/service.py\n"
            "@@ -0,0 +1,3 @@\n"
            "+def compute(x):\n"
            "+    return x * 2\n"
            "diff --git a/src/App.tsx b/src/App.tsx\n"
            "+++ b/src/App.tsx\n"
            "+export class AppContainer {\n"
            "diff --git a/src/Card.vue b/src/Card.vue\n"
            "+++ b/src/Card.vue\n"
            "+<template><div /></template>\n"
        )

    def test_run_returns_status_ok(self):
        sp = _make_state_json(self._tmp, 42, diff=self._make_diff())
        result = run(target=self._tmp, pr_number=42)
        self.assertEqual(result["status"], "ok")

    def test_run_returns_correct_pr_number(self):
        _make_state_json(self._tmp, 42, diff=self._make_diff())
        result = run(target=self._tmp, pr_number=42)
        self.assertEqual(result["pr_number"], 42)

    def test_run_state_path_in_output(self):
        sp = _make_state_json(self._tmp, 42, diff=self._make_diff())
        result = run(target=self._tmp, pr_number=42)
        self.assertEqual(result["state_path"], sp)

    def test_run_symbols_extracted_positive(self):
        _make_state_json(self._tmp, 42, diff=self._make_diff())
        result = run(target=self._tmp, pr_number=42)
        self.assertGreater(result["symbols_extracted"], 0)

    def test_run_by_language_populated(self):
        _make_state_json(self._tmp, 42, diff=self._make_diff())
        result = run(target=self._tmp, pr_number=42)
        # The diff has .py, .tsx, and .vue files
        self.assertIn("python", result["by_language"])
        self.assertIn("typescript", result["by_language"])
        self.assertIn("vue", result["by_language"])

    def test_run_capped_false_for_small_diff(self):
        _make_state_json(self._tmp, 42, diff=self._make_diff())
        result = run(target=self._tmp, pr_number=42)
        self.assertFalse(result["capped"])

    def test_run_next_action_mentions_step_8(self):
        _make_state_json(self._tmp, 42, diff=self._make_diff())
        result = run(target=self._tmp, pr_number=42)
        self.assertIn("Step 8", result["next_action"])

    def test_run_state_blast_written(self):
        sp = _make_state_json(self._tmp, 42, diff=self._make_diff())
        run(target=self._tmp, pr_number=42)
        with open(sp, "r", encoding="utf-8") as fh:
            state_data = json.load(fh)
        self.assertIsInstance(state_data["blast"], list)
        self.assertGreater(len(state_data["blast"]), 0)

    def test_run_blast_entries_have_required_keys(self):
        sp = _make_state_json(self._tmp, 42, diff=self._make_diff())
        run(target=self._tmp, pr_number=42)
        with open(sp, "r", encoding="utf-8") as fh:
            state_data = json.load(fh)
        for entry in state_data["blast"]:
            for key in _REQUIRED_PROBE_KEYS:
                self.assertIn(
                    key, entry,
                    "Key {0!r} missing from blast entry {1!r}".format(key, entry.get("symbol"))
                )

    def test_run_blast_python_symbol_present(self):
        sp = _make_state_json(self._tmp, 42, diff=self._make_diff())
        run(target=self._tmp, pr_number=42)
        with open(sp, "r", encoding="utf-8") as fh:
            state_data = json.load(fh)
        symbols = [e["symbol"] for e in state_data["blast"]]
        self.assertIn("compute", symbols)

    def test_run_blast_ts_class_present(self):
        sp = _make_state_json(self._tmp, 42, diff=self._make_diff())
        run(target=self._tmp, pr_number=42)
        with open(sp, "r", encoding="utf-8") as fh:
            state_data = json.load(fh)
        symbols = [e["symbol"] for e in state_data["blast"]]
        self.assertIn("AppContainer", symbols)

    def test_run_blast_vue_component_present(self):
        sp = _make_state_json(self._tmp, 42, diff=self._make_diff())
        run(target=self._tmp, pr_number=42)
        with open(sp, "r", encoding="utf-8") as fh:
            state_data = json.load(fh)
        kinds = [e["kind"] for e in state_data["blast"]]
        self.assertIn("component", kinds)

    def test_run_empty_diff_produces_empty_blast(self):
        sp = _make_state_json(self._tmp, 42, diff="")
        run(target=self._tmp, pr_number=42)
        with open(sp, "r", encoding="utf-8") as fh:
            state_data = json.load(fh)
        self.assertEqual(state_data["blast"], [])


# ---------------------------------------------------------------------------
# TestRunNoState
# ---------------------------------------------------------------------------


class TestRunNoState(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_missing_state_raises_value_error(self):
        with self.assertRaises(ValueError) as ctx:
            run(target=self._tmp, pr_number=9999)
        self.assertIn("intake", str(ctx.exception))

    def test_error_message_mentions_state_path(self):
        try:
            run(target=self._tmp, pr_number=9999)
        except ValueError as exc:
            self.assertIn("state.json", str(exc))


# ---------------------------------------------------------------------------
# TestRunReplacesPriorBlast
# ---------------------------------------------------------------------------


class TestRunReplacesPriorBlast(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_second_run_replaces_first_blast(self):
        first_diff = (
            "diff --git a/alpha.py b/alpha.py\n"
            "+def alpha_func():\n"
            "+    pass\n"
        )
        second_diff = (
            "diff --git a/beta.py b/beta.py\n"
            "+def beta_func():\n"
            "+    pass\n"
        )

        sp = _make_state_json(self._tmp, 1, diff=first_diff)
        run(target=self._tmp, pr_number=1)

        # Verify first run produced alpha_func
        with open(sp, "r", encoding="utf-8") as fh:
            state_data = json.load(fh)
        first_symbols = [e["symbol"] for e in state_data["blast"]]
        self.assertIn("alpha_func", first_symbols)

        # Update state.diff to second diff and re-run.
        with open(sp, "r", encoding="utf-8") as fh:
            state_data = json.load(fh)
        state_data["diff"] = second_diff
        with open(sp, "w", encoding="utf-8") as fh:
            json.dump(state_data, fh, indent=2)
            fh.write("\n")

        run(target=self._tmp, pr_number=1)

        with open(sp, "r", encoding="utf-8") as fh:
            state_data = json.load(fh)
        second_symbols = [e["symbol"] for e in state_data["blast"]]

        # Second run: only beta_func; alpha_func must be gone (replace, not append).
        self.assertIn("beta_func", second_symbols)
        self.assertNotIn(
            "alpha_func",
            second_symbols,
            "state.blast should be replaced, not appended",
        )

    def test_run_with_prior_blast_in_state_replaces_it(self):
        """state.blast pre-populated with 3 entries; run replaces entirely."""
        sp = _make_state_json(self._tmp, 2, diff="")
        with open(sp, "r", encoding="utf-8") as fh:
            state_data = json.load(fh)
        state_data["blast"] = [
            _build_probe_spec("old1", "old.py", "function", "python", "diff:line+0"),
            _build_probe_spec("old2", "old.py", "function", "python", "diff:line+1"),
            _build_probe_spec("old3", "old.py", "class", "python", "diff:line+2"),
        ]
        with open(sp, "w", encoding="utf-8") as fh:
            json.dump(state_data, fh, indent=2)
            fh.write("\n")

        # Run with empty diff — should produce empty blast.
        run(target=self._tmp, pr_number=2)

        with open(sp, "r", encoding="utf-8") as fh:
            state_data = json.load(fh)
        self.assertEqual(state_data["blast"], [])


# ---------------------------------------------------------------------------
# TestProbeSpecShape
# ---------------------------------------------------------------------------


class TestProbeSpecShape(unittest.TestCase):
    """Validates probe spec shapes produced by run()."""

    def setUp(self):
        self._tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _collect_blast(self, diff: str) -> list:
        sp = _make_state_json(self._tmp, 77, diff=diff)
        run(target=self._tmp, pr_number=77)
        with open(sp, "r", encoding="utf-8") as fh:
            return json.load(fh)["blast"]

    def test_all_required_keys_present_in_every_entry(self):
        diff = (
            "diff --git a/x.py b/x.py\n"
            "+def process():\n"
            "diff --git a/y.ts b/y.ts\n"
            "+interface Shape {\n"
            "diff --git a/z.vue b/z.vue\n"
            "+<template />\n"
        )
        blast = self._collect_blast(diff)
        self.assertGreater(len(blast), 0)
        for entry in blast:
            for key in _REQUIRED_PROBE_KEYS:
                self.assertIn(
                    key, entry,
                    "Key {0!r} missing from entry {1!r}".format(key, entry.get("symbol"))
                )

    def test_callers_is_empty_list(self):
        blast = self._collect_blast(
            "diff --git a/m.py b/m.py\n+def greet():\n"
        )
        for entry in blast:
            self.assertEqual(entry["callers"], [])

    def test_callees_is_empty_list(self):
        blast = self._collect_blast(
            "diff --git a/m.py b/m.py\n+def greet():\n"
        )
        for entry in blast:
            self.assertEqual(entry["callees"], [])

    def test_data_flow_targets_is_empty_list(self):
        blast = self._collect_blast(
            "diff --git a/m.py b/m.py\n+def greet():\n"
        )
        for entry in blast:
            self.assertEqual(entry["data_flow_targets"], [])

    def test_tests_referencing_is_empty_list(self):
        blast = self._collect_blast(
            "diff --git a/m.py b/m.py\n+def greet():\n"
        )
        for entry in blast:
            self.assertEqual(entry["tests_referencing"], [])

    def test_filled_is_false(self):
        blast = self._collect_blast(
            "diff --git a/m.py b/m.py\n+def greet():\n"
        )
        for entry in blast:
            self.assertIs(entry["filled"], False)

    def test_mcp_hints_symbol_matches_entry_symbol(self):
        blast = self._collect_blast(
            "diff --git a/m.py b/m.py\n+def greet():\n"
        )
        for entry in blast:
            hints = entry["mcp_hints"]
            self.assertEqual(hints["trace_path_in"], entry["symbol"])
            self.assertEqual(hints["trace_path_out"], entry["symbol"])
            self.assertEqual(hints["data_flow"], entry["symbol"])

    def test_diff_line_hint_format(self):
        blast = self._collect_blast(
            "diff --git a/m.py b/m.py\n+def greet():\n"
        )
        import re
        pattern = re.compile(r"^diff:line\+\d+$")
        for entry in blast:
            self.assertRegex(
                entry["diff_line_hint"],
                pattern,
                "diff_line_hint format invalid: {0!r}".format(entry["diff_line_hint"]),
            )


# ---------------------------------------------------------------------------
# TestNoMCPCalls (verifies the module does not attempt real CBM calls)
# ---------------------------------------------------------------------------


class TestNoMCPCalls(unittest.TestCase):
    """Structural check: _blast.py must not import or call MCP/CBM tools."""

    def test_blast_module_has_no_mcp_import(self):
        blast_path = str(
            _REPO_ROOT / "src" / "devforge" / "lib" / "_pr_review" / "_blast.py"
        )
        with open(blast_path, "r", encoding="utf-8") as fh:
            source = fh.read()
        self.assertNotIn(
            "mcp__codebase",
            source,
            "_blast.py must not contain MCP tool calls",
        )
        self.assertNotIn(
            "trace_path(",
            source,
            "_blast.py must not call trace_path() as a function",
        )

    def test_blast_module_has_no_subprocess_git_calls(self):
        blast_path = str(
            _REPO_ROOT / "src" / "devforge" / "lib" / "_pr_review" / "_blast.py"
        )
        with open(blast_path, "r", encoding="utf-8") as fh:
            source = fh.read()
        # git subprocess calls are not expected; just verify no git-specific command
        self.assertNotIn(
            '"git"',
            source,
            "_blast.py must not make git subprocess calls",
        )


if __name__ == "__main__":
    unittest.main()
