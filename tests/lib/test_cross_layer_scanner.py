"""Tests for ``_cross_layer._scanner``: ``scan_for_cross_layer_violations``.

Real-producer mandate: every test writes real ``.ts`` / ``.tsx`` / ``.vue``
files to a ``tempfile.TemporaryDirectory`` and calls
``scan_for_cross_layer_violations`` against the directory.  No hand-authored
fixtures that bypass the real scanner.

Stable test config used throughout
-----------------------------------
ALLOWED_IMPORTS = {
    "domain": {"domain"},
    "infra":  {"domain", "infra"},
    "ui":     {"domain", "infra", "ui"},
}
LAYER_DIRS = {
    "domain": ["pkg/domain/**", "**/pkg/domain/**"],
    "infra":  ["pkg/infra/**",  "**/pkg/infra/**"],
    "ui":     ["pkg/ui/**",     "**/pkg/ui/**"],
}

Coverage
--------
test_scanner_finds_disallowed_import      -- domain imports infra -> 1 finding
test_scanner_finds_import_type_violation  -- import type { T } from cross-layer -> 1 finding
test_scanner_finds_side_effect_import_violation -- import 'cross-layer' side-effect -> 1 finding
test_scanner_skips_allowed_import         -- ui imports domain -> 0 findings
test_scanner_skips_same_layer_import      -- domain imports ./sibling -> 0 findings
test_scanner_skips_external_package_import -- import 'lodash' -> 0 findings
test_scanner_skips_path_aliased_import    -- import '@app/foo' -> 0 findings
test_scanner_skips_unresolvable_import    -- import './nonexistent' -> 0 findings, no crash
test_scanner_resolves_index_ts            -- import '../infra' resolves to index.ts -> 1 finding
test_scanner_resolves_tsx_suffix          -- import resolves to .tsx -> 1 finding
test_scanner_resolves_vue_suffix          -- import resolves to .vue -> 1 finding
test_scanner_skips_unclassified_source    -- file at scripts/build.ts -> 0 findings from it
test_scanner_inline_escape_suppresses_finding -- forcing-fn-ok comment -> 0 findings
test_scanner_allowlist_path_suppresses_findings -- **.test.ts allowlist -> 0 findings
test_scanner_path_field_is_relative       -- Finding.path is project-relative
test_scanner_line_number_is_1_based       -- import on line 3 -> finding.line == 3
test_scanner_finding_fix_hint_present     -- finding carries a non-empty fix_hint
test_scanner_scans_tsx_files              -- .tsx source files are walked and scanned
test_scanner_scans_vue_files              -- .vue source files are walked and scanned
test_scanner_ignores_non_ts_files         -- .js files are not scanned -> 0 findings
test_scanner_finds_multiple_violations_in_one_file -- N imports -> N findings
test_scanner_only_flags_disallowed_in_mixed_file   -- allowed + disallowed mix -> 1 finding
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Dict, List, Set

_LIB_ROOT = os.path.join(
    os.path.dirname(__file__), "..", "..", "src", "devforge", "lib"
)
if _LIB_ROOT not in sys.path:
    sys.path.insert(0, _LIB_ROOT)

from _constitute._forcing_functions._cross_layer._scanner import (  # noqa: E402
    scan_for_cross_layer_violations,
)


# ---------------------------------------------------------------------------
# Stable test config
# ---------------------------------------------------------------------------

ALLOWED_IMPORTS: Dict[str, Set[str]] = {
    "domain": {"domain"},
    "infra": {"domain", "infra"},
    "ui": {"domain", "infra", "ui"},
}

LAYER_DIRS: Dict[str, List[str]] = {
    "domain": ["pkg/domain/**", "**/pkg/domain/**"],
    "infra": ["pkg/infra/**", "**/pkg/infra/**"],
    "ui": ["pkg/ui/**", "**/pkg/ui/**"],
}

EMPTY_ALLOWLIST: List[str] = []


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write(path: Path, content: str) -> None:
    """Write text to path, creating parent dirs as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _scan(root: str, allowlist: List[str] = None) -> list:
    return scan_for_cross_layer_violations(
        Path(root),
        ALLOWED_IMPORTS,
        LAYER_DIRS,
        allowlist or EMPTY_ALLOWLIST,
    )


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

class TestScannerDisallowedImport(unittest.TestCase):

    def test_scanner_finds_disallowed_import(self):
        """domain imports from infra -> 1 finding with correct summary + path + line."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # Create the infra target file so resolution succeeds.
            _write(root / "pkg/infra/bar.ts", "export const bar = 1;\n")
            # domain file imports infra — disallowed.
            _write(
                root / "pkg/domain/foo.ts",
                "import { bar } from '../infra/bar';\n",
            )
            findings = _scan(tmp)

        self.assertEqual(len(findings), 1)
        f = findings[0]
        self.assertIn("domain", f.summary)
        self.assertIn("infra", f.summary)
        self.assertEqual(f.rule, "cross_layer_imports")
        self.assertEqual(f.kind, "VIOLATION")
        self.assertEqual(f.path, "pkg/domain/foo.ts")
        self.assertEqual(f.line, 1)

    def test_scanner_finds_import_type_violation(self):
        """``import type { T } from '../infra/x'`` from a domain file is still a
        layer-coupling cross-edge. The scanner must catch type-only imports
        the same as value imports.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "pkg/infra/types.ts", "export type T = number;\n")
            _write(
                root / "pkg/domain/foo.ts",
                "import type { T } from '../infra/types';\n",
            )
            findings = _scan(tmp)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].rule, "cross_layer_imports")

    def test_scanner_finds_side_effect_import_violation(self):
        """``import '../infra/setup';`` from a domain file is a layer-coupling
        cross-edge (module-augmentation pattern). Must be caught.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "pkg/infra/setup.ts", "console.log('infra');\n")
            _write(
                root / "pkg/domain/foo.ts",
                "import '../infra/setup';\n",
            )
            findings = _scan(tmp)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].rule, "cross_layer_imports")

    def test_scanner_skips_allowed_import(self):
        """ui imports from domain -> allowed -> 0 findings."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "pkg/domain/bar.ts", "export const bar = 1;\n")
            _write(
                root / "pkg/ui/foo.ts",
                "import { bar } from '../domain/bar';\n",
            )
            findings = _scan(tmp)
        self.assertEqual(len(findings), 0)

    def test_scanner_skips_same_layer_import(self):
        """domain imports a sibling in domain -> same layer -> 0 findings."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "pkg/domain/bar.ts", "export const bar = 1;\n")
            _write(
                root / "pkg/domain/foo.ts",
                "import { bar } from './bar';\n",
            )
            findings = _scan(tmp)
        self.assertEqual(len(findings), 0)

    def test_scanner_skips_external_package_import(self):
        """Import from 'lodash' (no leading dot) -> out of scope -> 0 findings."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(
                root / "pkg/domain/foo.ts",
                "import _ from 'lodash';\n",
            )
            findings = _scan(tmp)
        self.assertEqual(len(findings), 0)

    def test_scanner_skips_path_aliased_import(self):
        """Import from '@app/foo' (TS path alias) -> out of scope -> 0 findings."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(
                root / "pkg/domain/foo.ts",
                "import { x } from '@app/infra/service';\n",
            )
            findings = _scan(tmp)
        self.assertEqual(len(findings), 0)

    def test_scanner_skips_unresolvable_import(self):
        """Import target file does not exist -> skip, no crash, 0 findings."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(
                root / "pkg/domain/foo.ts",
                "import { x } from '../infra/nonexistent';\n",
            )
            # Note: pkg/infra/nonexistent.ts is NOT created.
            findings = _scan(tmp)
        self.assertEqual(len(findings), 0)


class TestScannerResolution(unittest.TestCase):

    def test_scanner_resolves_index_ts(self):
        """Import '../infra' resolves to pkg/infra/index.ts -> 1 finding."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "pkg/infra/index.ts", "export const x = 1;\n")
            _write(
                root / "pkg/domain/foo.ts",
                "import { x } from '../infra';\n",
            )
            findings = _scan(tmp)
        self.assertEqual(len(findings), 1)
        self.assertIn("infra", findings[0].summary)

    def test_scanner_resolves_tsx_suffix(self):
        """Import resolves to a .tsx file -> finding emitted."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "pkg/infra/Component.tsx", "export const C = 1;\n")
            _write(
                root / "pkg/domain/foo.ts",
                "import { C } from '../infra/Component';\n",
            )
            findings = _scan(tmp)
        self.assertEqual(len(findings), 1)

    def test_scanner_resolves_vue_suffix(self):
        """Import resolves to a .vue file -> finding emitted."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "pkg/infra/Widget.vue", "<template></template>\n")
            _write(
                root / "pkg/domain/foo.ts",
                "import Widget from '../infra/Widget';\n",
            )
            findings = _scan(tmp)
        self.assertEqual(len(findings), 1)


class TestScannerSkipRules(unittest.TestCase):

    def test_scanner_skips_unclassified_source(self):
        """File at scripts/build.ts (no layer) -> not scanned -> 0 findings from it."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # Create infra target so resolution would succeed if the file were scanned.
            _write(root / "pkg/infra/bar.ts", "export const bar = 1;\n")
            # This file is NOT under any layer dir (scripts/ is not a layer).
            _write(
                root / "scripts/build.ts",
                "import { bar } from '../pkg/infra/bar';\n",
            )
            findings = _scan(tmp)
        self.assertEqual(len(findings), 0)

    def test_scanner_inline_escape_suppresses_finding(self):
        """Line with // forcing-fn-ok: reason -> escape suppresses finding."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "pkg/infra/bar.ts", "export const bar = 1;\n")
            _write(
                root / "pkg/domain/foo.ts",
                "import { bar } from '../infra/bar'; // forcing-fn-ok: legacy boundary\n",
            )
            findings = _scan(tmp)
        self.assertEqual(len(findings), 0)

    def test_scanner_allowlist_path_suppresses_findings(self):
        """File matching allowlist glob -> 0 findings."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "pkg/infra/bar.ts", "export const bar = 1;\n")
            _write(
                root / "pkg/domain/foo.test.ts",
                "import { bar } from '../infra/bar';\n",
            )
            findings = _scan(
                tmp,
                allowlist=["**/*.test.ts", "*.test.ts"],
            )
        self.assertEqual(len(findings), 0)


class TestScannerFindingShape(unittest.TestCase):

    def test_scanner_path_field_is_relative(self):
        """Finding.path is project-relative (not absolute)."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "pkg/infra/bar.ts", "export const bar = 1;\n")
            _write(
                root / "pkg/domain/foo.ts",
                "import { bar } from '../infra/bar';\n",
            )
            findings = _scan(tmp)
        self.assertEqual(len(findings), 1)
        self.assertFalse(
            os.path.isabs(findings[0].path),
            "Finding.path should be relative, got: {}".format(findings[0].path),
        )
        self.assertEqual(findings[0].path, "pkg/domain/foo.ts")

    def test_scanner_line_number_is_1_based(self):
        """Import on line 3 -> Finding.line == 3."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "pkg/infra/bar.ts", "export const bar = 1;\n")
            _write(
                root / "pkg/domain/foo.ts",
                "// line 1\n"
                "// line 2\n"
                "import { bar } from '../infra/bar';\n",
            )
            findings = _scan(tmp)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].line, 3)

    def test_scanner_finding_fix_hint_present(self):
        """Finding carries a non-empty fix_hint."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "pkg/infra/bar.ts", "export const bar = 1;\n")
            _write(
                root / "pkg/domain/foo.ts",
                "import { bar } from '../infra/bar';\n",
            )
            findings = _scan(tmp)
        self.assertEqual(len(findings), 1)
        self.assertIsNotNone(findings[0].fix_hint)
        self.assertGreater(len(findings[0].fix_hint), 0)


class TestScannerFileExtensions(unittest.TestCase):

    def test_scanner_scans_tsx_files(self):
        """.tsx source files are included in the walk."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "pkg/infra/bar.ts", "export const bar = 1;\n")
            _write(
                root / "pkg/domain/Component.tsx",
                "import { bar } from '../infra/bar';\n",
            )
            findings = _scan(tmp)
        self.assertEqual(len(findings), 1)

    def test_scanner_scans_vue_files(self):
        """.vue source files are included in the walk."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "pkg/infra/bar.ts", "export const bar = 1;\n")
            _write(
                root / "pkg/domain/Page.vue",
                "<script>\nimport { bar } from '../infra/bar';\n</script>\n",
            )
            findings = _scan(tmp)
        self.assertEqual(len(findings), 1)

    def test_scanner_ignores_non_ts_files(self):
        """Non-TS/TSX/Vue files (e.g. .js) are not scanned."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "pkg/infra/bar.ts", "export const bar = 1;\n")
            _write(
                root / "pkg/domain/foo.js",
                "import { bar } from '../infra/bar';\n",
            )
            findings = _scan(tmp)
        self.assertEqual(len(findings), 0)


class TestScannerMultipleImports(unittest.TestCase):

    def test_scanner_finds_multiple_violations_in_one_file(self):
        """Multiple disallowed imports in one file -> multiple findings."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "pkg/infra/a.ts", "export const a = 1;\n")
            _write(root / "pkg/infra/b.ts", "export const b = 2;\n")
            _write(
                root / "pkg/domain/foo.ts",
                "import { a } from '../infra/a';\n"
                "import { b } from '../infra/b';\n",
            )
            findings = _scan(tmp)
        self.assertEqual(len(findings), 2)

    def test_scanner_only_flags_disallowed_in_mixed_file(self):
        """File with both allowed and disallowed imports -> only flags disallowed."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "pkg/domain/allowed.ts", "export const a = 1;\n")
            _write(root / "pkg/infra/bad.ts", "export const b = 2;\n")
            _write(
                root / "pkg/domain/mixed.ts",
                "import { a } from './allowed';\n"   # same-layer: ok
                "import { b } from '../infra/bad';\n"  # disallowed
            )
            findings = _scan(tmp)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].line, 2)


if __name__ == "__main__":
    unittest.main()
