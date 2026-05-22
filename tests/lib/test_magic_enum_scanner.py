"""Tests for _constitute._forcing_functions._magic_enum._scanner.

Real-producer mandate: real TS files are written to tempfile.TemporaryDirectory
and scanned against a hand-built inventory dict.  The inventory is the
controlled variable (we know exactly what enum values exist); the scanner's
job is to find or not find them in the source files.

Coverage
--------
test_scanner_finds_violation                   -- literal matches inventory, no import
test_scanner_skips_legitimate_import           -- enum imported + member-access used
test_scanner_skips_inline_escape               -- // forcing-fn-ok: reason present
test_scanner_skips_allowlisted_path            -- scripts/seed.ts with scripts/**
test_scanner_skips_allowlisted_path_paired_glob -- scripts/** + **/scripts/**
test_scanner_skips_generated_dir               -- file inside a generated dir
test_scanner_skips_line_comment                -- // const role = 'RED'
test_scanner_path_field_is_relative            -- Finding.path is project-relative
test_scanner_finds_multiple_violations         -- two violations on different lines
test_scanner_handles_vue_files                 -- .vue file with string literal
test_scanner_no_findings_on_no_inventory       -- empty inventory -> no findings
test_scanner_literal_not_in_inventory          -- literal not in inventory -> no finding
test_scanner_empty_root                        -- empty root dir -> no findings
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

_LIB_ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "src", "devforge", "lib")
if _LIB_ROOT not in sys.path:
    sys.path.insert(0, _LIB_ROOT)

from _constitute._forcing_functions._magic_enum._scanner import (  # noqa: E402
    scan_for_magic_enum_violations,
)
from _constitute._forcing_functions._shared import Finding  # noqa: E402

# ---------------------------------------------------------------------------
# Shared inventory for controlled tests
# ---------------------------------------------------------------------------

_INVENTORY = {
    "Color": ["RED", "BILLING", "HOME"],
    "OrderStatus": ["PENDING", "CONFIRMED", "CANCELLED"],
}


def _write(tmpdir: str, rel_path: str, content: str) -> Path:
    """Write content to tmpdir/rel_path, creating intermediate dirs."""
    full = Path(tmpdir) / rel_path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content, encoding="utf-8")
    return full


class TestScannerViolation(unittest.TestCase):

    def test_scanner_finds_violation(self):
        """File uses 'RED' (in inventory), no import -> 1 finding."""
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "src/order.ts", "const role = 'RED';\n")
            findings = scan_for_magic_enum_violations(
                root=Path(tmp),
                inventory=_INVENTORY,
                allowlist_globs=[],
                generated_dirs=[],
            )
        self.assertEqual(len(findings), 1)
        f = findings[0]
        self.assertEqual(f.rule, "magic_enum_duplication")
        self.assertEqual(f.kind, "VIOLATION")
        self.assertIn("RED", f.summary)
        self.assertIsInstance(f.fix_hint, str)
        self.assertGreater(len(f.fix_hint), 0)

    def test_scanner_path_field_is_relative(self):
        """Finding.path is relative to root (e.g., src/foo.ts, not absolute)."""
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "src/foo.ts", "const x = 'RED';\n")
            findings = scan_for_magic_enum_violations(
                root=Path(tmp),
                inventory=_INVENTORY,
                allowlist_globs=[],
                generated_dirs=[],
            )
        self.assertEqual(len(findings), 1)
        # Must not be an absolute path.
        self.assertFalse(os.path.isabs(findings[0].path))
        self.assertEqual(findings[0].path, "src/foo.ts")

    def test_scanner_finds_multiple_violations(self):
        """Two matching literals on different lines -> two findings."""
        content = (
            "const a = 'RED';\n"
            "const b = 'BILLING';\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "src/addr.ts", content)
            findings = scan_for_magic_enum_violations(
                root=Path(tmp),
                inventory=_INVENTORY,
                allowlist_globs=[],
                generated_dirs=[],
            )
        self.assertEqual(len(findings), 2)
        lines = {f.line for f in findings}
        self.assertEqual(lines, {1, 2})


class TestScannerExemptions(unittest.TestCase):

    def test_scanner_skips_legitimate_import(self):
        """File imports Color AND uses Color. -> 0 findings."""
        content = (
            "import { Color } from '../generated/types';\n"
            "const type = Color.Red;\n"
            "// even if 'RED' appears here it is exempted\n"
            "const fallback = 'RED';\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "src/order.ts", content)
            findings = scan_for_magic_enum_violations(
                root=Path(tmp),
                inventory=_INVENTORY,
                allowlist_globs=[],
                generated_dirs=[],
            )
        # All Color members are exempted because the import+member-access pair exists.
        shipping_findings = [f for f in findings if "RED" in f.summary]
        self.assertEqual(len(shipping_findings), 0)

    def test_scanner_import_without_member_access_still_flags(self):
        """Import alone does NOT exempt — member-access must also be present.

        Regression guard for the AND condition in the exemption rule.  A
        future change that loosened the check to "imported in this file
        suppresses all enum-member-value literals" would falsely exempt
        files that imported the type but used a raw string literal
        elsewhere.
        """
        content = (
            "import { Color } from '../generated/types';\n"
            "function annotate(_t: Color): void {}\n"
            "const role = 'RED';\n"  # Magic-string violation here.
        )
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "src/order.ts", content)
            findings = scan_for_magic_enum_violations(
                root=Path(tmp),
                inventory=_INVENTORY,
                allowlist_globs=[],
                generated_dirs=[],
            )
        shipping_findings = [f for f in findings if "RED" in f.summary]
        self.assertEqual(len(shipping_findings), 1)

    def test_scanner_member_access_in_comment_does_not_exempt(self):
        """Comment containing ``EnumName.X`` must NOT trigger the exemption.

        Regression guard for the comment-aware ``_enum_used_via_member_access``
        helper.  Without comment-stripping, a comment like
        ``// avoid Color.X`` would falsely exempt the file's
        magic-string literals from the violation report.
        """
        content = (
            "import { Color } from '../generated/types';\n"
            "// avoid Color.Red pattern; use string instead\n"
            "function annotate(_t: Color): void {}\n"
            "const role = 'RED';\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "src/order.ts", content)
            findings = scan_for_magic_enum_violations(
                root=Path(tmp),
                inventory=_INVENTORY,
                allowlist_globs=[],
                generated_dirs=[],
            )
        shipping_findings = [f for f in findings if "RED" in f.summary]
        self.assertEqual(len(shipping_findings), 1)

    def test_scanner_skips_inline_escape(self):
        """Line with forcing-fn-ok: reason -> 0 findings for that line."""
        content = "const role = 'RED'; // forcing-fn-ok: legacy contract\n"
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "src/legacy.ts", content)
            findings = scan_for_magic_enum_violations(
                root=Path(tmp),
                inventory=_INVENTORY,
                allowlist_globs=[],
                generated_dirs=[],
            )
        self.assertEqual(len(findings), 0)

    def test_scanner_skips_allowlisted_path(self):
        """File at scripts/seed.ts with allowlist scripts/** -> 0 findings."""
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "scripts/seed.ts", "const role = 'RED';\n")
            findings = scan_for_magic_enum_violations(
                root=Path(tmp),
                inventory=_INVENTORY,
                allowlist_globs=["scripts/**"],
                generated_dirs=[],
            )
        self.assertEqual(len(findings), 0)

    def test_scanner_skips_allowlisted_path_paired_glob(self):
        """Paired-pattern convention: scripts/** + **/scripts/** both cover the path."""
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "scripts/seed.ts", "const role = 'RED';\n")
            findings = scan_for_magic_enum_violations(
                root=Path(tmp),
                inventory=_INVENTORY,
                allowlist_globs=["scripts/**", "**/scripts/**"],
                generated_dirs=[],
            )
        self.assertEqual(len(findings), 0)

    def test_scanner_skips_generated_dir(self):
        """File inside generated_dirs subtree is excluded from scanning."""
        with tempfile.TemporaryDirectory() as tmp:
            gen_dir = Path(tmp) / "packages" / "cse-types" / "src"
            gen_dir.mkdir(parents=True)
            _write(tmp, "packages/cse-types/src/foo.ts", "const x = 'RED';\n")
            findings = scan_for_magic_enum_violations(
                root=Path(tmp),
                inventory=_INVENTORY,
                allowlist_globs=[],
                generated_dirs=[gen_dir],
            )
        self.assertEqual(len(findings), 0)

    def test_scanner_skips_line_comment(self):
        """// const role = 'RED' (whole line is comment) -> 0 findings."""
        content = "// const role = 'RED';\n"
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "src/disabled.ts", content)
            findings = scan_for_magic_enum_violations(
                root=Path(tmp),
                inventory=_INVENTORY,
                allowlist_globs=[],
                generated_dirs=[],
            )
        self.assertEqual(len(findings), 0)


class TestScannerEdgeCases(unittest.TestCase):

    def test_scanner_backtick_url_does_not_mask_same_line_literal(self):
        """Regression guard: backtick template literal containing ``//`` (e.g., a URL)
        must NOT trigger spurious ``//``-line-comment detection that suppresses a
        same-line magic-enum violation downstream of the backtick string.

        Original bug: _is_in_line_comment tracked only ', ", so http:// inside
        a backtick literal looked like a comment start, hiding 'RED'
        after it.
        """
        content = (
            "const url = `http://example.com`; const role = 'RED';\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "src/order.ts", content)
            findings = scan_for_magic_enum_violations(
                root=Path(tmp),
                inventory=_INVENTORY,
                allowlist_globs=[],
                generated_dirs=[],
            )
        self.assertEqual(len(findings), 1)
        self.assertIn("RED", findings[0].summary)

    def test_scanner_embedded_opposite_quote_no_phantom_match(self):
        """Regression guard: a single-quoted string containing an unescaped
        double-quoted word must NOT produce a phantom match on the embedded
        substring.  Without the fix, ``'address "RED" required'`` would
        falsely emit a finding for the embedded "RED" token.
        """
        content = (
            "function fail(): never { throw new Error('address \"RED\" required'); }\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "src/err.ts", content)
            findings = scan_for_magic_enum_violations(
                root=Path(tmp),
                inventory=_INVENTORY,
                allowlist_globs=[],
                generated_dirs=[],
            )
        # The whole-string literal is 'address "RED" required' — not a
        # bare 'RED' token — so no finding.
        self.assertEqual(len(findings), 0)

    def test_scanner_no_findings_on_no_inventory(self):
        """Empty inventory -> no findings regardless of source content."""
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "src/foo.ts", "const x = 'RED';\n")
            findings = scan_for_magic_enum_violations(
                root=Path(tmp),
                inventory={},
                allowlist_globs=[],
                generated_dirs=[],
            )
        self.assertEqual(len(findings), 0)

    def test_scanner_literal_not_in_inventory(self):
        """Literal that does not appear in inventory -> 0 findings."""
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "src/foo.ts", "const x = 'UNKNOWN_VALUE';\n")
            findings = scan_for_magic_enum_violations(
                root=Path(tmp),
                inventory=_INVENTORY,
                allowlist_globs=[],
                generated_dirs=[],
            )
        self.assertEqual(len(findings), 0)

    def test_scanner_empty_root(self):
        """Empty root directory -> no findings."""
        with tempfile.TemporaryDirectory() as tmp:
            findings = scan_for_magic_enum_violations(
                root=Path(tmp),
                inventory=_INVENTORY,
                allowlist_globs=[],
                generated_dirs=[],
            )
        self.assertEqual(len(findings), 0)

    def test_scanner_handles_vue_files(self):
        """.vue file with matching literal in script block -> 1 finding."""
        content = (
            "<template><div>hello</div></template>\n"
            "<script>\n"
            "const role = 'RED';\n"
            "</script>\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "src/Order.vue", content)
            findings = scan_for_magic_enum_violations(
                root=Path(tmp),
                inventory=_INVENTORY,
                allowlist_globs=[],
                generated_dirs=[],
            )
        self.assertEqual(len(findings), 1)
        self.assertIn("RED", findings[0].summary)

    def test_scanner_finding_is_frozen_dataclass(self):
        """Findings are frozen Finding instances (cannot be mutated)."""
        import dataclasses
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "src/foo.ts", "const x = 'RED';\n")
            findings = scan_for_magic_enum_violations(
                root=Path(tmp),
                inventory=_INVENTORY,
                allowlist_globs=[],
                generated_dirs=[],
            )
        self.assertEqual(len(findings), 1)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            findings[0].summary = "mutated"  # type: ignore[misc]

    def test_scanner_allowlist_non_match_still_scanned(self):
        """File NOT in allowlist is scanned normally."""
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "src/real.ts", "const x = 'RED';\n")
            findings = scan_for_magic_enum_violations(
                root=Path(tmp),
                inventory=_INVENTORY,
                allowlist_globs=["scripts/**"],
                generated_dirs=[],
            )
        self.assertEqual(len(findings), 1)

    def test_scanner_finding_line_number_correct(self):
        """Finding.line is 1-based and matches the line containing the literal."""
        content = (
            "// line 1 comment\n"
            "const x = 1;\n"
            "const role = 'RED';\n"  # line 3
        )
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "src/foo.ts", content)
            findings = scan_for_magic_enum_violations(
                root=Path(tmp),
                inventory=_INVENTORY,
                allowlist_globs=[],
                generated_dirs=[],
            )
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].line, 3)


if __name__ == "__main__":
    unittest.main()
