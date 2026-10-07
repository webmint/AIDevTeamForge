"""Pins the exact text of the four `src/`-layout messages (plan 112 Phase 6).

Phase 6 routes the path segment of these messages through
`_generate_docs/_concern_root.py` without changing the text.
"""
from __future__ import annotations

import argparse
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

_LIB_DIR = Path(__file__).resolve().parent.parent.parent / "src" / "devforge" / "lib"
if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _generate_docs._concern_input import cmd_concern_input  # noqa: E402
from _generate_docs._package_input import cmd_package_input  # noqa: E402
from _generate_docs._setters_concern import _check_tree_entry_coverage  # noqa: E402
from _generate_docs._validators_decomposition import _check_decomposition  # noqa: E402


class LayoutMessageTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name).resolve()
        self.devforge = self.root / ".devforge"
        self.devforge.mkdir()

    def _stderr_of(self, fn, args):
        err = io.StringIO()
        with redirect_stdout(io.StringIO()), redirect_stderr(err):
            code = fn(args)
        self.assertEqual(code, 2)
        return err.getvalue()

    def test_concern_input_not_found(self):
        args = argparse.Namespace(
            devforge_dir=str(self.devforge), package="pkg-a", concern="nope"
        )
        err = self._stderr_of(cmd_concern_input, args)
        self.assertEqual(
            err,
            "concern subfolder not found: {0} "
            "(expected <project_root>/pkg-a/src/nope/)\n".format(
                self.root / "pkg-a" / "src" / "nope"
            ),
        )

    def test_concern_input_not_found_fallback_package(self):
        (self.root / "infra" / "tf").mkdir(parents=True)
        args = argparse.Namespace(
            devforge_dir=str(self.devforge), package="infra/tf", concern="nope"
        )
        err = self._stderr_of(cmd_concern_input, args)
        self.assertEqual(
            err,
            "concern subfolder not found: {0} "
            "(expected <project_root>/infra/tf/src/nope/; package 'infra/tf' "
            "has no src/ directory, so its only concern is 'tf' "
            "(rooted at <project_root>/infra/tf/))\n".format(
                self.root / "infra" / "tf" / "src" / "nope"
            ),
        )

    def test_package_input_no_concerns(self):
        args = argparse.Namespace(devforge_dir=str(self.devforge), package="pkg-a")
        err = self._stderr_of(cmd_package_input, args)
        self.assertEqual(
            err,
            "package 'pkg-a' has no `src/<concern>/` subdirs at "
            "{0} — verify the package path\n".format(self.root / "pkg-a" / "src"),
        )

    def test_tree_coverage_message(self):
        files = ["src/components/f{0}.ts".format(i) for i in range(10)]
        (self.devforge / "index.json").write_text(
            json.dumps({"version": 1, "packages": {"apps/web": {"files": files}}}),
            encoding="utf-8",
        )
        tree = "src/components/\n└── f0.ts"
        msg = _check_tree_entry_coverage(tree, "apps/web", "components", self.devforge)
        self.assertEqual(
            msg,
            "set-concern-tree: tree coverage 10.0% below threshold 80.0%"
            " — rendered 1 entries, expected 10 (concern=components,"
            " subfolder=src/components). The strict spec mandate \"EVERY entry"
            " at EVERY depth\" was not satisfied; recurse into subfolders or"
            " document missing entries.",
        )

    def test_decomposition_message(self):
        sub = self.root / "pkg-a" / "src" / "services"
        sub.mkdir(parents=True)
        errs = _check_decomposition({"concerns": {}}, "pkg-a", self.root)
        self.assertEqual(len(errs), 1)
        self.assertEqual(
            errs[0]["message"],
            "missing concern for substantive subfolder 'services' under "
            "pkg-a/src/; run add-concern --package pkg-a --concern services",
        )


if __name__ == "__main__":
    unittest.main()
