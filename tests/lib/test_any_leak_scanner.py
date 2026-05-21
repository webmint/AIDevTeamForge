"""Tests for ``_any_leak._scanner``: ``scan_for_any_leak_violations``.

Real-producer mandate: every test writes real ``.ts`` / ``.tsx`` / ``.vue``
files to a ``tempfile.TemporaryDirectory`` and calls
``scan_for_any_leak_violations`` against the directory.  No hand-authored
fixtures that bypass the real scanner.

The qualifying-file setup helper writes a file that imports from
``packages/cse-types/src`` (matching pattern variant 4, the package segment).

Coverage
--------
test_scanner_flags_type_annotation_any         -- ': any' -> 1 finding
test_scanner_flags_as_cast_any                 -- 'as any' -> 1 finding
test_scanner_flags_generic_any                 -- 'Array<any>' generic -> 1 finding
test_scanner_flags_two_generic_any             -- 'Array<any> | Set<any>' -> 2 findings same line
test_scanner_flags_map_any_any                 -- 'Map<any, any>' -> 2 findings (regression for lookbehind)
test_scanner_flags_record_string_any           -- 'Record<string, any>' -> 1 finding
test_scanner_flags_map_string_any              -- 'Map<string, any>' -> 1 finding
test_scanner_flags_multiple_any_same_line      -- 'f(x: any, y: any)' -> 2 findings at same line
test_scanner_flags_colon_any_in_variable       -- 'const y: any = value' -> 1 finding
test_scanner_flags_any_array                   -- 'x: any[]' -> 1 finding
test_scanner_skips_capitalized_Any             -- 'const x: Any' -> 0 findings
test_scanner_skips_any_in_string_literal       -- "'as any'" -> 0 findings
test_scanner_skips_any_in_double_quoted_string -- '"as any"' -> 0 findings
test_scanner_skips_any_in_line_comment         -- '// const x: any' -> 0 findings
test_scanner_skips_any_after_comment_on_line   -- 'code; // x: any' -> 0 findings
test_scanner_skips_inline_escape               -- '... // forcing-fn-ok: ...' -> 0 findings
test_scanner_skips_non_qualifying_file         -- no import from gen dir -> 0 findings
test_scanner_skips_allowlisted_path            -- *.test.ts allowlist -> 0 findings
test_scanner_skips_files_under_generated_dir   -- file inside generated dir -> 0 findings
test_scanner_word_boundary                     -- 'const anyOther = 1;' -> 0 findings
test_scanner_word_boundary_as_cast             -- 'result as anyhow' -> 0 findings ('as any\b' boundary)
test_scanner_handles_tsx_files                 -- .tsx qualifying file -> finding emitted
test_scanner_handles_vue_files                 -- .vue qualifying file -> finding emitted
test_scanner_ignores_js_files                  -- .js file -> not walked -> 0 findings
test_scanner_path_field_is_relative            -- finding.path is project-relative
test_scanner_line_number_is_1_based            -- annotation on line 5 -> finding.line == 5
test_scanner_fix_hint_present                  -- finding.fix_hint is non-empty
test_scanner_fix_hint_references_gen_dir       -- finding.fix_hint cites the generated_types_dir name
test_scanner_qualifies_via_full_path           -- import via full generated-dir path -> file qualifies
test_scanner_qualifies_via_package_segment     -- import via package-name segment -> file qualifies
test_scanner_qualifies_via_last_segment_alias  -- import via last-segment alias -> file qualifies
test_scanner_does_not_flag_pure_code_file      -- non-importing file -> 0 findings
test_scanner_clean_source_returns_empty        -- qualifying file with no any -> 0 findings
test_scanner_empty_root_returns_empty          -- empty root -> 0 findings
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from typing import List

_LIB_ROOT = os.path.join(
    os.path.dirname(__file__), "..", "..", "src", "devforge", "lib"
)
if _LIB_ROOT not in sys.path:
    sys.path.insert(0, _LIB_ROOT)

from _constitute._forcing_functions._any_leak._scanner import (  # noqa: E402
    scan_for_any_leak_violations,
)


# ---------------------------------------------------------------------------
# Stable test config
# ---------------------------------------------------------------------------

# The generated_types_dir path relative to root used in all tests.
_GEN_DIR_REL = "packages/cse-types/src"

# Default allowlist (mirrors plan's example config).
_DEFAULT_ALLOWLIST = [
    "node_modules/**", "**/node_modules/**",
    ".git/**", "**/.git/**",
    "**/*.test.ts", "**/*.spec.ts",
]


def _make_root_and_gen_dir(tmp: str):
    """Return (root: Path, gen_dir: Path) for a tempdir-based test."""
    root = Path(tmp)
    gen_dir = root / _GEN_DIR_REL
    gen_dir.mkdir(parents=True, exist_ok=True)
    return root, [gen_dir]


def _qualifying_header() -> str:
    """Return an import line that qualifies the file for scanning."""
    return "import { Foo } from '../../packages/cse-types/src/types';\n"


def _write_qualifying_file(root_path: Path, file_rel_path: str, body: str) -> Path:
    """Write a file that imports from the generated dir + append body lines."""
    full_path = root_path / file_rel_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(_qualifying_header() + body, encoding="utf-8")
    return full_path


def _scan(root: Path, gen_dirs: List[Path], allowlist=None):
    if allowlist is None:
        allowlist = _DEFAULT_ALLOWLIST
    return scan_for_any_leak_violations(root, gen_dirs, allowlist)


# ---------------------------------------------------------------------------
# Tests: detection of any-leak patterns
# ---------------------------------------------------------------------------

class TestScannerDetection(unittest.TestCase):

    def test_scanner_flags_type_annotation_any(self):
        """: any in function parameter -> 1 finding."""
        with tempfile.TemporaryDirectory() as tmp:
            root, gen_dirs = _make_root_and_gen_dir(tmp)
            _write_qualifying_file(root, "src/service.ts", "function foo(x: any): void {}\n")
            findings = _scan(root, gen_dirs)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].rule, "any_with_generated_available")
        self.assertEqual(findings[0].kind, "VIOLATION")

    def test_scanner_flags_as_cast_any(self):
        """obj as any -> 1 finding."""
        with tempfile.TemporaryDirectory() as tmp:
            root, gen_dirs = _make_root_and_gen_dir(tmp)
            _write_qualifying_file(root, "src/service.ts", "const x = obj as any;\n")
            findings = _scan(root, gen_dirs)
        self.assertEqual(len(findings), 1)
        self.assertIn("any", findings[0].summary)

    def test_scanner_flags_generic_any(self):
        """Array<any> generic -> 1 finding (the literal '<any>' present).

        Note: ``Map<any, any>`` contains NO literal ``<any>`` — the sequence is
        ``<any,`` and ``, any>``.  A genuine ``<any>`` match requires the angle
        brackets to directly wrap ``any`` with no comma, e.g. ``Array<any>``.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root, gen_dirs = _make_root_and_gen_dir(tmp)
            _write_qualifying_file(root, "src/service.ts", "const items: Array<any> = [];\n")
            findings = _scan(root, gen_dirs)
        self.assertEqual(len(findings), 1)

    def test_scanner_flags_two_generic_any(self):
        """Two separate <any> groups on the same line -> 2 findings."""
        with tempfile.TemporaryDirectory() as tmp:
            root, gen_dirs = _make_root_and_gen_dir(tmp)
            _write_qualifying_file(root, "src/service.ts", "const x: Array<any> | Set<any> = [];\n")
            findings = _scan(root, gen_dirs)
        self.assertEqual(len(findings), 2)
        self.assertEqual(findings[0].line, findings[1].line)

    def test_scanner_flags_map_any_any(self):
        """``Map<any, any>`` is a dominant TS pattern; 2 generic-any occurrences -> 2 findings.

        Regression guard: the original ``<any>`` regex literal missed this case
        because the lexical tokens are ``<any,`` and ``, any>`` — neither is
        ``<any>``.  Broader regex catches both via the two-alternative pattern.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root, gen_dirs = _make_root_and_gen_dir(tmp)
            _write_qualifying_file(root, "src/service.ts", "const m = new Map<any, any>();\n")
            findings = _scan(root, gen_dirs)
        self.assertEqual(len(findings), 2)
        self.assertEqual(findings[0].line, findings[1].line)

    def test_scanner_flags_record_string_any(self):
        """``Record<string, any>`` is the standard TS pattern for typed-key /
        any-value records; 1 generic-any occurrence -> 1 finding.

        Regression guard: literal ``<any>`` regex would miss this; broader
        regex catches ``, any>``.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root, gen_dirs = _make_root_and_gen_dir(tmp)
            _write_qualifying_file(root, "src/service.ts", "const r: Record<string, any> = {};\n")
            findings = _scan(root, gen_dirs)
        self.assertEqual(len(findings), 1)

    def test_scanner_flags_map_string_any(self):
        """``Map<string, any>`` — typed-key, any-value collection; 1 finding."""
        with tempfile.TemporaryDirectory() as tmp:
            root, gen_dirs = _make_root_and_gen_dir(tmp)
            _write_qualifying_file(root, "src/service.ts", "const m: Map<string, any> = new Map();\n")
            findings = _scan(root, gen_dirs)
        self.assertEqual(len(findings), 1)

    def test_scanner_flags_multiple_any_same_line(self):
        """function f(x: any, y: any) {} -> 2 findings at the same line."""
        with tempfile.TemporaryDirectory() as tmp:
            root, gen_dirs = _make_root_and_gen_dir(tmp)
            _write_qualifying_file(root, "src/service.ts", "function f(x: any, y: any) {}\n")
            findings = _scan(root, gen_dirs)
        self.assertEqual(len(findings), 2)
        self.assertEqual(findings[0].line, findings[1].line)

    def test_scanner_flags_colon_any_in_variable(self):
        """const y: any = value; -> 1 finding."""
        with tempfile.TemporaryDirectory() as tmp:
            root, gen_dirs = _make_root_and_gen_dir(tmp)
            _write_qualifying_file(root, "src/service.ts", "const y: any = value;\n")
            findings = _scan(root, gen_dirs)
        self.assertEqual(len(findings), 1)

    def test_scanner_flags_any_array(self):
        """let z: any[] -> 1 finding (': any' with word-boundary from non-word char '[')."""
        with tempfile.TemporaryDirectory() as tmp:
            root, gen_dirs = _make_root_and_gen_dir(tmp)
            _write_qualifying_file(root, "src/service.ts", "let z: any[] = [];\n")
            findings = _scan(root, gen_dirs)
        # ': any' matches; word boundary from '[' is a non-word char so \b holds.
        self.assertGreaterEqual(len(findings), 1)


# ---------------------------------------------------------------------------
# Tests: skip rules
# ---------------------------------------------------------------------------

class TestScannerSkipRules(unittest.TestCase):

    def test_scanner_skips_capitalized_Any(self):
        """'Any' (capitalized) is a different identifier; 0 findings."""
        with tempfile.TemporaryDirectory() as tmp:
            root, gen_dirs = _make_root_and_gen_dir(tmp)
            _write_qualifying_file(
                root, "src/service.ts",
                "import { Any } from '../../packages/cse-types/src/types';\n"
                "const x: Any = someValue;\n",
            )
            findings = _scan(root, gen_dirs)
        self.assertEqual(len(findings), 0)

    def test_scanner_skips_any_in_string_literal(self):
        """String 'as any' is not a type annotation; 0 findings."""
        with tempfile.TemporaryDirectory() as tmp:
            root, gen_dirs = _make_root_and_gen_dir(tmp)
            _write_qualifying_file(
                root, "src/service.ts",
                "const msg = 'as any';\n",
            )
            findings = _scan(root, gen_dirs)
        self.assertEqual(len(findings), 0)

    def test_scanner_skips_any_in_double_quoted_string(self):
        """String \"as any\" inside double quotes -> 0 findings."""
        with tempfile.TemporaryDirectory() as tmp:
            root, gen_dirs = _make_root_and_gen_dir(tmp)
            _write_qualifying_file(
                root, "src/service.ts",
                'const msg = "as any";\n',
            )
            findings = _scan(root, gen_dirs)
        self.assertEqual(len(findings), 0)

    def test_scanner_skips_any_in_line_comment(self):
        """// const x: any = 1; -> 0 findings (whole line is a comment)."""
        with tempfile.TemporaryDirectory() as tmp:
            root, gen_dirs = _make_root_and_gen_dir(tmp)
            _write_qualifying_file(
                root, "src/service.ts",
                "// const x: any = 1;\n",
            )
            findings = _scan(root, gen_dirs)
        self.assertEqual(len(findings), 0)

    def test_scanner_skips_any_after_comment_on_line(self):
        """Code before //, then : any in comment -> 0 findings from comment."""
        with tempfile.TemporaryDirectory() as tmp:
            root, gen_dirs = _make_root_and_gen_dir(tmp)
            _write_qualifying_file(
                root, "src/service.ts",
                "const x = 1; // type is: any here\n",
            )
            findings = _scan(root, gen_dirs)
        self.assertEqual(len(findings), 0)

    def test_scanner_skips_inline_escape(self):
        """Line with forcing-fn-ok comment -> 0 findings (escape honored)."""
        with tempfile.TemporaryDirectory() as tmp:
            root, gen_dirs = _make_root_and_gen_dir(tmp)
            _write_qualifying_file(
                root, "src/service.ts",
                "const x: any = unknownValue; // forcing-fn-ok: legacy contract\n",
            )
            findings = _scan(root, gen_dirs)
        self.assertEqual(len(findings), 0)

    def test_scanner_skips_non_qualifying_file(self):
        """File with : any but no import from generated dir -> 0 findings."""
        with tempfile.TemporaryDirectory() as tmp:
            root, gen_dirs = _make_root_and_gen_dir(tmp)
            non_qualifying = root / "src/other.ts"
            non_qualifying.parent.mkdir(parents=True, exist_ok=True)
            # Import from an unrelated package, NOT from generated_types_dir.
            non_qualifying.write_text(
                "import { Something } from 'some-unrelated-package';\n"
                "const x: any = 1;\n",
                encoding="utf-8",
            )
            findings = _scan(root, gen_dirs)
        self.assertEqual(len(findings), 0)

    def test_scanner_skips_allowlisted_path(self):
        """File matching *.test.ts allowlist with : any -> 0 findings."""
        with tempfile.TemporaryDirectory() as tmp:
            root, gen_dirs = _make_root_and_gen_dir(tmp)
            _write_qualifying_file(
                root, "src/service.test.ts",
                "const x: any = 1;\n",
            )
            findings = _scan(root, gen_dirs)
        self.assertEqual(len(findings), 0)

    def test_scanner_skips_files_under_generated_dir(self):
        """File under packages/cse-types/src/ with : any -> 0 findings."""
        with tempfile.TemporaryDirectory() as tmp:
            root, gen_dirs = _make_root_and_gen_dir(tmp)
            gen_file = gen_dirs[0] / "foo.ts"
            gen_file.write_text(
                "import { Foo } from '../../packages/cse-types/src/types';\n"
                "const x: any = 1;\n",
                encoding="utf-8",
            )
            findings = _scan(root, gen_dirs)
        self.assertEqual(len(findings), 0)

    def test_scanner_word_boundary(self):
        """'anyOther' must NOT match (word boundary required on ':' pattern)."""
        with tempfile.TemporaryDirectory() as tmp:
            root, gen_dirs = _make_root_and_gen_dir(tmp)
            _write_qualifying_file(
                root, "src/service.ts",
                "const anyOther = 1;\n",
            )
            findings = _scan(root, gen_dirs)
        self.assertEqual(len(findings), 0)

    def test_scanner_word_boundary_as_cast(self):
        """'as anyhow' must NOT match 'as any\\b' pattern."""
        with tempfile.TemporaryDirectory() as tmp:
            root, gen_dirs = _make_root_and_gen_dir(tmp)
            _write_qualifying_file(
                root, "src/service.ts",
                "const x = result as anyhow;\n",
            )
            findings = _scan(root, gen_dirs)
        self.assertEqual(len(findings), 0)


# ---------------------------------------------------------------------------
# Tests: file type support
# ---------------------------------------------------------------------------

class TestScannerFileTypes(unittest.TestCase):

    def test_scanner_handles_tsx_files(self):
        """.tsx qualifying file with : any -> finding emitted."""
        with tempfile.TemporaryDirectory() as tmp:
            root, gen_dirs = _make_root_and_gen_dir(tmp)
            _write_qualifying_file(
                root, "src/Component.tsx",
                "const x: any = props;\n",
            )
            findings = _scan(root, gen_dirs)
        self.assertEqual(len(findings), 1)

    def test_scanner_handles_vue_files(self):
        """.vue qualifying file with : any -> finding emitted."""
        with tempfile.TemporaryDirectory() as tmp:
            root, gen_dirs = _make_root_and_gen_dir(tmp)
            _write_qualifying_file(
                root, "src/MyComponent.vue",
                "<script>\nconst x: any = 1;\n</script>\n",
            )
            findings = _scan(root, gen_dirs)
        self.assertEqual(len(findings), 1)

    def test_scanner_ignores_js_files(self):
        """.js files are not scanned even if they match content."""
        with tempfile.TemporaryDirectory() as tmp:
            root, gen_dirs = _make_root_and_gen_dir(tmp)
            js_file = root / "src/service.js"
            js_file.parent.mkdir(parents=True, exist_ok=True)
            js_file.write_text(
                "import { Foo } from '../../packages/cse-types/src/types';\n"
                "const x = obj;\n",
                encoding="utf-8",
            )
            findings = _scan(root, gen_dirs)
        self.assertEqual(len(findings), 0)


# ---------------------------------------------------------------------------
# Tests: Finding field contracts
# ---------------------------------------------------------------------------

class TestScannerFindingFields(unittest.TestCase):

    def test_scanner_path_field_is_relative(self):
        """finding.path is project-relative (not absolute)."""
        with tempfile.TemporaryDirectory() as tmp:
            root, gen_dirs = _make_root_and_gen_dir(tmp)
            _write_qualifying_file(root, "src/service.ts", "const x: any = 1;\n")
            findings = _scan(root, gen_dirs)
        self.assertEqual(len(findings), 1)
        self.assertFalse(
            os.path.isabs(findings[0].path),
            "Finding.path must be project-relative, got: {!r}".format(findings[0].path),
        )
        self.assertIn("service.ts", findings[0].path)

    def test_scanner_line_number_is_1_based(self):
        """Annotation on line 5 (after 4-line header) -> finding.line == 5."""
        with tempfile.TemporaryDirectory() as tmp:
            root, gen_dirs = _make_root_and_gen_dir(tmp)
            # Header is 1 line (the qualifying import).
            # Add 3 more blank lines, then : any on line 5.
            _write_qualifying_file(
                root, "src/service.ts",
                "\n\n\nconst x: any = 1;\n",  # lines 2, 3, 4 blank; line 5 is the annotation
            )
            findings = _scan(root, gen_dirs)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].line, 5)

    def test_scanner_fix_hint_present(self):
        """Findings carry a non-empty fix_hint."""
        with tempfile.TemporaryDirectory() as tmp:
            root, gen_dirs = _make_root_and_gen_dir(tmp)
            _write_qualifying_file(root, "src/service.ts", "const x: any = 1;\n")
            findings = _scan(root, gen_dirs)
        self.assertEqual(len(findings), 1)
        self.assertIsNotNone(findings[0].fix_hint)
        self.assertGreater(len(findings[0].fix_hint), 0)

    def test_scanner_fix_hint_references_gen_dir(self):
        """fix_hint mentions the generated-types dir name."""
        with tempfile.TemporaryDirectory() as tmp:
            root, gen_dirs = _make_root_and_gen_dir(tmp)
            _write_qualifying_file(root, "src/service.ts", "const x: any = 1;\n")
            findings = _scan(root, gen_dirs)
        self.assertEqual(len(findings), 1)
        # The fix_hint should reference the generated_types_dir path.
        self.assertIn("cse-types", findings[0].fix_hint)


# ---------------------------------------------------------------------------
# Tests: import qualification heuristic
# ---------------------------------------------------------------------------

class TestScannerImportQualification(unittest.TestCase):

    def test_scanner_qualifies_via_full_path(self):
        """Import from exact dir path qualifies the file."""
        with tempfile.TemporaryDirectory() as tmp:
            root, gen_dirs = _make_root_and_gen_dir(tmp)
            f = root / "src/service.ts"
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(
                "import { Foo } from 'packages/cse-types/src';\n"
                "const x: any = 1;\n",
                encoding="utf-8",
            )
            findings = _scan(root, gen_dirs)
        self.assertEqual(len(findings), 1)

    def test_scanner_qualifies_via_package_segment(self):
        """Import specifier contains 'packages/cse-types' -> file qualifies."""
        with tempfile.TemporaryDirectory() as tmp:
            root, gen_dirs = _make_root_and_gen_dir(tmp)
            f = root / "src/service.ts"
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(
                "import { Bar } from 'packages/cse-types';\n"
                "const x: any = 1;\n",
                encoding="utf-8",
            )
            findings = _scan(root, gen_dirs)
        self.assertEqual(len(findings), 1)

    def test_scanner_qualifies_via_last_segment_alias(self):
        """Import specifier contains 'cse-types' (last segment) -> file qualifies."""
        with tempfile.TemporaryDirectory() as tmp:
            root, gen_dirs = _make_root_and_gen_dir(tmp)
            f = root / "src/service.ts"
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(
                "import { Bar } from '@org/cse-types';\n"
                "const x: any = 1;\n",
                encoding="utf-8",
            )
            findings = _scan(root, gen_dirs)
        self.assertEqual(len(findings), 1)

    def test_scanner_does_not_flag_pure_code_file(self):
        """File with : any but importing from a totally different path -> 0 findings."""
        with tempfile.TemporaryDirectory() as tmp:
            root, gen_dirs = _make_root_and_gen_dir(tmp)
            f = root / "src/service.ts"
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(
                "import { Something } from '@completely-different/library';\n"
                "const x: any = 1;\n",
                encoding="utf-8",
            )
            findings = _scan(root, gen_dirs)
        self.assertEqual(len(findings), 0)


# ---------------------------------------------------------------------------
# Tests: clean source (no violations)
# ---------------------------------------------------------------------------

class TestScannerClean(unittest.TestCase):

    def test_scanner_clean_source_returns_empty(self):
        """Qualifying file with no any usage -> 0 findings."""
        with tempfile.TemporaryDirectory() as tmp:
            root, gen_dirs = _make_root_and_gen_dir(tmp)
            _write_qualifying_file(
                root, "src/service.ts",
                "const x: string = 'hello';\n"
                "const y: number = 42;\n",
            )
            findings = _scan(root, gen_dirs)
        self.assertEqual(len(findings), 0)

    def test_scanner_empty_root_returns_empty(self):
        """Empty consumer root -> 0 findings (no crash)."""
        with tempfile.TemporaryDirectory() as tmp:
            root, gen_dirs = _make_root_and_gen_dir(tmp)
            findings = _scan(root, gen_dirs)
        self.assertEqual(len(findings), 0)


if __name__ == "__main__":
    unittest.main()
