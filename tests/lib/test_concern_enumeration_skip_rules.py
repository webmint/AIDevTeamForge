"""Pins F20: the two concern enumerations keep DIFFERENT skip rules.

`_package_input._enumerate_concerns` skips dot-prefixed names and
node_modules/dist/build/target; `_preflight._enumerate_concerns` skips
trivial-leaf names (e.g. `static`) but not dot-prefixed ones. Plan 112
Phase 6 must not unify them. Preflight's input is built through the real
chain: init_helper add-package -> index_helper build-index.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_LIB_DIR = Path(__file__).resolve().parent.parent.parent / "src" / "devforge" / "lib"
if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _generate_docs import _package_input, _preflight  # noqa: E402


def _run(script, devforge_dir, *args):
    env = os.environ.copy()
    env["DEVFORGE_DIR"] = str(devforge_dir)
    return subprocess.run(
        [sys.executable, str(_LIB_DIR / script)] + list(args),
        env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )


class ConcernEnumerationSkipRulesTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name).resolve()
        self.devforge = self.root / ".devforge"
        self.devforge.mkdir()
        pkg = self.root / "pkg-a"
        for d in ("real", "static", ".x"):
            (pkg / "src" / d).mkdir(parents=True)
            (pkg / "src" / d / "f.py").write_text("x = 1\n", encoding="utf-8")
        (pkg / "package.json").write_text("{}\n", encoding="utf-8")
        for script, args in (
            ("init_helper.py", ("reset",)),
            ("init_helper.py", ("set-workspace-mode", "standalone")),
            ("init_helper.py", ("set-project-root", ".")),
            ("init_helper.py", ("set-project-state", "brownfield")),
            ("init_helper.py", ("set-default-branch", "main")),
            ("init_helper.py", ("add-package", "--path", "pkg-a", "--no-manifest")),
            ("index_helper.py", ("build-index",)),
        ):
            proc = _run(script, self.devforge, *args)
            self.assertEqual(proc.returncode, 0, proc.stderr.decode())

    def _preflight(self):
        return {c for p, c in _preflight._enumerate_concerns(self.devforge, self.root)
                if p == "pkg-a"}

    def _package_input(self):
        return set(_package_input._enumerate_concerns(self.root, "pkg-a"))

    def test_static_in_package_input_not_preflight(self):
        self.assertIn("static", self._package_input())
        self.assertNotIn("static", self._preflight())

    def test_dot_dir_in_preflight_not_package_input(self):
        self.assertIn(".x", self._preflight())
        self.assertNotIn(".x", self._package_input())

    def test_real_in_both(self):
        self.assertIn("real", self._package_input())
        self.assertIn("real", self._preflight())


if __name__ == "__main__":
    unittest.main()
