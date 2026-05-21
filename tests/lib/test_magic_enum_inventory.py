"""Tests for _constitute._forcing_functions._magic_enum._inventory.

Real-producer mandate: every test writes real ``.ts`` / ``.d.ts`` files to a
``tempfile.TemporaryDirectory`` and then calls ``extract_enum_inventory``
against that dir.  No hand-authored inventory dicts are used as test fixtures.

Coverage
--------
test_inventory_ts_enum_with_string_values       -- enum X { A = 'a', B = 'b' }
test_inventory_string_literal_union_single_line -- type X = 'a' | 'b' | 'c'
test_inventory_string_literal_union_multi_line  -- same union split across lines
test_inventory_const_object_as_const            -- const X = { A: 'a' as const } as const
test_inventory_plain_const_object_not_recorded  -- const X = { A: 'a' } (no as const)
test_inventory_skips_numeric_enum               -- enum X { A = 1, B = 2 }
test_inventory_skips_computed_member            -- enum X { A = 'a', B = someFn() }
test_inventory_mixed_union                      -- type X = string | 'a' | 'b'
test_inventory_walks_subdirs                    -- fixture in subdir/file.ts
test_inventory_picks_up_d_ts_files              -- fixture with .d.ts extension
test_inventory_double_and_single_quotes         -- both ' and " quoting shapes
test_inventory_nonexistent_dir_is_skipped       -- no-crash on missing dir
test_inventory_empty_dir                        -- empty dir yields empty result
test_inventory_multiple_enums_same_file         -- two enums in one file
test_inventory_tsx_file                         -- .tsx extension is picked up
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

from _constitute._forcing_functions._magic_enum._inventory import (  # noqa: E402
    extract_enum_inventory,
)


def _write(tmpdir: str, rel_path: str, content: str) -> Path:
    """Write content to tmpdir/rel_path, creating intermediate dirs."""
    full = Path(tmpdir) / rel_path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content, encoding="utf-8")
    return full


class TestInventoryTsEnum(unittest.TestCase):

    def test_inventory_ts_enum_with_string_values(self):
        """enum X { A = 'a', B = 'b' } -> {'X': ['a', 'b']}"""
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "index.ts", "export enum X { A = 'a', B = 'b' }\n")
            result = extract_enum_inventory([Path(tmp)])
        self.assertIn("X", result)
        self.assertEqual(sorted(result["X"]), ["a", "b"])

    def test_inventory_skips_numeric_enum(self):
        """enum X { A = 1, B = 2 } -> X absent (no string values)"""
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "index.ts", "export enum X { A = 1, B = 2 }\n")
            result = extract_enum_inventory([Path(tmp)])
        self.assertNotIn("X", result)

    def test_inventory_skips_computed_member(self):
        """enum X { A = 'a', B = someFn() } -> X present with only 'a'"""
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "index.ts", "export enum X { A = 'a', B = someFn() }\n")
            result = extract_enum_inventory([Path(tmp)])
        self.assertIn("X", result)
        self.assertEqual(result["X"], ["a"])

    def test_inventory_enum_double_quotes(self):
        """enum X { A = \"a\" } is recognized when double-quoted."""
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "index.ts", 'export enum X { A = "a", B = "b" }\n')
            result = extract_enum_inventory([Path(tmp)])
        self.assertIn("X", result)
        self.assertEqual(sorted(result["X"]), ["a", "b"])


class TestInventoryStringUnion(unittest.TestCase):

    def test_inventory_string_literal_union_single_line(self):
        """type X = 'a' | 'b' | 'c' -> {'X': ['a', 'b', 'c']}"""
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "types.ts", "export type X = 'a' | 'b' | 'c';\n")
            result = extract_enum_inventory([Path(tmp)])
        self.assertIn("X", result)
        self.assertEqual(sorted(result["X"]), ["a", "b", "c"])

    def test_inventory_string_literal_union_multi_line(self):
        """Multi-line union type alias -> same result as single-line."""
        content = (
            "export type X =\n"
            "  | 'a'\n"
            "  | 'b'\n"
            "  | 'c';\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "types.ts", content)
            result = extract_enum_inventory([Path(tmp)])
        self.assertIn("X", result)
        self.assertEqual(sorted(result["X"]), ["a", "b", "c"])

    def test_inventory_mixed_union(self):
        """type X = string | 'a' | 'b' -> only string literals recorded."""
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "types.ts", "export type X = string | 'a' | 'b';\n")
            result = extract_enum_inventory([Path(tmp)])
        self.assertIn("X", result)
        self.assertEqual(sorted(result["X"]), ["a", "b"])


class TestInventoryConstAsConst(unittest.TestCase):

    def test_inventory_const_object_as_const(self):
        """const X = { A: 'a' as const, B: 'b' as const } as const -> {'X': ['a', 'b']}"""
        content = "export const X = { A: 'a' as const, B: 'b' as const } as const;\n"
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "enums.ts", content)
            result = extract_enum_inventory([Path(tmp)])
        self.assertIn("X", result)
        self.assertEqual(sorted(result["X"]), ["a", "b"])

    def test_inventory_plain_const_object_not_recorded(self):
        """const X = { A: 'a' } (no as const) -> X absent."""
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "enums.ts", "export const X = { A: 'a', B: 'b' };\n")
            result = extract_enum_inventory([Path(tmp)])
        self.assertNotIn("X", result)

    def test_inventory_const_object_partial_as_const_not_recorded(self):
        """const X = { A: 'a' as const } (no trailing as const on object) -> X absent."""
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "enums.ts", "export const X = { A: 'a' as const };\n")
            result = extract_enum_inventory([Path(tmp)])
        self.assertNotIn("X", result)

    def test_inventory_const_object_with_object_level_only_not_recorded(self):
        """Object-level ``as const`` alone is insufficient — per-member ``as const``
        is also required.  Regression guard for the per-member-missing branch.
        """
        with tempfile.TemporaryDirectory() as tmp:
            _write(
                tmp,
                "enums.ts",
                "export const X = { A: 'a', B: 'b' } as const;\n",
            )
            result = extract_enum_inventory([Path(tmp)])
        self.assertNotIn("X", result)


class TestInventoryWalkBehavior(unittest.TestCase):

    def test_inventory_walks_subdirs(self):
        """Files in subdirectories are found and their enums are recorded."""
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "subdir/types.ts", "export type Role = 'ADMIN' | 'USER';\n")
            result = extract_enum_inventory([Path(tmp)])
        self.assertIn("Role", result)
        self.assertEqual(sorted(result["Role"]), ["ADMIN", "USER"])

    def test_inventory_picks_up_d_ts_files(self):
        """Files with .d.ts extension are picked up (suffix is .ts)."""
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "index.d.ts", "export type Status = 'ACTIVE' | 'INACTIVE';\n")
            result = extract_enum_inventory([Path(tmp)])
        self.assertIn("Status", result)
        self.assertEqual(sorted(result["Status"]), ["ACTIVE", "INACTIVE"])

    def test_inventory_last_wins_on_same_name_across_files(self):
        """Documents the Phase 1 same-name merge semantics: when two files
        define the same enum/union name, the file visited later overwrites
        the earlier definition.  Phase 2 may upgrade to merge-or-error if
        empirical use shows collisions are common; for Phase 1, last-wins
        is the documented behavior.

        os.walk traversal order is filesystem-dependent.  This test uses
        unambiguously different values so any order produces a determinate
        last-wins assertion: at the end of the walk, ``Status`` must
        contain exactly ONE of the two value lists (not the union of both).
        """
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "a/types.ts", "export type Status = 'ACTIVE';\n")
            _write(tmp, "b/types.ts", "export type Status = 'OPEN';\n")
            result = extract_enum_inventory([Path(tmp)])
        self.assertIn("Status", result)
        # Either ['ACTIVE'] or ['OPEN'] — last-wins, not merged.
        self.assertIn(result["Status"], (["ACTIVE"], ["OPEN"]))

    def test_inventory_tsx_file(self):
        """.tsx files are picked up."""
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "colors.tsx", "export type Color = 'red' | 'blue';\n")
            result = extract_enum_inventory([Path(tmp)])
        self.assertIn("Color", result)
        self.assertEqual(sorted(result["Color"]), ["blue", "red"])

    def test_inventory_nonexistent_dir_is_skipped(self):
        """Non-existent directory is silently skipped; no exception."""
        result = extract_enum_inventory([Path("/tmp/__no_such_dir_inventory_test__")])
        self.assertEqual(result, {})

    def test_inventory_empty_dir(self):
        """Directory with no eligible files yields empty result."""
        with tempfile.TemporaryDirectory() as tmp:
            result = extract_enum_inventory([Path(tmp)])
        self.assertEqual(result, {})

    def test_inventory_multiple_enums_same_file(self):
        """Two distinct enum/type declarations in one file are both recorded."""
        content = (
            "export enum Status { ACTIVE = 'ACTIVE', INACTIVE = 'INACTIVE' }\n"
            "export type Role = 'ADMIN' | 'USER';\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "index.ts", content)
            result = extract_enum_inventory([Path(tmp)])
        self.assertIn("Status", result)
        self.assertIn("Role", result)
        self.assertEqual(sorted(result["Status"]), ["ACTIVE", "INACTIVE"])
        self.assertEqual(sorted(result["Role"]), ["ADMIN", "USER"])

    def test_inventory_double_and_single_quotes(self):
        """Both single-quoted and double-quoted enum members are recorded."""
        content = (
            "export enum A { X = 'x' }\n"
            'export enum B { Y = "y" }\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "index.ts", content)
            result = extract_enum_inventory([Path(tmp)])
        self.assertIn("A", result)
        self.assertIn("B", result)
        self.assertEqual(result["A"], ["x"])
        self.assertEqual(result["B"], ["y"])

    def test_inventory_multiple_dirs(self):
        """Two distinct generated dirs; both are walked."""
        with tempfile.TemporaryDirectory() as tmp1:
            with tempfile.TemporaryDirectory() as tmp2:
                _write(tmp1, "a.ts", "export type Role = 'ADMIN';\n")
                _write(tmp2, "b.ts", "export type Status = 'ACTIVE';\n")
                result = extract_enum_inventory([Path(tmp1), Path(tmp2)])
        self.assertIn("Role", result)
        self.assertIn("Status", result)


if __name__ == "__main__":
    unittest.main()
