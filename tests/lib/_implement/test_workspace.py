"""Tests for src/devforge/lib/_implement/_workspace.py.

Coverage:

  resolve_workspace:
    Happy paths:
    - standalone: PROJECT_ROOT "." → source_root == install_root, is_wrapper False.
    - wrapper: PROJECT_ROOT "acme-product-app" → source_root == install/acme-product-app,
      is_wrapper True.
    - PROJECT_ROOT with surrounding whitespace ("  acme-product-app  ") → trimmed,
      treated as wrapper.

    Fail-soft (all return standalone, never raise):
    - missing config file → standalone.
    - malformed JSON → standalone.
    - valid JSON but not a dict (e.g. a list) → standalone.
    - PROJECT_ROOT key absent → standalone.
    - PROJECT_ROOT empty string "" → standalone.
    - PROJECT_ROOT whitespace-only "  " → standalone.
    - PROJECT_ROOT wrong type (integer) → standalone.
    - config file unreadable (permission denied) → standalone.

    Edge cases:
    - install_root given as a string (not Path) → still resolves correctly.
    - Workspace fields are frozen (mutation raises FrozenInstanceError).
    - source_root is always an absolute path.
    - install_root is always an absolute path.

  Workspace dataclass:
    - Correct field types accepted.
    - Non-Path install_root → ValueError.
    - Non-Path source_root → ValueError.
    - Non-bool is_wrapper → ValueError.

Design notes:
- Tests write real .devforge/project-config.json files to tempdir (the real
  producer shape, not hand-authored guesses), so the loader path is exercised
  end-to-end.
- The permission-denied test uses os.chmod and is skipped on platforms where
  that doesn't actually prevent reading (Windows; unlikely in CI but guarded).
- Stdlib only. Python 3.8+.
"""

import dataclasses
import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path

# ---------------------------------------------------------------------------
# Path bootstrap: make _implement importable without an installed package.
# ---------------------------------------------------------------------------
_LIB_DIR = str(Path(__file__).resolve().parents[3] / "src" / "devforge" / "lib")
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

from _implement._workspace import (  # noqa: E402
    Workspace,
    resolve_workspace,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_config(install_dir, data):
    # type: (Path, object) -> Path
    """Write data as JSON to <install_dir>/.devforge/project-config.json.

    Returns the config file Path.
    """
    devforge = install_dir / ".devforge"
    devforge.mkdir(parents=True, exist_ok=True)
    config_path = devforge / "project-config.json"
    config_path.write_text(json.dumps(data), encoding="utf-8")
    return config_path


# ---------------------------------------------------------------------------
# Tests: resolve_workspace — standalone
# ---------------------------------------------------------------------------


class TestResolveWorkspaceStandalone(unittest.TestCase):

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self.install = Path(self._tmpdir).resolve()

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_dot_project_root_is_standalone(self):
        """PROJECT_ROOT '.' → source_root == install_root, is_wrapper False."""
        _write_config(self.install, {"PROJECT_ROOT": "."})
        ws = resolve_workspace(self.install)
        self.assertEqual(ws.install_root, self.install)
        self.assertEqual(ws.source_root, self.install)
        self.assertFalse(ws.is_wrapper)

    def test_dot_project_root_source_root_equals_install_root(self):
        """source_root and install_root are the same object / value for standalone."""
        _write_config(self.install, {"PROJECT_ROOT": "."})
        ws = resolve_workspace(self.install)
        # Must be equal, not just "similar" — no trailing slashes, no /. suffix.
        self.assertEqual(ws.source_root, ws.install_root)
        # Both must be absolute.
        self.assertTrue(ws.source_root.is_absolute())
        self.assertTrue(ws.install_root.is_absolute())


# ---------------------------------------------------------------------------
# Tests: resolve_workspace — wrapper
# ---------------------------------------------------------------------------


class TestResolveWorkspaceWrapper(unittest.TestCase):

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self.install = Path(self._tmpdir).resolve()
        # Create the nested source directory so resolve() works correctly
        # on symlink-free systems (resolve() on a non-existent dir still works
        # on CPython, but create it to be unambiguous).
        (self.install / "acme-product-app").mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_wrapper_project_root(self):
        """PROJECT_ROOT 'acme-product-app' → source_root points at nested dir."""
        _write_config(self.install, {"PROJECT_ROOT": "acme-product-app"})
        ws = resolve_workspace(self.install)
        self.assertEqual(ws.install_root, self.install)
        self.assertEqual(ws.source_root, self.install / "acme-product-app")
        self.assertTrue(ws.is_wrapper)

    def test_wrapper_source_root_is_absolute(self):
        _write_config(self.install, {"PROJECT_ROOT": "acme-product-app"})
        ws = resolve_workspace(self.install)
        self.assertTrue(ws.source_root.is_absolute())

    def test_wrapper_project_root_with_surrounding_whitespace(self):
        """PROJECT_ROOT '  acme-product-app  ' → stripped, treated as wrapper."""
        _write_config(self.install, {"PROJECT_ROOT": "  acme-product-app  "})
        ws = resolve_workspace(self.install)
        self.assertEqual(ws.source_root, self.install / "acme-product-app")
        self.assertTrue(ws.is_wrapper)


# ---------------------------------------------------------------------------
# Tests: resolve_workspace — fail-soft cases
# ---------------------------------------------------------------------------


class TestResolveWorkspaceFailSoft(unittest.TestCase):
    """All fail-soft paths must return standalone and never raise."""

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self.install = Path(self._tmpdir).resolve()

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def _assert_standalone(self, ws):
        # type: (Workspace) -> None
        self.assertIsInstance(ws, Workspace)
        self.assertEqual(ws.install_root, self.install)
        self.assertEqual(ws.source_root, self.install)
        self.assertFalse(ws.is_wrapper)

    def test_missing_config_file(self):
        """No .devforge/project-config.json → standalone fail-soft."""
        # No config written; .devforge/ may not even exist.
        ws = resolve_workspace(self.install)
        self._assert_standalone(ws)

    def test_malformed_json(self):
        """Malformed JSON in config → standalone fail-soft."""
        devforge = self.install / ".devforge"
        devforge.mkdir(parents=True, exist_ok=True)
        (devforge / "project-config.json").write_text(
            "{not valid json}", encoding="utf-8"
        )
        ws = resolve_workspace(self.install)
        self._assert_standalone(ws)

    def test_json_not_a_dict(self):
        """Config is valid JSON but a list, not a dict → standalone fail-soft."""
        _write_config(self.install, ["PROJECT_ROOT", "."])
        ws = resolve_workspace(self.install)
        self._assert_standalone(ws)

    def test_project_root_key_absent(self):
        """Config is a valid dict but has no PROJECT_ROOT key → standalone."""
        _write_config(self.install, {"SOME_OTHER_KEY": "value"})
        ws = resolve_workspace(self.install)
        self._assert_standalone(ws)

    def test_project_root_empty_string(self):
        """PROJECT_ROOT '' (empty string) → standalone."""
        _write_config(self.install, {"PROJECT_ROOT": ""})
        ws = resolve_workspace(self.install)
        self._assert_standalone(ws)

    def test_project_root_whitespace_only(self):
        """PROJECT_ROOT '   ' (whitespace only) → standalone."""
        _write_config(self.install, {"PROJECT_ROOT": "   "})
        ws = resolve_workspace(self.install)
        self._assert_standalone(ws)

    def test_project_root_wrong_type_integer(self):
        """PROJECT_ROOT is an integer (not a string) → standalone fail-soft."""
        _write_config(self.install, {"PROJECT_ROOT": 42})
        ws = resolve_workspace(self.install)
        self._assert_standalone(ws)

    def test_project_root_wrong_type_none(self):
        """PROJECT_ROOT is JSON null → standalone fail-soft."""
        _write_config(self.install, {"PROJECT_ROOT": None})
        ws = resolve_workspace(self.install)
        self._assert_standalone(ws)

    @unittest.skipIf(
        os.name == "nt",
        "chmod permission denial unreliable on Windows",
    )
    def test_unreadable_config_file(self):
        """Unreadable config file (permission denied) → standalone fail-soft."""
        config = _write_config(self.install, {"PROJECT_ROOT": "acme-product-app"})
        # Remove read permission.
        config.chmod(0o000)
        try:
            ws = resolve_workspace(self.install)
            self._assert_standalone(ws)
        finally:
            # Restore so tearDown cleanup can delete it.
            config.chmod(stat.S_IRUSR | stat.S_IWUSR)


# ---------------------------------------------------------------------------
# Tests: resolve_workspace — edge cases
# ---------------------------------------------------------------------------


class TestResolveWorkspaceEdgeCases(unittest.TestCase):

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self.install = Path(self._tmpdir).resolve()

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_install_root_given_as_string(self):
        """install_root passed as str (not Path) → resolves correctly."""
        _write_config(self.install, {"PROJECT_ROOT": "."})
        ws = resolve_workspace(str(self.install))
        self.assertEqual(ws.install_root, self.install)
        self.assertEqual(ws.source_root, self.install)
        self.assertFalse(ws.is_wrapper)

    def test_install_root_is_absolute_in_result(self):
        """install_root in returned Workspace is always absolute."""
        _write_config(self.install, {"PROJECT_ROOT": "."})
        ws = resolve_workspace(self.install)
        self.assertTrue(ws.install_root.is_absolute())

    def test_workspace_is_frozen(self):
        """Workspace is immutable — attribute assignment must raise."""
        _write_config(self.install, {"PROJECT_ROOT": "."})
        ws = resolve_workspace(self.install)
        with self.assertRaises((dataclasses.FrozenInstanceError, TypeError, AttributeError)):
            ws.is_wrapper = True  # type: ignore[misc]

    def test_standalone_source_root_no_dot_suffix(self):
        """source_root for standalone must not end with '/.' — resolve() collapses it."""
        _write_config(self.install, {"PROJECT_ROOT": "."})
        ws = resolve_workspace(self.install)
        # The string representation must not end with the literal dot segment.
        self.assertFalse(str(ws.source_root).endswith("/."))
        self.assertFalse(str(ws.source_root).endswith(os.sep + "."))


# ---------------------------------------------------------------------------
# Tests: Workspace dataclass direct construction validation
# ---------------------------------------------------------------------------


class TestWorkspaceDataclassValidation(unittest.TestCase):

    def _sample_path(self):
        return Path("/tmp/forge-test")

    def test_valid_construction(self):
        """Well-typed fields construct without error."""
        p = self._sample_path()
        ws = Workspace(install_root=p, source_root=p, is_wrapper=False)
        self.assertEqual(ws.install_root, p)
        self.assertEqual(ws.source_root, p)
        self.assertFalse(ws.is_wrapper)

    def test_install_root_not_path_raises(self):
        """Non-Path install_root → ValueError."""
        p = self._sample_path()
        with self.assertRaises(ValueError) as ctx:
            Workspace(install_root="/tmp/foo", source_root=p, is_wrapper=False)  # type: ignore[arg-type]
        self.assertIn("install_root", str(ctx.exception))

    def test_source_root_not_path_raises(self):
        """Non-Path source_root → ValueError."""
        p = self._sample_path()
        with self.assertRaises(ValueError) as ctx:
            Workspace(install_root=p, source_root="/tmp/foo", is_wrapper=False)  # type: ignore[arg-type]
        self.assertIn("source_root", str(ctx.exception))

    def test_is_wrapper_not_bool_raises(self):
        """Non-bool is_wrapper → ValueError."""
        p = self._sample_path()
        with self.assertRaises(ValueError) as ctx:
            Workspace(install_root=p, source_root=p, is_wrapper=1)  # type: ignore[arg-type]
        self.assertIn("is_wrapper", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
