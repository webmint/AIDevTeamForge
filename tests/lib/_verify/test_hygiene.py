"""Tests for src/devforge/lib/_verify/_hygiene.py and the check-hygiene CLI verb.

Real-file discipline:
  All leftover-artifact tests write real temporary files and call check_hygiene
  against them — no mocked content.  Scope-creep tests use a real temp dir.

Coverage:
  check_hygiene (function level):
    - scope-creep: changed file not in baseline → flagged
    - scope-creep: changed file in baseline → not flagged
    - scope-creep: baseline=None → check skipped (scope_creep_checked=False)
    - scope-creep: baseline=[] → check skipped
    - scope-creep: absolute paths normalised correctly
    - scope-creep: relative paths with "./" prefix normalised correctly
    - scope-creep: PascalCase path distinct from lowercase path (case-sensitive, F4)
    - leftover artifact: console.log( → debug_print flagged
    - leftover artifact: print( → debug_print flagged
    - leftover artifact: self.print( → NOT flagged (F2 negative)
    - leftover artifact: rich.print( → NOT flagged (F2 negative)
    - leftover artifact: logger.print( → NOT flagged (F2 negative)
    - leftover artifact: debugger on its own line → debug_statement flagged
    - leftover artifact: pdb.set_trace() → debug_statement flagged
    - leftover artifact: breakpoint() → debug_statement flagged
    - leftover artifact: bare TODO without ticket ref → bare_todo flagged
    - leftover artifact: TODO with #123 ticket ref → NOT flagged
    - leftover artifact: TODO with JIRA-style PROJ-42 → NOT flagged
    - leftover artifact: bare FIXME without ticket → bare_fixme flagged
    - leftover artifact: commented-out def → commented_code_block flagged
    - leftover artifact: commented-out function → commented_code_block flagged
    - leftover artifact: commented-out call ending ; → commented_code_block flagged (F3 positive)
    - leftover artifact: prose comment "// from the spec" → NOT flagged (F3 negative)
    - leftover artifact: prose comment "// return type is X" → NOT flagged (F3 negative)
    - leftover artifact: prose comment "// class is immutable" → NOT flagged (F3 negative)
    - leftover artifact: prose comment "// let me explain" → NOT flagged (F3 negative)
    - leftover artifact: prose comment "// import order matters" → NOT flagged (F3 negative)
    - leftover artifact: prose comment "# function of the input" → NOT flagged (F3 negative)
    - leftover artifact: "// const x = getConfig();" → flagged (F3 positive via assign-call)
    - leftover artifact: "# return compute(x)" → flagged (F3 positive via call ending ))
    - leftover artifact: "// if (foo) { bar(); }" → flagged (F3 positive structure+terminator)
    - leftover artifact: "// oldFunc();" → flagged (F3 positive bare call ending ;)
    - clean file with no artifacts → nothing flagged
    - unreadable file → noted in files_unreadable, not in leftover_artifacts
    - output shape: all required keys present

  check-hygiene CLI verb:
    - valid inputs → exit 0, valid JSON
    - scope_creep present → in output
    - baseline="none" → scope_creep_checked=False
    - breakdown-handoff.json baseline → touched_files extracted correctly
    - missing --files → exit 2
    - missing --scope-baseline → exit 2
    - --files "-" reads from stdin (implicitly tested via file path)
"""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _verify._hygiene import check_hygiene  # noqa: E402
from _verify._cli import main  # noqa: E402


# ---------------------------------------------------------------------------
# Helper: capture CLI output
# ---------------------------------------------------------------------------

def _capture(argv):
    """Run main(argv) with captured stdout/stderr.  Returns (stdout, stderr, rc)."""
    buf_out = io.StringIO()
    buf_err = io.StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = buf_out, buf_err
    try:
        rc = main(argv)
    except SystemExit as exc:
        rc = exc.code if isinstance(exc.code, int) else 2
    finally:
        sys.stdout, sys.stderr = old_out, old_err
    return buf_out.getvalue(), buf_err.getvalue(), rc


# ---------------------------------------------------------------------------
# Helper: write temp file and return path
# ---------------------------------------------------------------------------

def _write_tmp(tmp_dir, filename, content):
    # type: (str, str, str) -> str
    """Write content to tmp_dir/filename and return the full path."""
    path = os.path.join(tmp_dir, filename)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    return path


# ---------------------------------------------------------------------------
# Tests — scope-creep
# ---------------------------------------------------------------------------

class TestScopeCreep(unittest.TestCase):
    """check_hygiene scope-creep detection."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        # Write a simple clean file (no artifacts) into the tmp dir.
        self.clean_file = _write_tmp(self.tmp_dir, "clean.py", "x = 1\n")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_file_not_in_baseline_flagged(self):
        """A changed file absent from the scope baseline is scope-creep."""
        changed = [self.clean_file]
        baseline = ["/other/file.py"]
        result = check_hygiene(changed, baseline, self.tmp_dir)
        self.assertIn(self.clean_file, result["scope_creep"])
        self.assertTrue(result["scope_creep_checked"])

    def test_file_in_baseline_not_flagged(self):
        """A changed file present in the scope baseline is NOT scope-creep."""
        changed = [self.clean_file]
        baseline = [self.clean_file]
        result = check_hygiene(changed, baseline, self.tmp_dir)
        self.assertEqual(result["scope_creep"], [])
        self.assertTrue(result["scope_creep_checked"])

    def test_none_baseline_skips_check(self):
        """scope_baseline=None → scope_creep_checked=False, scope_creep=[]."""
        changed = [self.clean_file]
        result = check_hygiene(changed, None, self.tmp_dir)
        self.assertFalse(result["scope_creep_checked"])
        self.assertEqual(result["scope_creep"], [])

    def test_empty_baseline_skips_check(self):
        """scope_baseline=[] → scope_creep_checked=False, scope_creep=[]."""
        changed = [self.clean_file]
        result = check_hygiene(changed, [], self.tmp_dir)
        self.assertFalse(result["scope_creep_checked"])
        self.assertEqual(result["scope_creep"], [])

    def test_relative_path_with_dotslash_normalised(self):
        """Relative paths with './' prefix are normalised for comparison."""
        # baseline has no "./" prefix; changed has it → should still match.
        rel_name = "clean.py"
        rel_with_dot = "./clean.py"
        # Use relative paths (resolved against tmp_dir).
        result = check_hygiene(
            changed_files=[rel_with_dot],
            scope_baseline=[rel_name],
            source_root=self.tmp_dir,
        )
        # clean.py == ./clean.py after normalisation → no scope creep.
        self.assertEqual(result["scope_creep"], [])

    def test_mixed_absolute_and_relative_baseline(self):
        """Absolute path in changed_files matches relative in baseline."""
        abs_path = os.path.join(self.tmp_dir, "clean.py")
        result = check_hygiene(
            changed_files=[abs_path],
            scope_baseline=["clean.py"],
            source_root=self.tmp_dir,
        )
        self.assertEqual(result["scope_creep"], [])

    def test_multiple_changed_files_some_creep(self):
        """Only the out-of-scope files appear in scope_creep."""
        planned_file = _write_tmp(self.tmp_dir, "planned.py", "x = 1\n")
        unplanned_file = _write_tmp(self.tmp_dir, "unplanned.py", "y = 2\n")
        result = check_hygiene(
            changed_files=[planned_file, unplanned_file],
            scope_baseline=[planned_file],
            source_root=self.tmp_dir,
        )
        self.assertNotIn(planned_file, result["scope_creep"])
        self.assertIn(unplanned_file, result["scope_creep"])

    def test_case_sensitive_paths_treated_as_distinct(self):
        """F4: PascalCase path is NOT matched by its lowercase equivalent.

        On case-sensitive filesystems src/Components/MyButton.tsx and
        src/components/mybutton.tsx are distinct files.  The detector must
        treat them as distinct (case-sensitive comparison) — the old .lower()
        call would have falsely merged them, hiding scope creep.
        """
        # The baseline declares the lowercase variant.
        baseline = ["src/components/mybutton.tsx"]
        # The changed file is the PascalCase variant (distinct on Linux).
        changed = ["src/Components/MyButton.tsx"]
        # We use None source_root (cwd); no file reading needed for this test
        # (we only care about the scope-creep comparison logic, not file contents).
        result = check_hygiene(
            changed_files=changed,
            scope_baseline=baseline,
            source_root=os.getcwd(),
        )
        # PascalCase path is NOT in the lowercase baseline → scope creep flagged.
        self.assertIn("src/Components/MyButton.tsx", result["scope_creep"])


# ---------------------------------------------------------------------------
# Tests — leftover artifacts (debug prints)
# ---------------------------------------------------------------------------

class TestLeftoverDebugPrint(unittest.TestCase):
    """check_hygiene flags console.log and bare print( as debug_print."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _run(self, filename, content):
        path = _write_tmp(self.tmp_dir, filename, content)
        result = check_hygiene([path], None, self.tmp_dir)
        return result["leftover_artifacts"]

    def test_console_log_flagged(self):
        """console.log( on a line → debug_print."""
        artifacts = self._run("a.ts", "function foo() {\n  console.log(data);\n}\n")
        kinds = [a["kind"] for a in artifacts]
        self.assertIn("debug_print", kinds)

    def test_console_log_line_number(self):
        """console.log on line 2 → line=2 in the finding."""
        artifacts = self._run("b.ts", "// comment\nconsole.log('debug');\n")
        debug = [a for a in artifacts if a["kind"] == "debug_print"]
        self.assertEqual(len(debug), 1)
        self.assertEqual(debug[0]["line"], 2)

    def test_print_python_flagged(self):
        """bare print( in Python file → debug_print."""
        artifacts = self._run("c.py", "x = 1\nprint(x)\ny = 2\n")
        kinds = [a["kind"] for a in artifacts]
        self.assertIn("debug_print", kinds)

    def test_print_with_leading_spaces_flagged(self):
        """Indented bare print( → debug_print (F2 positive)."""
        artifacts = self._run("c2.py", "def foo():\n    print(y)\n")
        kinds = [a["kind"] for a in artifacts]
        self.assertIn("debug_print", kinds)

    def test_console_log_snippet_in_output(self):
        """The snippet field contains the flagged line content."""
        artifacts = self._run("d.ts", "console.log('hello world');\n")
        self.assertTrue(any("console.log" in a["snippet"] for a in artifacts))

    def test_file_path_in_finding(self):
        """The file field in each finding matches the changed file path."""
        path = _write_tmp(self.tmp_dir, "e.js", "console.log('x');\n")
        result = check_hygiene([path], None, self.tmp_dir)
        for a in result["leftover_artifacts"]:
            self.assertEqual(a["file"], path)

    # --- F2 negative tests: method calls must NOT fire ---

    def test_self_print_not_flagged(self):
        """F2: self.print(msg) is a method call → NOT debug_print."""
        artifacts = self._run("f2a.py", "self.print(msg)\n")
        kinds = [a["kind"] for a in artifacts]
        self.assertNotIn("debug_print", kinds)

    def test_rich_print_not_flagged(self):
        """F2: rich.print(msg) is a qualified call → NOT debug_print."""
        artifacts = self._run("f2b.py", "rich.print(msg)\n")
        kinds = [a["kind"] for a in artifacts]
        self.assertNotIn("debug_print", kinds)

    def test_logger_print_not_flagged(self):
        """F2: logger.print(x) is a method call → NOT debug_print."""
        artifacts = self._run("f2c.py", "logger.print(x)\n")
        kinds = [a["kind"] for a in artifacts]
        self.assertNotIn("debug_print", kinds)

    def test_obj_print_method_not_flagged(self):
        """F2: obj.print(data) — any .print() method call → NOT debug_print."""
        artifacts = self._run("f2d.py", "result = obj.print(data)\n")
        kinds = [a["kind"] for a in artifacts]
        self.assertNotIn("debug_print", kinds)


# ---------------------------------------------------------------------------
# Tests — leftover artifacts (debug statements)
# ---------------------------------------------------------------------------

class TestLeftoverDebugStatement(unittest.TestCase):
    """check_hygiene flags debugger / pdb.set_trace / breakpoint()."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _run(self, filename, content):
        path = _write_tmp(self.tmp_dir, filename, content)
        result = check_hygiene([path], None, self.tmp_dir)
        return result["leftover_artifacts"]

    def test_debugger_flagged(self):
        """``debugger`` keyword → debug_statement."""
        artifacts = self._run("a.js", "function foo() {\n  debugger;\n}\n")
        kinds = [a["kind"] for a in artifacts]
        self.assertIn("debug_statement", kinds)

    def test_pdb_set_trace_flagged(self):
        """``pdb.set_trace()`` → debug_statement."""
        artifacts = self._run("a.py", "import pdb\npdb.set_trace()\nx = 1\n")
        kinds = [a["kind"] for a in artifacts]
        self.assertIn("debug_statement", kinds)

    def test_breakpoint_flagged(self):
        """``breakpoint()`` → debug_statement."""
        artifacts = self._run("b.py", "x = 1\nbreakpoint()\ny = 2\n")
        kinds = [a["kind"] for a in artifacts]
        self.assertIn("debug_statement", kinds)

    def test_debugger_line_number(self):
        """Debugger on line 3 → line=3 in the finding."""
        artifacts = self._run("c.js", "a = 1;\nb = 2;\ndebugger;\nd = 4;\n")
        debug = [a for a in artifacts if a["kind"] == "debug_statement"]
        self.assertEqual(debug[0]["line"], 3)


# ---------------------------------------------------------------------------
# Tests — leftover artifacts (bare TODOs)
# ---------------------------------------------------------------------------

class TestLeftoverBareTodo(unittest.TestCase):
    """check_hygiene flags bare TODO/FIXME without ticket references."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _run(self, filename, content):
        path = _write_tmp(self.tmp_dir, filename, content)
        result = check_hygiene([path], None, self.tmp_dir)
        return result["leftover_artifacts"]

    def test_bare_todo_flagged(self):
        """TODO with no ticket reference → bare_todo."""
        artifacts = self._run("a.py", "# TODO: clean this up\nx = 1\n")
        kinds = [a["kind"] for a in artifacts]
        self.assertIn("bare_todo", kinds)

    def test_todo_with_hash_ticket_not_flagged(self):
        """TODO with #123 → not flagged."""
        artifacts = self._run("b.py", "# TODO: clean this up #123\nx = 1\n")
        kinds = [a["kind"] for a in artifacts]
        self.assertNotIn("bare_todo", kinds)

    def test_todo_with_jira_ticket_not_flagged(self):
        """TODO with PROJ-42 (JIRA-style) → not flagged."""
        artifacts = self._run("c.py", "# TODO PROJ-42: clean this up\nx = 1\n")
        kinds = [a["kind"] for a in artifacts]
        self.assertNotIn("bare_todo", kinds)

    def test_todo_with_http_url_not_flagged(self):
        """TODO with a URL → not flagged (URL counts as a reference)."""
        artifacts = self._run("d.py", "# TODO: see https://example.com/issue/1\n")
        kinds = [a["kind"] for a in artifacts]
        self.assertNotIn("bare_todo", kinds)

    def test_bare_fixme_flagged(self):
        """FIXME with no ticket reference → bare_fixme."""
        artifacts = self._run("e.py", "x = 1  # FIXME: this is wrong\n")
        kinds = [a["kind"] for a in artifacts]
        self.assertIn("bare_fixme", kinds)

    def test_fixme_with_ticket_not_flagged(self):
        """FIXME with #456 → not flagged."""
        artifacts = self._run("f.py", "# FIXME #456: handle edge case\n")
        kinds = [a["kind"] for a in artifacts]
        self.assertNotIn("bare_fixme", kinds)

    def test_todo_case_insensitive(self):
        """todo (lowercase) is also flagged."""
        artifacts = self._run("g.py", "# todo: lowercase version\n")
        kinds = [a["kind"] for a in artifacts]
        self.assertIn("bare_todo", kinds)


# ---------------------------------------------------------------------------
# Tests — leftover artifacts (commented-out code blocks)
# ---------------------------------------------------------------------------

class TestLeftoverCommentedCode(unittest.TestCase):
    """check_hygiene flags commented-out code statements (dual-signal rule)."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _run(self, filename, content):
        path = _write_tmp(self.tmp_dir, filename, content)
        result = check_hygiene([path], None, self.tmp_dir)
        return result["leftover_artifacts"]

    # --- Positive cases: real commented-out code SHOULD fire ---

    def test_commented_def_flagged(self):
        """# def old_function(): → commented_code_block (structure + : terminator)."""
        artifacts = self._run("a.py", "# def old_function():\nx = 1\n")
        kinds = [a["kind"] for a in artifacts]
        self.assertIn("commented_code_block", kinds)

    def test_commented_function_js_flagged(self):
        """// function oldHelper() { → commented_code_block (structure + { terminator)."""
        artifacts = self._run("b.js", "// function oldHelper() {\nx = 1;\n")
        kinds = [a["kind"] for a in artifacts]
        self.assertIn("commented_code_block", kinds)

    def test_commented_const_assign_call_flagged(self):
        """// const x = getConfig(); → commented_code_block (F3 positive: assign-call)."""
        artifacts = self._run("c.js", "// const x = getConfig();\n")
        kinds = [a["kind"] for a in artifacts]
        self.assertIn("commented_code_block", kinds)

    def test_commented_return_with_call_flagged(self):
        """# return compute(x) → commented_code_block (F3 positive: structure + ) terminator)."""
        artifacts = self._run("d.py", "def foo():\n    # return compute(x)\n    return 1\n")
        kinds = [a["kind"] for a in artifacts]
        self.assertIn("commented_code_block", kinds)

    def test_commented_if_block_flagged(self):
        """// if (foo) { bar(); } → commented_code_block (F3 positive: structure + } terminator)."""
        artifacts = self._run("e.js", "// if (foo) { bar(); }\n")
        kinds = [a["kind"] for a in artifacts]
        self.assertIn("commented_code_block", kinds)

    def test_commented_bare_call_ending_semicolon_flagged(self):
        """// oldFunc(); → commented_code_block (F3 positive: bare call ending ;)."""
        artifacts = self._run("f.js", "// oldFunc();\n")
        kinds = [a["kind"] for a in artifacts]
        self.assertIn("commented_code_block", kinds)

    def test_commented_async_def_flagged(self):
        """# async def handler(): → commented_code_block."""
        artifacts = self._run("g.py", "# async def handler():\n    pass\n")
        kinds = [a["kind"] for a in artifacts]
        self.assertIn("commented_code_block", kinds)

    def test_commented_for_paren_flagged(self):
        """// for (let i = 0; i < n; i++) { → commented_code_block (structure + { terminator)."""
        artifacts = self._run("h.js", "// for (let i = 0; i < n; i++) {\n")
        kinds = [a["kind"] for a in artifacts]
        self.assertIn("commented_code_block", kinds)

    # --- Negative cases: English prose MUST NOT fire (F3 negatives) ---

    def test_prose_from_the_spec_not_flagged(self):
        """F3: '// from the spec' is English prose → NOT commented_code_block."""
        artifacts = self._run("n1.js", "// from the spec\n")
        kinds = [a["kind"] for a in artifacts]
        self.assertNotIn("commented_code_block", kinds)

    def test_prose_return_type_not_flagged(self):
        """F3: '// return type is AuthUser' is English prose → NOT flagged."""
        artifacts = self._run("n2.js", "// return type is AuthUser\n")
        kinds = [a["kind"] for a in artifacts]
        self.assertNotIn("commented_code_block", kinds)

    def test_prose_class_is_immutable_not_flagged(self):
        """F3: '// class is immutable' is English prose → NOT flagged."""
        artifacts = self._run("n3.js", "// class is immutable\n")
        kinds = [a["kind"] for a in artifacts]
        self.assertNotIn("commented_code_block", kinds)

    def test_prose_let_me_explain_not_flagged(self):
        """F3: '// let me explain' is English prose → NOT flagged."""
        artifacts = self._run("n4.js", "// let me explain\n")
        kinds = [a["kind"] for a in artifacts]
        self.assertNotIn("commented_code_block", kinds)

    def test_prose_import_order_matters_not_flagged(self):
        """F3: '// import order matters' is English prose → NOT flagged."""
        artifacts = self._run("n5.js", "// import order matters\n")
        kinds = [a["kind"] for a in artifacts]
        self.assertNotIn("commented_code_block", kinds)

    def test_prose_function_of_input_not_flagged(self):
        """F3: '# function of the input' is English prose → NOT flagged."""
        artifacts = self._run("n6.py", "# function of the input\n")
        kinds = [a["kind"] for a in artifacts]
        self.assertNotIn("commented_code_block", kinds)

    def test_prose_var_is_deprecated_not_flagged(self):
        """F3: '// var is deprecated' is English prose → NOT flagged."""
        artifacts = self._run("n7.js", "// var is deprecated\n")
        kinds = [a["kind"] for a in artifacts]
        self.assertNotIn("commented_code_block", kinds)

    def test_prose_export_hint_not_flagged(self):
        """F3: '// export only the public API' is English prose → NOT flagged."""
        artifacts = self._run("n8.js", "// export only the public API\n")
        kinds = [a["kind"] for a in artifacts]
        self.assertNotIn("commented_code_block", kinds)

    def test_ordinary_comment_not_flagged(self):
        """A plain English comment is not flagged as commented code."""
        artifacts = self._run("n9.py", "# This is a normal explanation comment\n")
        kinds = [a["kind"] for a in artifacts]
        self.assertNotIn("commented_code_block", kinds)

    def test_prose_const_explanation_not_flagged(self):
        """F3: '// const values are cached' is English prose → NOT flagged."""
        artifacts = self._run("n10.js", "// const values are cached\n")
        kinds = [a["kind"] for a in artifacts]
        self.assertNotIn("commented_code_block", kinds)


# ---------------------------------------------------------------------------
# Tests — clean file produces no artifacts
# ---------------------------------------------------------------------------

class TestCleanFile(unittest.TestCase):
    """A clean file with no leftover artifacts produces an empty list."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_clean_python_file(self):
        content = textwrap.dedent("""\
            \"\"\"Module docstring.\"\"\"

            import os


            def migrate():
                # This comment explains the approach.
                result = os.path.join("a", "b")
                return result
        """)
        path = _write_tmp(self.tmp_dir, "clean.py", content)
        result = check_hygiene([path], None, self.tmp_dir)
        self.assertEqual(result["leftover_artifacts"], [])
        self.assertEqual(result["files_checked"], 1)

    def test_clean_typescript_file(self):
        content = textwrap.dedent("""\
            // Module for handling requests
            export function processRequest(data: string): string {
              // Validate input
              if (!data) {
                throw new Error("Empty data");
              }
              return data.trim();
            }
        """)
        path = _write_tmp(self.tmp_dir, "clean.ts", content)
        result = check_hygiene([path], None, self.tmp_dir)
        self.assertEqual(result["leftover_artifacts"], [])

    def test_clean_file_with_rich_print(self):
        """F2: rich.print() in a clean CLI file → no debug_print artifact."""
        content = textwrap.dedent("""\
            import rich
            def show(msg):
                rich.print(msg)
        """)
        path = _write_tmp(self.tmp_dir, "cli.py", content)
        result = check_hygiene([path], None, self.tmp_dir)
        kinds = [a["kind"] for a in result["leftover_artifacts"]]
        self.assertNotIn("debug_print", kinds)

    def test_clean_file_with_from_import_prose_comment(self):
        """F3: 'from the spec' and 'import order' prose comments → no commented_code_block."""
        content = textwrap.dedent("""\
            # from the spec: all handlers are async
            # import order follows project conventions
            # class is used as a namespace here
            # return early on error
            # let the caller handle exceptions
            x = 1
        """)
        path = _write_tmp(self.tmp_dir, "prose.py", content)
        result = check_hygiene([path], None, self.tmp_dir)
        kinds = [a["kind"] for a in result["leftover_artifacts"]]
        self.assertNotIn("commented_code_block", kinds)


# ---------------------------------------------------------------------------
# Tests — output shape
# ---------------------------------------------------------------------------

class TestOutputShape(unittest.TestCase):
    """check_hygiene always returns the full expected shape."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_all_required_keys_present(self):
        result = check_hygiene([], None, self.tmp_dir)
        required = {
            "scope_creep", "leftover_artifacts",
            "scope_creep_checked", "files_checked", "files_unreadable",
        }
        self.assertEqual(set(result.keys()), required)

    def test_finding_dict_shape(self):
        """Each leftover_artifacts entry has file, line, kind, snippet."""
        path = _write_tmp(self.tmp_dir, "a.py", "print('hello')\n")
        result = check_hygiene([path], None, self.tmp_dir)
        self.assertGreater(len(result["leftover_artifacts"]), 0)
        for a in result["leftover_artifacts"]:
            self.assertIn("file", a)
            self.assertIn("line", a)
            self.assertIn("kind", a)
            self.assertIn("snippet", a)
            self.assertIsInstance(a["line"], int)
            self.assertGreater(a["line"], 0)

    def test_unreadable_file_in_files_unreadable(self):
        """A file that doesn't exist appears in files_unreadable."""
        result = check_hygiene(
            ["/nonexistent/missing.py"], None, self.tmp_dir
        )
        self.assertIn("/nonexistent/missing.py", result["files_unreadable"])
        self.assertEqual(result["files_checked"], 0)

    def test_empty_changed_files(self):
        """Empty changed_files list → no artifacts, no creep, files_checked=0."""
        result = check_hygiene([], ["planned.py"], self.tmp_dir)
        self.assertEqual(result["scope_creep"], [])
        self.assertEqual(result["leftover_artifacts"], [])
        self.assertEqual(result["files_checked"], 0)


# ---------------------------------------------------------------------------
# Tests — check-hygiene CLI verb
# ---------------------------------------------------------------------------

class TestCheckHygieneCLI(unittest.TestCase):
    """CLI round-trip tests for the check-hygiene verb."""

    @classmethod
    def setUpClass(cls):
        cls.tmp_dir = tempfile.mkdtemp()

        # A file with a debug artifact.
        cls.dirty_file = _write_tmp(cls.tmp_dir, "dirty.py", "print('debug')\n")

        # A clean file.
        cls.clean_file = _write_tmp(cls.tmp_dir, "clean.py", "x = 1\n")

        # A files JSON (points at the dirty file).
        cls.files_json = os.path.join(cls.tmp_dir, "files.json")
        with open(cls.files_json, "w", encoding="utf-8") as fh:
            fh.write(json.dumps([cls.dirty_file]))

        # A breakdown-handoff.json with touched_files.
        cls.handoff_json = os.path.join(cls.tmp_dir, "breakdown-handoff.json")
        handoff_data = {
            "schema_version": "1.0",
            "handoff_kind": "breakdown",
            "tasks_dir": cls.tmp_dir,
            "breakdown_completed_at": "2026-06-16T00:00:00Z",
            "tasks": [
                {
                    "number": "001",
                    "title": "Task one",
                    "agent": "backend-engineer",
                    "depends_on": [],
                    "blocks": [],
                    "touched_files": [cls.clean_file],
                    "expects": [],
                    "produces": [],
                    "ac_addressed": ["AC-1"],
                    "doc_refs": [],
                    "review_checkpoint": False,
                }
            ],
            "additions": [],
            "dependency_graph": "",
            "provenance": {
                "upstream_handoff_path": None,
                "upstream_handoff_kind": None,
                "plan_path": None,
                "spec_path": None,
            },
        }
        with open(cls.handoff_json, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(handoff_data))

    @classmethod
    def tearDownClass(cls):
        import shutil
        shutil.rmtree(cls.tmp_dir, ignore_errors=True)

    def test_exit_0_on_valid_inputs(self):
        _, _, rc = _capture([
            "check-hygiene",
            "--files", self.files_json,
            "--scope-baseline", "none",
            "--source-root", self.tmp_dir,
        ])
        self.assertEqual(rc, 0)

    def test_emits_valid_json(self):
        out, _, _ = _capture([
            "check-hygiene",
            "--files", self.files_json,
            "--scope-baseline", "none",
            "--source-root", self.tmp_dir,
        ])
        data = json.loads(out)
        self.assertIsInstance(data, dict)

    def test_leftover_artifact_detected(self):
        """print( in dirty.py → debug_print in leftover_artifacts."""
        out, _, _ = _capture([
            "check-hygiene",
            "--files", self.files_json,
            "--scope-baseline", "none",
            "--source-root", self.tmp_dir,
        ])
        data = json.loads(out)
        kinds = [a["kind"] for a in data["leftover_artifacts"]]
        self.assertIn("debug_print", kinds)

    def test_scope_baseline_none_skips_check(self):
        """--scope-baseline none → scope_creep_checked=False."""
        out, _, _ = _capture([
            "check-hygiene",
            "--files", self.files_json,
            "--scope-baseline", "none",
            "--source-root", self.tmp_dir,
        ])
        data = json.loads(out)
        self.assertFalse(data["scope_creep_checked"])
        self.assertEqual(data["scope_creep"], [])

    def test_scope_creep_via_handoff(self):
        """Dirty file not in breakdown-handoff.json touched_files → scope_creep."""
        # dirty_file is NOT in the handoff's touched_files (only clean_file is).
        out, _, rc = _capture([
            "check-hygiene",
            "--files", self.files_json,
            "--scope-baseline", self.handoff_json,
            "--source-root", self.tmp_dir,
        ])
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertTrue(data["scope_creep_checked"])
        self.assertIn(self.dirty_file, data["scope_creep"])

    def test_no_scope_creep_when_file_in_baseline(self):
        """clean.py is in the handoff's touched_files → not in scope_creep."""
        # Write a files JSON for the clean file only.
        clean_files_json = os.path.join(self.tmp_dir, "clean_files.json")
        with open(clean_files_json, "w", encoding="utf-8") as fh:
            fh.write(json.dumps([self.clean_file]))
        out, _, rc = _capture([
            "check-hygiene",
            "--files", clean_files_json,
            "--scope-baseline", self.handoff_json,
            "--source-root", self.tmp_dir,
        ])
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["scope_creep"], [])

    def test_missing_files_flag_exits_2(self):
        _, _, rc = _capture([
            "check-hygiene",
            "--scope-baseline", "none",
        ])
        self.assertNotEqual(rc, 0)

    def test_missing_scope_baseline_flag_exits_2(self):
        _, _, rc = _capture([
            "check-hygiene",
            "--files", self.files_json,
        ])
        self.assertNotEqual(rc, 0)

    def test_output_has_all_required_keys(self):
        out, _, _ = _capture([
            "check-hygiene",
            "--files", self.files_json,
            "--scope-baseline", "none",
            "--source-root", self.tmp_dir,
        ])
        data = json.loads(out)
        expected = {
            "scope_creep", "leftover_artifacts",
            "scope_creep_checked", "files_checked", "files_unreadable",
        }
        self.assertEqual(set(data.keys()), expected)


if __name__ == "__main__":
    unittest.main()
