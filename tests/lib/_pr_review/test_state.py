"""Tests for src/devforge/lib/_pr_review/_state.py.

Coverage:
  PRReviewState default construction — field types + default values.
  state_path — returns correct path structure ending in state.json.
"""

import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _pr_review._state import PRReviewState, state_path  # noqa: E402


class TestPRReviewStateDefaults(unittest.TestCase):
    def setUp(self):
        self.state = PRReviewState()

    def test_pr_number_default_is_zero(self):
        self.assertIsInstance(self.state.pr_number, int)
        self.assertEqual(self.state.pr_number, 0)

    def test_repo_default_is_empty_string(self):
        self.assertEqual(self.state.repo, "")

    def test_diff_default_is_empty_string(self):
        self.assertEqual(self.state.diff, "")

    def test_pr_body_default_is_empty_string(self):
        self.assertEqual(self.state.pr_body, "")

    def test_linked_issues_default_is_empty_list(self):
        self.assertIsInstance(self.state.linked_issues, list)
        self.assertEqual(self.state.linked_issues, [])

    def test_ticket_text_default_is_empty_string(self):
        self.assertEqual(self.state.ticket_text, "")

    def test_forge_tier_default_is_none_sentinel(self):
        self.assertEqual(self.state.forge_tier, "none")

    def test_bundle_default_is_empty_dict(self):
        self.assertIsInstance(self.state.bundle, dict)
        self.assertEqual(self.state.bundle, {})

    def test_smells_default_is_empty_list(self):
        self.assertIsInstance(self.state.smells, list)
        self.assertEqual(self.state.smells, [])

    def test_blast_default_is_empty_list(self):
        self.assertIsInstance(self.state.blast, list)
        self.assertEqual(self.state.blast, [])

    def test_drift_default_is_empty_dict(self):
        self.assertIsInstance(self.state.drift, dict)
        self.assertEqual(self.state.drift, {})

    def test_findings_default_is_empty_list(self):
        self.assertIsInstance(self.state.findings, list)
        self.assertEqual(self.state.findings, [])

    def test_commit_subjects_default_is_empty_list(self):
        self.assertIsInstance(self.state.commit_subjects, list)
        self.assertEqual(self.state.commit_subjects, [])

    def test_target_default_is_empty_string(self):
        """F5: target must be a declared field defaulting to empty string."""
        self.assertIsInstance(self.state.target, str)
        self.assertEqual(self.state.target, "")

    def test_mutable_defaults_are_independent(self):
        """Each instance has its own list/dict objects (no shared default)."""
        s1 = PRReviewState()
        s2 = PRReviewState()
        s1.smells.append("x")
        self.assertEqual(s2.smells, [])
        s1.bundle["k"] = "v"
        self.assertEqual(s2.bundle, {})
        s1.commit_subjects.append("feat: something")
        self.assertEqual(s2.commit_subjects, [])

    def test_target_field_in_asdict(self):
        """F5: dataclasses.asdict must include target field (serialization check)."""
        import dataclasses
        state = PRReviewState(target="/some/path")
        d = dataclasses.asdict(state)
        self.assertIn("target", d)
        self.assertEqual(d["target"], "/some/path")


class TestStatePath(unittest.TestCase):
    def test_returns_string(self):
        result = state_path(".devforge", 42)
        self.assertIsInstance(result, str)

    def test_ends_with_state_json(self):
        result = state_path(".devforge", 42)
        self.assertTrue(result.endswith("state.json"), result)

    def test_contains_pr_number_in_path(self):
        result = state_path(".devforge", 123)
        self.assertIn("123", result)

    def test_contains_pr_reviews_segment(self):
        result = state_path(".devforge", 42)
        self.assertIn("pr-reviews", result)

    def test_contains_devforge_segment(self):
        result = state_path("/abs/path/.devforge", 7)
        self.assertIn(".devforge", result)

    def test_absolute_devforge_dir_preserved(self):
        result = state_path("/some/absolute/.devforge", 99)
        self.assertTrue(result.startswith("/some/absolute/.devforge"), result)

    def test_path_structure_full(self):
        """Path must end with .devforge/pr-reviews/<pr>/state.json."""
        result = state_path("/proj/.devforge", 55)
        self.assertTrue(
            result.endswith(".devforge/pr-reviews/55/state.json"),
            "got: {0}".format(result),
        )

    def test_relative_devforge_dir_becomes_absolute(self):
        """Relative paths are made absolute via os.path.abspath."""
        import os
        result = state_path(".devforge", 1)
        self.assertTrue(os.path.isabs(result), "expected absolute path, got: {0}".format(result))


if __name__ == "__main__":
    unittest.main()
