"""Tests for src/devforge/lib/_pr_review/_smells/_catalog.py.

Coverage:
  register()   — happy path, duplicate-name rejection
  run_all()    — dispatches all registered heuristics in order, returns flat list
  clear_registry() — test-isolation helper
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _pr_review._smells._catalog import (  # noqa: E402
    _CATALOG,
    clear_registry,
    register,
    run_all,
)
from _pr_review._state import PRReviewState  # noqa: E402


def _reload_smells_defaults():
    """Clear the catalog and reload the _smells package to restore defaults."""
    import importlib
    import _pr_review._smells as _smells_pkg
    clear_registry()
    importlib.reload(_smells_pkg)


class TestRegister(unittest.TestCase):
    def setUp(self):
        clear_registry()

    def tearDown(self):
        # Always restore catalog to default state after each test.
        _reload_smells_defaults()

    def test_register_adds_entry_to_catalog(self):
        self.assertEqual(len(_CATALOG), 0)
        register("test_h", "low", lambda s: [])
        self.assertEqual(len(_CATALOG), 1)

    def test_register_stores_name_and_severity(self):
        register("my_h", "medium", lambda s: [])
        name, sev, _ = _CATALOG[0]
        self.assertEqual(name, "my_h")
        self.assertEqual(sev, "medium")

    def test_register_duplicate_name_raises_value_error(self):
        register("dup_h", "low", lambda s: [])
        with self.assertRaises(ValueError) as ctx:
            register("dup_h", "low", lambda s: [])
        self.assertIn("dup_h", str(ctx.exception))

    def test_register_multiple_distinct_names(self):
        register("h1", "nit", lambda s: [])
        register("h2", "low", lambda s: [])
        register("h3", "medium", lambda s: [])
        self.assertEqual(len(_CATALOG), 3)

    def test_register_preserves_insertion_order(self):
        register("first", "nit", lambda s: [])
        register("second", "low", lambda s: [])
        names = [entry[0] for entry in _CATALOG]
        self.assertEqual(names, ["first", "second"])


class TestRunAll(unittest.TestCase):
    def setUp(self):
        clear_registry()

    def tearDown(self):
        _reload_smells_defaults()

    def _make_state(self, **kwargs):
        return PRReviewState(**kwargs)

    def test_run_all_empty_catalog_returns_empty_list(self):
        state = self._make_state()
        result = run_all(state)
        self.assertEqual(result, [])

    def test_run_all_collects_findings_from_one_heuristic(self):
        finding = {"name": "h1", "severity": "low", "location": "*", "evidence": "x"}
        register("h1", "low", lambda s: [finding])
        state = self._make_state()
        result = run_all(state)
        self.assertEqual(result, [finding])

    def test_run_all_collects_findings_from_multiple_heuristics(self):
        f1 = {"name": "h1", "severity": "low", "location": "*", "evidence": "a"}
        f2 = {"name": "h2", "severity": "medium", "location": "*", "evidence": "b"}
        register("h1", "low", lambda s: [f1])
        register("h2", "medium", lambda s: [f2])
        state = self._make_state()
        result = run_all(state)
        self.assertEqual(result, [f1, f2])

    def test_run_all_preserves_registration_order(self):
        """Findings from heuristics appear in registration order."""
        calls = []
        register("first", "nit", lambda s: [calls.append("first")] and [])
        register("second", "low", lambda s: [calls.append("second")] and [])
        run_all(self._make_state())
        self.assertEqual(calls, ["first", "second"])

    def test_run_all_heuristic_returning_no_findings_does_not_add_to_list(self):
        register("empty_h", "nit", lambda s: [])
        register("real_h", "low", lambda s: [{"name": "real_h", "severity": "low",
                                               "location": "*", "evidence": "x"}])
        result = run_all(self._make_state())
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "real_h")

    def test_run_all_multiple_findings_from_single_heuristic(self):
        """A heuristic emitting N findings adds all N to the flat list."""
        findings = [
            {"name": "h", "severity": "low", "location": "diff:line+1", "evidence": "x"},
            {"name": "h", "severity": "low", "location": "diff:line+2", "evidence": "y"},
            {"name": "h", "severity": "low", "location": "diff:line+3", "evidence": "z"},
        ]
        register("h", "low", lambda s: findings)
        result = run_all(self._make_state())
        self.assertEqual(len(result), 3)

    def test_run_all_passes_state_to_heuristic(self):
        """The state object received by the heuristic is the same one passed."""
        received = []
        register("spy", "nit", lambda s: received.append(s) or [])
        state = self._make_state(pr_number=42)
        run_all(state)
        self.assertIs(received[0], state)

    def test_clear_registry_empties_catalog(self):
        register("h", "nit", lambda s: [])
        self.assertEqual(len(_CATALOG), 1)
        clear_registry()
        self.assertEqual(len(_CATALOG), 0)


class TestDefaultRegistration(unittest.TestCase):
    """The default catalog (populated by _smells/__init__.py) has 4 heuristics."""

    def setUp(self):
        # Ensure we are using the production catalog by reloading defaults.
        _reload_smells_defaults()

    def test_four_heuristics_registered_by_default(self):
        self.assertEqual(len(_CATALOG), 4)

    def test_default_heuristic_names(self):
        names = [entry[0] for entry in _CATALOG]
        self.assertIn("empty_pr_body", names)
        self.assertIn("atomic_dump", names)
        self.assertIn("hedge_defensive", names)
        self.assertIn("verbose_commit_msg", names)

    def test_registration_order(self):
        names = [entry[0] for entry in _CATALOG]
        self.assertEqual(names, [
            "empty_pr_body",
            "atomic_dump",
            "hedge_defensive",
            "verbose_commit_msg",
        ])


if __name__ == "__main__":
    unittest.main()
