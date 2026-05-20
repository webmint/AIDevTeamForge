"""Tests for src/devforge/lib/_pr_review/_smells/hallucinated_api.py.

Coverage:
    _is_stdlib_python         — known stdlib, unknown module, dotted top-level match
    _grep_for_module          — found (exit 0 + stdout), not found (exit 1), FileNotFoundError
    run()                     — positive (fake module → finding), negative (known module),
                                stdlib allowlist, relative import skip, cap, empty diff,
                                grep missing, no target
    Finding schema            — correct keys + evidence text
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _pr_review._smells.hallucinated_api import (  # noqa: E402
    _MAX_IMPORTS_PER_PR,
    _grep_for_module,
    _is_stdlib_python,
    run,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_state(diff: str, target: str = "/fake/repo") -> SimpleNamespace:
    return SimpleNamespace(diff=diff, target=target)


def _make_diff_with_import(import_line: str) -> str:
    return (
        "diff --git a/src/foo.py b/src/foo.py\n"
        "+++ b/src/foo.py\n"
        "@@ -1,0 +1,1 @@\n"
        "+" + import_line + "\n"
    )


def _fake_grep_found(*args, **kwargs):
    """Fake subprocess.run result simulating grep found one match."""
    m = MagicMock()
    m.returncode = 0
    m.stdout = "/some/file.py\n"
    return m


def _fake_grep_not_found(*args, **kwargs):
    """Fake subprocess.run result simulating grep found nothing."""
    m = MagicMock()
    m.returncode = 1
    m.stdout = ""
    return m


# ---------------------------------------------------------------------------
# _is_stdlib_python
# ---------------------------------------------------------------------------


class TestIsStdlibPython(unittest.TestCase):
    def test_os_is_stdlib(self):
        self.assertTrue(_is_stdlib_python("os"))

    def test_sys_is_stdlib(self):
        self.assertTrue(_is_stdlib_python("sys"))

    def test_json_is_stdlib(self):
        self.assertTrue(_is_stdlib_python("json"))

    def test_re_is_stdlib(self):
        self.assertTrue(_is_stdlib_python("re"))

    def test_pathlib_is_stdlib(self):
        self.assertTrue(_is_stdlib_python("pathlib"))

    def test_unittest_mock_is_stdlib(self):
        self.assertTrue(_is_stdlib_python("unittest.mock"))

    def test_os_path_is_stdlib(self):
        self.assertTrue(_is_stdlib_python("os.path"))

    def test_unknown_module_not_stdlib(self):
        self.assertFalse(_is_stdlib_python("fake_module"))

    def test_third_party_package_not_stdlib(self):
        self.assertFalse(_is_stdlib_python("requests"))

    def test_dotted_top_level_stdlib(self):
        """xml.etree.ElementTree → top level 'xml' is in stdlib."""
        self.assertTrue(_is_stdlib_python("xml.etree.ElementTree"))


# ---------------------------------------------------------------------------
# _grep_for_module
# ---------------------------------------------------------------------------


class TestGrepForModule(unittest.TestCase):
    def test_found_returns_true(self):
        with patch("subprocess.run", side_effect=_fake_grep_found):
            result = _grep_for_module("some_module", "py", "/fake/repo")
        self.assertTrue(result)

    def test_not_found_returns_false(self):
        with patch("subprocess.run", side_effect=_fake_grep_not_found):
            result = _grep_for_module("fake_module", "py", "/fake/repo")
        self.assertFalse(result)

    def test_file_not_found_returns_none(self):
        """grep binary missing → fail-soft, returns None (not False)."""
        with patch("subprocess.run", side_effect=FileNotFoundError):
            result = _grep_for_module("some_module", "py", "/fake/repo")
        self.assertIsNone(result)

    def test_timeout_returns_none(self):
        import subprocess as sp
        with patch(
            "subprocess.run",
            side_effect=sp.TimeoutExpired(cmd="grep", timeout=30),
        ):
            result = _grep_for_module("some_module", "py", "/fake/repo")
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# run()
# ---------------------------------------------------------------------------


class TestHallucinatedApiRun(unittest.TestCase):
    def test_positive_fake_module_fires(self):
        """Diff imports fake_module; grep finds zero refs → finding."""
        diff = _make_diff_with_import("from fake_module import Thing")
        state = _make_state(diff)
        with patch("subprocess.run", side_effect=_fake_grep_not_found):
            findings = run(state)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["name"], "hallucinated_api")
        self.assertIn("fake_module", findings[0]["evidence"])

    def test_negative_known_module_no_finding(self):
        """Diff imports 'os'; grep finds many refs → no finding."""
        diff = _make_diff_with_import("import os")
        state = _make_state(diff)
        # os is in stdlib allowlist; grep not even called.
        with patch("subprocess.run", side_effect=_fake_grep_found):
            findings = run(state)
        self.assertEqual(findings, [])

    def test_stdlib_json_not_flagged(self):
        diff = _make_diff_with_import("import json")
        state = _make_state(diff)
        with patch("subprocess.run", side_effect=_fake_grep_not_found):
            findings = run(state)
        self.assertEqual(findings, [])

    def test_stdlib_from_typing_not_flagged(self):
        diff = _make_diff_with_import("from typing import Optional")
        state = _make_state(diff)
        with patch("subprocess.run", side_effect=_fake_grep_not_found):
            findings = run(state)
        self.assertEqual(findings, [])

    def test_relative_import_not_flagged(self):
        diff = _make_diff_with_import("from .utils import helper")
        state = _make_state(diff)
        with patch("subprocess.run", side_effect=_fake_grep_not_found):
            findings = run(state)
        self.assertEqual(findings, [])

    def test_ts_import_fires(self):
        """TS import with unknown module → finding."""
        diff = (
            "diff --git a/src/foo.ts b/src/foo.ts\n"
            "+++ b/src/foo.ts\n"
            "@@ -1,0 +1,1 @@\n"
            "+import { Thing } from 'fake-ts-module'\n"
        )
        state = _make_state(diff)
        with patch("subprocess.run", side_effect=_fake_grep_not_found):
            findings = run(state)
        self.assertEqual(len(findings), 1)
        self.assertIn("fake-ts-module", findings[0]["evidence"])

    def test_ts_import_found_no_finding(self):
        """TS import whose module grep finds elsewhere → no finding."""
        diff = (
            "diff --git a/src/foo.ts b/src/foo.ts\n"
            "+++ b/src/foo.ts\n"
            "@@ -1,0 +1,1 @@\n"
            "+import { Thing } from 'react'\n"
        )
        state = _make_state(diff)
        with patch("subprocess.run", side_effect=_fake_grep_found):
            findings = run(state)
        self.assertEqual(findings, [])

    def test_empty_diff_no_finding(self):
        state = _make_state("")
        findings = run(state)
        self.assertEqual(findings, [])

    def test_no_target_no_finding(self):
        diff = _make_diff_with_import("from fake_module import X")
        state = SimpleNamespace(diff=diff, target="")
        findings = run(state)
        self.assertEqual(findings, [])

    def test_grep_missing_no_crash(self):
        """grep binary not in PATH → fail-soft, no finding, no crash."""
        diff = _make_diff_with_import("from fake_module import X")
        state = _make_state(diff)
        with patch("subprocess.run", side_effect=FileNotFoundError):
            findings = run(state)
        self.assertEqual(findings, [])

    def test_cap_at_max_imports(self):
        """More than _MAX_IMPORTS_PER_PR import lines → stops at cap."""
        import_lines = [
            "+from fake_module_{i} import X\n".format(i=i)
            for i in range(40)
        ]
        diff = (
            "diff --git a/src/foo.py b/src/foo.py\n"
            "+++ b/src/foo.py\n"
            "@@ -1,0 +1,40 @@\n"
            + "".join(import_lines)
        )
        state = _make_state(diff)
        with patch("subprocess.run", side_effect=_fake_grep_not_found):
            findings = run(state)
        self.assertLessEqual(len(findings), _MAX_IMPORTS_PER_PR)

    def test_removed_import_not_flagged(self):
        """Import on a '-' line (removed) should not trigger."""
        diff = (
            "diff --git a/src/foo.py b/src/foo.py\n"
            "+++ b/src/foo.py\n"
            "@@ -1,1 +1,0 @@\n"
            "-from fake_module import X\n"
        )
        state = _make_state(diff)
        with patch("subprocess.run", side_effect=_fake_grep_not_found):
            findings = run(state)
        self.assertEqual(findings, [])


class TestHallucinatedApiFindingSchema(unittest.TestCase):
    def setUp(self):
        diff = _make_diff_with_import("from fake_module import Thing")
        state = _make_state(diff)
        with patch("subprocess.run", side_effect=_fake_grep_not_found):
            self.findings = run(state)

    def test_one_finding(self):
        self.assertEqual(len(self.findings), 1)

    def test_name(self):
        self.assertEqual(self.findings[0]["name"], "hallucinated_api")

    def test_severity_low(self):
        self.assertEqual(self.findings[0]["severity"], "low")

    def test_location_format(self):
        self.assertRegex(self.findings[0]["location"], r"^diff:line\+\d+$")

    def test_evidence_contains_module_and_phrase(self):
        ev = self.findings[0]["evidence"]
        self.assertIn("fake_module", ev)
        self.assertIn("not found elsewhere", ev)


if __name__ == "__main__":
    unittest.main()
