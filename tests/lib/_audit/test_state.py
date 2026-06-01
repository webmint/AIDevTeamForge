"""Tests for src/devforge/lib/_audit/_state.py.

Coverage:
  state_path — returns absolute path ending in audits/.state.json
  read_state — missing file, corrupt JSON, round-trip, unknown-key tolerance
  write_state — atomic write; parent dir created on demand
  flip_phase — from absent state, from existing state, with status, empty raises
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

from _audit._state import (  # noqa: E402
    AuditState,
    flip_phase,
    read_state,
    state_path,
    write_state,
)


class TestStatePath(unittest.TestCase):
    def test_returns_absolute_path(self):
        result = state_path("/some/workspace")
        self.assertTrue(os.path.isabs(result))

    def test_path_ends_with_state_json(self):
        result = state_path("/some/workspace")
        self.assertTrue(result.endswith(".state.json"))

    def test_path_contains_audits_dir(self):
        result = state_path("/some/workspace")
        self.assertIn("audits", result)

    def test_relative_root_becomes_absolute(self):
        result = state_path("relative/path")
        self.assertTrue(os.path.isabs(result))

    def test_expected_structure(self):
        result = state_path("/ws")
        self.assertEqual(result, "/ws/audits/.state.json")


class TestReadState(unittest.TestCase):
    def test_missing_file_returns_none(self):
        self.assertIsNone(read_state("/nonexistent/path/.state.json"))

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
            sp = os.path.join(td, "audits", ".state.json")
            original = AuditState(
                phase="2",
                mode="narrow",
                scope_description="src/auth/login.py",
                scope_files=["src/auth/login.py"],
                out_path="audits/2024-01-01-audit.md",
                status="in_progress",
            )
            write_state(sp, original)
            loaded = read_state(sp)
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.phase, "2")
            self.assertEqual(loaded.mode, "narrow")
            self.assertEqual(loaded.scope_description, "src/auth/login.py")
            self.assertEqual(loaded.scope_files, ["src/auth/login.py"])
            self.assertEqual(loaded.out_path, "audits/2024-01-01-audit.md")
            self.assertEqual(loaded.status, "in_progress")

    def test_unknown_keys_tolerated(self):
        with tempfile.TemporaryDirectory() as td:
            sp = os.path.join(td, ".state.json")
            data = {
                "phase": "3",
                "mode": "broad",
                "scope_description": "",
                "scope_files": [],
                "out_path": "",
                "status": "complete",
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
            sp = os.path.join(td, "audits", ".state.json")
            self.assertFalse(os.path.exists(sp))
            write_state(sp, AuditState())
            self.assertTrue(os.path.exists(sp))

    def test_output_is_valid_json(self):
        with tempfile.TemporaryDirectory() as td:
            sp = os.path.join(td, ".state.json")
            write_state(sp, AuditState(phase="preflight"))
            with open(sp, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            self.assertEqual(data["phase"], "preflight")

    def test_atomic_write_no_leftover_tmp(self):
        """No .json.tmp files should remain after a successful write."""
        with tempfile.TemporaryDirectory() as td:
            sp = os.path.join(td, ".state.json")
            write_state(sp, AuditState())
            tmp_files = [f for f in os.listdir(td) if f.endswith(".json.tmp")]
            self.assertEqual(tmp_files, [])


class TestFlipPhase(unittest.TestCase):
    def test_from_absent_state_creates_fresh(self):
        with tempfile.TemporaryDirectory() as td:
            sp = os.path.join(td, "audits", ".state.json")
            state = flip_phase(sp, "preflight")
            self.assertEqual(state.phase, "preflight")
            self.assertEqual(state.status, "in_progress")  # default
            self.assertTrue(os.path.exists(sp))

    def test_from_existing_state_updates_phase(self):
        with tempfile.TemporaryDirectory() as td:
            sp = os.path.join(td, "audits", ".state.json")
            # Write initial state.
            write_state(sp, AuditState(phase="1", mode="narrow", status="in_progress"))
            state = flip_phase(sp, "2")
            self.assertEqual(state.phase, "2")
            # Other fields preserved.
            self.assertEqual(state.mode, "narrow")
            self.assertEqual(state.status, "in_progress")

    def test_with_status_update(self):
        with tempfile.TemporaryDirectory() as td:
            sp = os.path.join(td, "audits", ".state.json")
            state = flip_phase(sp, "6", to_status="complete")
            self.assertEqual(state.phase, "6")
            self.assertEqual(state.status, "complete")

    def test_without_to_status_leaves_status_unchanged(self):
        with tempfile.TemporaryDirectory() as td:
            sp = os.path.join(td, "audits", ".state.json")
            write_state(sp, AuditState(phase="3", status="in_progress"))
            state = flip_phase(sp, "4")
            self.assertEqual(state.status, "in_progress")

    def test_empty_phase_raises_value_error(self):
        with tempfile.TemporaryDirectory() as td:
            sp = os.path.join(td, "audits", ".state.json")
            with self.assertRaises(ValueError):
                flip_phase(sp, "")

    def test_whitespace_only_phase_raises_value_error(self):
        with tempfile.TemporaryDirectory() as td:
            sp = os.path.join(td, "audits", ".state.json")
            with self.assertRaises(ValueError):
                flip_phase(sp, "   ")

    def test_result_persisted_to_disk(self):
        with tempfile.TemporaryDirectory() as td:
            sp = os.path.join(td, "audits", ".state.json")
            flip_phase(sp, "5", to_status="complete")
            loaded = read_state(sp)
            self.assertEqual(loaded.phase, "5")
            self.assertEqual(loaded.status, "complete")


class TestAuditStateDefaults(unittest.TestCase):
    def test_default_phase_empty_string(self):
        self.assertEqual(AuditState().phase, "")

    def test_default_mode_empty_string(self):
        self.assertEqual(AuditState().mode, "")

    def test_default_scope_files_is_list(self):
        self.assertIsInstance(AuditState().scope_files, list)
        self.assertEqual(AuditState().scope_files, [])

    def test_default_status_in_progress(self):
        self.assertEqual(AuditState().status, "in_progress")

    def test_scope_files_no_shared_default(self):
        """Verify field(default_factory=list) — no shared mutable default."""
        a = AuditState()
        b = AuditState()
        a.scope_files.append("file.py")
        self.assertEqual(b.scope_files, [])


if __name__ == "__main__":
    unittest.main()
