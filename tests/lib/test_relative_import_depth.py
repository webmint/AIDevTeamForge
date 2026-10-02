"""tests/lib/test_relative_import_depth.py

Static guard: no relative import under src/devforge/lib climbs above the
top-level package.

Helpers are invoked through extension-less POSIX launchers (for example
``.devforge/lib/verify_helper``) that exec a Python 3 interpreter on
``<lib>/<x>_helper.py``. Running a script puts its directory (``lib/``) on
``sys.path``, and most ``*_helper.py`` files (``verify_helper.py`` among them)
also insert it explicitly. So every ``_<pkg>`` directory under ``lib/`` is a
TOP-LEVEL package. A module's package depth is the number of directories
between ``lib/`` and the file; an ``ImportFrom`` whose ``level`` (dot count) exceeds
that depth raises ``ImportError: attempted relative import beyond top-level
package`` at run time. When the import is function-local, no module-load test
notices (plan 125 -- the ``_verify/_cli.py`` ``file_bugs`` import).

Structure
---------
TestLiveTree     -- the PERMANENT GATE against the real src/devforge/lib.
TestFindViolations -- synthetic trees exercising find_relative_import_violations.
"""

from __future__ import annotations

import ast
import os
import tempfile
import unittest
from pathlib import Path
from typing import List, Tuple

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_LIB_ROOT = _REPO_ROOT / "src" / "devforge" / "lib"


def find_relative_import_violations(lib_root) -> Tuple[List[str], List[str]]:
    """Return (violations, parse_errors) for every .py under ``lib_root``.

    A violation is ``relpath:lineno level=N depth=M`` for any ImportFrom whose
    level exceeds the file's depth below ``lib_root``. Parse errors name the
    file that could not be parsed; such files are never skipped.
    """
    lib_root = Path(lib_root)
    violations = []  # type: List[str]
    parse_errors = []  # type: List[str]
    for path in sorted(lib_root.rglob("*.py")):
        rel = path.relative_to(lib_root)
        if "__pycache__" in rel.parts:
            continue
        depth = len(rel.parts) - 1
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (SyntaxError, ValueError) as exc:
            parse_errors.append("%s: %s" % (rel.as_posix(), exc))
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.level > depth:
                violations.append(
                    "%s:%d level=%d depth=%d"
                    % (rel.as_posix(), node.lineno, node.level, depth)
                )
    return violations, parse_errors


class TestLiveTree(unittest.TestCase):
    def test_no_relative_import_beyond_top_level(self):
        violations, parse_errors = find_relative_import_violations(_LIB_ROOT)
        problems = (
            ["VIOLATION " + v for v in violations]
            + ["PARSE ERROR " + p for p in parse_errors]
        )
        self.assertEqual(
            problems, [], "relative-import depth problems:\n" + "\n".join(problems)
        )


class TestFindViolations(unittest.TestCase):
    def _scan(self, files):
        with tempfile.TemporaryDirectory() as tmp:
            for rel, text in files.items():
                p = Path(tmp) / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(text, encoding="utf-8")
            return find_relative_import_violations(tmp)

    def test_depth1_double_dot_flagged(self):
        v, e = self._scan({"_pkg/_cli.py": "from .._x import y\n"})
        self.assertEqual(v, ["_pkg/_cli.py:1 level=2 depth=1"])
        self.assertEqual(e, [])

    def test_depth1_single_dot_clean(self):
        self.assertEqual(self._scan({"_pkg/_cli.py": "from ._x import y\n"}), ([], []))

    def test_depth2_double_dot_clean(self):
        files = {"_pkg/_sub/_m.py": "from .. import z\n"}
        self.assertEqual(self._scan(files), ([], []))

    def test_depth0_single_dot_flagged(self):
        v, e = self._scan({"a_helper.py": "from . import x\n"})
        self.assertEqual(v, ["a_helper.py:1 level=1 depth=0"])
        self.assertEqual(e, [])

    def test_nested_in_function_still_flagged(self):
        src = "def f():\n    from .._x import y\n    return y\n"
        v, _ = self._scan({"_pkg/_cli.py": src})
        self.assertEqual(v, ["_pkg/_cli.py:2 level=2 depth=1"])

    def test_unparseable_file_reported_as_parse_error(self):
        v, e = self._scan({"_pkg/_bad.py": "def (:\n"})
        self.assertEqual(v, [])
        self.assertEqual(len(e), 1)
        self.assertTrue(e[0].startswith("_pkg/_bad.py"))

    def test_pycache_ignored(self):
        files = {
            "_pkg/__pycache__/_x.py": "from ... import y\n",
            "_pkg/__pycache__/_bad.py": "def (:\n",
        }
        self.assertEqual(self._scan(files), ([], []))

    def test_every_violation_reported(self):
        files = {
            "_p/_a.py": "from .._x import y\n",
            "_p/_b.py": "x = 1\nfrom ... import z\n",
        }
        v, _ = self._scan(files)
        self.assertEqual(
            v, ["_p/_a.py:1 level=2 depth=1", "_p/_b.py:2 level=3 depth=1"]
        )

    def test_init_follows_same_rule(self):
        v, _ = self._scan({"_p/__init__.py": "from .. import x\n"})
        self.assertEqual(v, ["_p/__init__.py:1 level=2 depth=1"])


if __name__ == "__main__":
    unittest.main()
