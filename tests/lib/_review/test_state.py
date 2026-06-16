"""Tests for src/devforge/lib/_review/_state.py.

Coverage:
  state_path       — returns absolute path ending in review-state.json
  read_state       — missing file, corrupt JSON, round-trip, unknown-key tolerance
  write_state      — atomic write; parent dir created on demand
  flip_phase       — from absent state, from existing state, with status, empty raises
  ReviewState      — default values, list field isolation
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _review._state import (  # noqa: E402
    ReviewState,
    flip_phase,
    read_state,
    state_path,
    write_state,
)


class TestStatePath(unittest.TestCase):
    def test_returns_absolute_path(self):
        result = state_path("/some/feature")
        self.assertTrue(os.path.isabs(result))

    def test_path_ends_with_state_json(self):
        result = state_path("/some/feature")
        self.assertTrue(result.endswith("review-state.json"))

    def test_relative_root_becomes_absolute(self):
        result = state_path("relative/path")
        self.assertTrue(os.path.isabs(result))

    def test_expected_structure(self):
        result = state_path("/specs/001-auth")
        self.assertEqual(result, "/specs/001-auth/review-state.json")

    def test_different_feature_dirs_give_different_paths(self):
        p1 = state_path("/specs/001-auth")
        p2 = state_path("/specs/002-dashboard")
        self.assertNotEqual(p1, p2)


class TestReadState(unittest.TestCase):
    def test_missing_file_returns_none(self):
        self.assertIsNone(read_state("/nonexistent/path/review-state.json"))

    def test_corrupt_json_returns_none(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as fh:
            fh.write("not valid json {{{{")
            tmp = fh.name
        try:
            self.assertIsNone(read_state(tmp))
        finally:
            os.unlink(tmp)

    def test_round_trip(self):
        with tempfile.TemporaryDirectory() as td:
            sp = os.path.join(td, "review-state.json")
            original = ReviewState(
                phase="2",
                feature_dir="specs/001-auth",
                status="in_progress",
                out_path="specs/001-auth/review.md",
                scope_files=["src/auth/login.py", "src/auth/middleware.py"],
                agent_assignments=["security-reviewer", "qa-reviewer"],
            )
            write_state(sp, original)
            loaded = read_state(sp)
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.phase, "2")
            self.assertEqual(loaded.feature_dir, "specs/001-auth")
            self.assertEqual(loaded.status, "in_progress")
            self.assertEqual(loaded.out_path, "specs/001-auth/review.md")
            self.assertEqual(
                loaded.scope_files, ["src/auth/login.py", "src/auth/middleware.py"]
            )
            self.assertEqual(
                loaded.agent_assignments, ["security-reviewer", "qa-reviewer"]
            )

    def test_unknown_keys_tolerated(self):
        with tempfile.TemporaryDirectory() as td:
            sp = os.path.join(td, "review-state.json")
            data = {
                "phase": "3",
                "feature_dir": "specs/002-dashboard",
                "status": "complete",
                "out_path": "specs/002-dashboard/review.md",
                "scope_files": [],
                "agent_assignments": [],
                "future_unknown_field": "ignored",
                "another_unknown": 42,
            }
            with open(sp, "w", encoding="utf-8") as fh:
                json.dump(data, fh)
            state = read_state(sp)
            self.assertIsNotNone(state)
            self.assertEqual(state.phase, "3")
            self.assertEqual(state.status, "complete")
            # Unknown fields should not appear on the object.
            self.assertFalse(hasattr(state, "future_unknown_field"))
            self.assertFalse(hasattr(state, "another_unknown"))


class TestWriteState(unittest.TestCase):
    def test_creates_parent_dir(self):
        with tempfile.TemporaryDirectory() as td:
            sp = os.path.join(td, "specs", "001-auth", "review-state.json")
            self.assertFalse(os.path.exists(sp))
            write_state(sp, ReviewState())
            self.assertTrue(os.path.exists(sp))

    def test_output_is_valid_json(self):
        with tempfile.TemporaryDirectory() as td:
            sp = os.path.join(td, "review-state.json")
            write_state(sp, ReviewState(phase="preflight"))
            with open(sp, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            self.assertEqual(data["phase"], "preflight")

    def test_atomic_write_no_leftover_tmp(self):
        """No .json.tmp files should remain after a successful write."""
        with tempfile.TemporaryDirectory() as td:
            sp = os.path.join(td, "review-state.json")
            write_state(sp, ReviewState())
            tmp_files = [f for f in os.listdir(td) if f.endswith(".json.tmp")]
            self.assertEqual(tmp_files, [])

    def test_written_json_has_all_fields(self):
        with tempfile.TemporaryDirectory() as td:
            sp = os.path.join(td, "review-state.json")
            write_state(sp, ReviewState())
            with open(sp, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            for key in ("phase", "feature_dir", "status", "out_path",
                        "scope_files", "agent_assignments"):
                self.assertIn(key, data)


class TestFlipPhase(unittest.TestCase):
    def test_from_absent_state_creates_fresh(self):
        with tempfile.TemporaryDirectory() as td:
            sp = os.path.join(td, "review-state.json")
            state = flip_phase(sp, "preflight")
            self.assertEqual(state.phase, "preflight")
            self.assertEqual(state.status, "in_progress")  # default
            self.assertTrue(os.path.exists(sp))

    def test_from_existing_state_updates_phase(self):
        with tempfile.TemporaryDirectory() as td:
            sp = os.path.join(td, "review-state.json")
            write_state(sp, ReviewState(phase="1", feature_dir="specs/001", status="in_progress"))
            state = flip_phase(sp, "2")
            self.assertEqual(state.phase, "2")
            # Other fields preserved.
            self.assertEqual(state.feature_dir, "specs/001")
            self.assertEqual(state.status, "in_progress")

    def test_with_status_update(self):
        with tempfile.TemporaryDirectory() as td:
            sp = os.path.join(td, "review-state.json")
            state = flip_phase(sp, "5", to_status="complete")
            self.assertEqual(state.phase, "5")
            self.assertEqual(state.status, "complete")

    def test_without_to_status_leaves_status_unchanged(self):
        with tempfile.TemporaryDirectory() as td:
            sp = os.path.join(td, "review-state.json")
            write_state(sp, ReviewState(phase="3", status="in_progress"))
            state = flip_phase(sp, "4")
            self.assertEqual(state.status, "in_progress")

    def test_empty_phase_raises_value_error(self):
        with tempfile.TemporaryDirectory() as td:
            sp = os.path.join(td, "review-state.json")
            with self.assertRaises(ValueError):
                flip_phase(sp, "")

    def test_whitespace_only_phase_raises_value_error(self):
        with tempfile.TemporaryDirectory() as td:
            sp = os.path.join(td, "review-state.json")
            with self.assertRaises(ValueError):
                flip_phase(sp, "   ")

    def test_result_persisted_to_disk(self):
        with tempfile.TemporaryDirectory() as td:
            sp = os.path.join(td, "review-state.json")
            flip_phase(sp, "5", to_status="complete")
            loaded = read_state(sp)
            self.assertEqual(loaded.phase, "5")
            self.assertEqual(loaded.status, "complete")

    def test_feature_dir_in_path_resolves_correctly(self):
        """state_path + flip_phase resolve correctly when path is inside feature dir."""
        with tempfile.TemporaryDirectory() as td:
            feature_dir = os.path.join(td, "specs", "001-auth")
            os.makedirs(feature_dir, exist_ok=True)
            sp = state_path(feature_dir)
            state = flip_phase(sp, "preflight")
            self.assertTrue(sp.endswith("review-state.json"))
            self.assertEqual(state.phase, "preflight")


class TestReviewStateDefaults(unittest.TestCase):
    def test_default_phase_empty_string(self):
        self.assertEqual(ReviewState().phase, "")

    def test_default_feature_dir_empty_string(self):
        self.assertEqual(ReviewState().feature_dir, "")

    def test_default_status_in_progress(self):
        self.assertEqual(ReviewState().status, "in_progress")

    def test_default_out_path_empty_string(self):
        self.assertEqual(ReviewState().out_path, "")

    def test_default_scope_files_is_list(self):
        self.assertIsInstance(ReviewState().scope_files, list)
        self.assertEqual(ReviewState().scope_files, [])

    def test_default_agent_assignments_is_list(self):
        self.assertIsInstance(ReviewState().agent_assignments, list)
        self.assertEqual(ReviewState().agent_assignments, [])

    def test_scope_files_no_shared_default(self):
        """Verify field(default_factory=list) — no shared mutable default."""
        a = ReviewState()
        b = ReviewState()
        a.scope_files.append("file.py")
        self.assertEqual(b.scope_files, [])

    def test_agent_assignments_no_shared_default(self):
        a = ReviewState()
        b = ReviewState()
        a.agent_assignments.append("security-reviewer")
        self.assertEqual(b.agent_assignments, [])


if __name__ == "__main__":
    unittest.main()
