"""Tests for `_generate_docs/_concern_root.py` (plan 112 Phase 6)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

_LIB_DIR = Path(__file__).resolve().parent.parent.parent / "src" / "devforge" / "lib"
if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _generate_docs import _concern_root as cr  # noqa: E402

ROOT = Path("/proj")


class ConcernRootTests(unittest.TestCase):
    def test_src_dir_name(self):
        self.assertEqual(cr.SRC_DIR_NAME, "src")

    def test_package_root(self):
        self.assertEqual(cr.package_root(ROOT, "pkg"), ROOT / "pkg")
        self.assertEqual(cr.package_root(ROOT, "a/b"), ROOT / "a" / "b")
        self.assertEqual(cr.package_root(ROOT, "."), ROOT)

    def test_concerns_parent_dir(self):
        self.assertEqual(cr.concerns_parent_dir(ROOT, "a/b"), ROOT / "a" / "b" / "src")
        self.assertEqual(cr.concerns_parent_dir(ROOT, "."), ROOT / "src")

    def test_src_root_dir(self):
        self.assertEqual(cr.src_root_dir(ROOT, "a/b"), ROOT / "a" / "b" / "src")
        self.assertEqual(cr.src_root_dir(ROOT, "."), ROOT / "src")

    def test_concern_dir(self):
        self.assertEqual(cr.concern_dir(ROOT, "a/b", "c"), ROOT / "a/b/src/c")
        self.assertEqual(cr.concern_dir(ROOT, ".", "c"), ROOT / "src" / "c")

    def test_concern_rel_prefix(self):
        self.assertEqual(cr.concern_rel_prefix(ROOT, "pkg", "c"), "pkg/src/c/")
        self.assertEqual(cr.concern_rel_prefix(ROOT, "a/b", "c"), "a/b/src/c/")
        self.assertEqual(cr.concern_rel_prefix(ROOT, ".", "c"), "src/c/")

    def test_concern_pkg_prefix(self):
        self.assertEqual(cr.concern_pkg_prefix(ROOT, "pkg", "c"), "src/c/")
        self.assertEqual(cr.concern_pkg_prefix(ROOT, ".", "c"), "src/c/")


if __name__ == "__main__":
    unittest.main()
