"""Tests for src/devforge/lib/_verify/_state.py.

Coverage:
  state_path       — returns absolute path ending in verify-state.json
  read_state       — missing file, corrupt JSON, round-trip, unknown-key tolerance
  write_state      — atomic write; parent dir created on demand
  flip_phase       — from absent state, from existing state, with status, empty raises
  VerifyState      — default values, list field isolation
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

from _verify._state import (  # noqa: E402
    VerifyState,
    flip_phase,
    read_state,
    state_path,
    write_state,
)
from _verify._cli import main as cli_main  # noqa: E402


class TestStatePath(unittest.TestCase):
    def test_returns_absolute_path(self):
        result = state_path("/some/feature")
        self.assertTrue(os.path.isabs(result))

    def test_path_ends_with_verify_state_json(self):
        result = state_path("/some/feature")
        self.assertTrue(result.endswith("verify-state.json"))

    def test_path_does_not_end_with_review_state_json(self):
        """Ensure we use verify-state.json, not review-state.json."""
        result = state_path("/some/feature")
        self.assertFalse(result.endswith("review-state.json"))

    def test_relative_root_becomes_absolute(self):
        result = state_path("relative/path")
        self.assertTrue(os.path.isabs(result))

    def test_expected_structure(self):
        result = state_path("/specs/001-auth")
        self.assertEqual(result, "/specs/001-auth/verify-state.json")

    def test_different_feature_dirs_give_different_paths(self):
        p1 = state_path("/specs/001-auth")
        p2 = state_path("/specs/002-dashboard")
        self.assertNotEqual(p1, p2)


class TestReadState(unittest.TestCase):
    def test_missing_file_returns_none(self):
        self.assertIsNone(read_state("/nonexistent/path/verify-state.json"))

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
            sp = os.path.join(td, "verify-state.json")
            original = VerifyState(
                phase="2",
                feature_dir="specs/001-auth",
                status="in_progress",
                out_path="specs/001-auth/verification.md",
                scope_files=["src/auth/login.py", "src/auth/middleware.py"],
                verdict="",
            )
            write_state(sp, original)
            loaded = read_state(sp)
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.phase, "2")
            self.assertEqual(loaded.feature_dir, "specs/001-auth")
            self.assertEqual(loaded.status, "in_progress")
            self.assertEqual(loaded.out_path, "specs/001-auth/verification.md")
            self.assertEqual(
                loaded.scope_files, ["src/auth/login.py", "src/auth/middleware.py"]
            )
            self.assertEqual(loaded.verdict, "")

    def test_unknown_keys_tolerated(self):
        with tempfile.TemporaryDirectory() as td:
            sp = os.path.join(td, "verify-state.json")
            data = {
                "phase": "3",
                "feature_dir": "specs/002-dashboard",
                "status": "complete",
                "out_path": "specs/002-dashboard/verification.md",
                "scope_files": [],
                "verdict": "APPROVED",
                "future_unknown_field": "ignored",
                "another_unknown": 42,
            }
            with open(sp, "w", encoding="utf-8") as fh:
                json.dump(data, fh)
            state = read_state(sp)
            self.assertIsNotNone(state)
            self.assertEqual(state.phase, "3")
            self.assertEqual(state.status, "complete")
            self.assertEqual(state.verdict, "APPROVED")
            # Unknown fields should not appear on the object.
            self.assertFalse(hasattr(state, "future_unknown_field"))
            self.assertFalse(hasattr(state, "another_unknown"))


class TestWriteState(unittest.TestCase):
    def test_creates_parent_dir(self):
        with tempfile.TemporaryDirectory() as td:
            sp = os.path.join(td, "specs", "001-auth", "verify-state.json")
            self.assertFalse(os.path.exists(sp))
            write_state(sp, VerifyState())
            self.assertTrue(os.path.exists(sp))

    def test_output_is_valid_json(self):
        with tempfile.TemporaryDirectory() as td:
            sp = os.path.join(td, "verify-state.json")
            write_state(sp, VerifyState(phase="preflight"))
            with open(sp, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            self.assertEqual(data["phase"], "preflight")

    def test_atomic_write_no_leftover_tmp(self):
        """No .json.tmp files should remain after a successful write."""
        with tempfile.TemporaryDirectory() as td:
            sp = os.path.join(td, "verify-state.json")
            write_state(sp, VerifyState())
            tmp_files = [f for f in os.listdir(td) if f.endswith(".json.tmp")]
            self.assertEqual(tmp_files, [])

    def test_written_json_has_all_fields(self):
        with tempfile.TemporaryDirectory() as td:
            sp = os.path.join(td, "verify-state.json")
            write_state(sp, VerifyState())
            with open(sp, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            for key in ("phase", "feature_dir", "status", "out_path",
                        "scope_files", "verdict"):
                self.assertIn(key, data)

    def test_state_file_named_verify_state_json(self):
        """Verify the state file uses the verify-specific filename."""
        with tempfile.TemporaryDirectory() as td:
            feature_dir = os.path.join(td, "specs", "001-auth")
            os.makedirs(feature_dir, exist_ok=True)
            sp = state_path(feature_dir)
            self.assertTrue(sp.endswith("verify-state.json"))
            write_state(sp, VerifyState(phase="preflight"))
            self.assertTrue(os.path.exists(sp))
            # Confirm the file is named correctly
            self.assertEqual(os.path.basename(sp), "verify-state.json")


class TestFlipPhase(unittest.TestCase):
    def test_from_absent_state_creates_fresh(self):
        with tempfile.TemporaryDirectory() as td:
            sp = os.path.join(td, "verify-state.json")
            state = flip_phase(sp, "preflight")
            self.assertEqual(state.phase, "preflight")
            self.assertEqual(state.status, "in_progress")  # default
            self.assertTrue(os.path.exists(sp))

    def test_from_existing_state_updates_phase(self):
        with tempfile.TemporaryDirectory() as td:
            sp = os.path.join(td, "verify-state.json")
            write_state(sp, VerifyState(phase="1", feature_dir="specs/001", status="in_progress"))
            state = flip_phase(sp, "2")
            self.assertEqual(state.phase, "2")
            # Other fields preserved.
            self.assertEqual(state.feature_dir, "specs/001")
            self.assertEqual(state.status, "in_progress")

    def test_with_status_update(self):
        with tempfile.TemporaryDirectory() as td:
            sp = os.path.join(td, "verify-state.json")
            state = flip_phase(sp, "9", to_status="complete")
            self.assertEqual(state.phase, "9")
            self.assertEqual(state.status, "complete")

    def test_without_to_status_leaves_status_unchanged(self):
        with tempfile.TemporaryDirectory() as td:
            sp = os.path.join(td, "verify-state.json")
            write_state(sp, VerifyState(phase="3", status="in_progress"))
            state = flip_phase(sp, "4")
            self.assertEqual(state.status, "in_progress")

    def test_empty_phase_raises_value_error(self):
        with tempfile.TemporaryDirectory() as td:
            sp = os.path.join(td, "verify-state.json")
            with self.assertRaises(ValueError):
                flip_phase(sp, "")

    def test_whitespace_only_phase_raises_value_error(self):
        with tempfile.TemporaryDirectory() as td:
            sp = os.path.join(td, "verify-state.json")
            with self.assertRaises(ValueError):
                flip_phase(sp, "   ")

    def test_result_persisted_to_disk(self):
        with tempfile.TemporaryDirectory() as td:
            sp = os.path.join(td, "verify-state.json")
            flip_phase(sp, "9", to_status="complete")
            loaded = read_state(sp)
            self.assertEqual(loaded.phase, "9")
            self.assertEqual(loaded.status, "complete")

    def test_feature_dir_in_path_resolves_correctly(self):
        """state_path + flip_phase resolve correctly when path is inside feature dir."""
        with tempfile.TemporaryDirectory() as td:
            feature_dir = os.path.join(td, "specs", "001-auth")
            os.makedirs(feature_dir, exist_ok=True)
            sp = state_path(feature_dir)
            state = flip_phase(sp, "preflight")
            self.assertTrue(sp.endswith("verify-state.json"))
            self.assertEqual(state.phase, "preflight")

    # --- verdict recording tests (Fix B) ---

    def test_flip_phase_with_verdict_records_it(self):
        """flip_phase(verdict=...) sets state.verdict in the returned state."""
        with tempfile.TemporaryDirectory() as td:
            sp = os.path.join(td, "verify-state.json")
            state = flip_phase(sp, "9", verdict="NEEDS WORK")
            self.assertEqual(state.verdict, "NEEDS WORK")

    def test_flip_phase_with_verdict_persists_to_disk(self):
        """The verdict written by flip_phase is readable back from disk."""
        with tempfile.TemporaryDirectory() as td:
            sp = os.path.join(td, "verify-state.json")
            flip_phase(sp, "9", verdict="APPROVED")
            loaded = read_state(sp)
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.verdict, "APPROVED")

    def test_flip_phase_without_verdict_leaves_existing_verdict_unchanged(self):
        """Omitting verdict param does not blank an already-set verdict (back-compat)."""
        with tempfile.TemporaryDirectory() as td:
            sp = os.path.join(td, "verify-state.json")
            # First flip sets a verdict.
            flip_phase(sp, "9", verdict="REJECTED")
            # Second flip does NOT pass verdict — must not clear the first one.
            state = flip_phase(sp, "9", to_status="complete")
            self.assertEqual(state.verdict, "REJECTED")

    def test_flip_phase_without_verdict_param_default_empty_on_fresh_state(self):
        """Without verdict param on a fresh state, verdict stays the VerifyState default ('')."""
        with tempfile.TemporaryDirectory() as td:
            sp = os.path.join(td, "verify-state.json")
            state = flip_phase(sp, "preflight")
            self.assertEqual(state.verdict, "")

    def test_flip_phase_verdict_approved(self):
        """APPROVED verdict round-trips correctly."""
        with tempfile.TemporaryDirectory() as td:
            sp = os.path.join(td, "verify-state.json")
            state = flip_phase(sp, "9", verdict="APPROVED")
            self.assertEqual(state.verdict, "APPROVED")
            loaded = read_state(sp)
            self.assertEqual(loaded.verdict, "APPROVED")

    def test_flip_phase_verdict_rejected(self):
        """REJECTED verdict round-trips correctly."""
        with tempfile.TemporaryDirectory() as td:
            sp = os.path.join(td, "verify-state.json")
            state = flip_phase(sp, "9", verdict="REJECTED")
            self.assertEqual(state.verdict, "REJECTED")

    def test_flip_phase_verdict_does_not_affect_other_fields(self):
        """Setting verdict must not alter phase, status, feature_dir, scope_files."""
        with tempfile.TemporaryDirectory() as td:
            sp = os.path.join(td, "verify-state.json")
            write_state(
                sp,
                VerifyState(
                    phase="8",
                    feature_dir="specs/002-dash",
                    status="in_progress",
                    scope_files=["src/dash.py"],
                ),
            )
            state = flip_phase(sp, "9", to_status="complete", verdict="APPROVED")
            self.assertEqual(state.phase, "9")
            self.assertEqual(state.status, "complete")
            self.assertEqual(state.feature_dir, "specs/002-dash")
            self.assertEqual(state.scope_files, ["src/dash.py"])
            self.assertEqual(state.verdict, "APPROVED")


class TestVerifyStateDefaults(unittest.TestCase):
    def test_default_phase_empty_string(self):
        self.assertEqual(VerifyState().phase, "")

    def test_default_feature_dir_empty_string(self):
        self.assertEqual(VerifyState().feature_dir, "")

    def test_default_status_in_progress(self):
        self.assertEqual(VerifyState().status, "in_progress")

    def test_default_out_path_empty_string(self):
        self.assertEqual(VerifyState().out_path, "")

    def test_default_scope_files_is_list(self):
        self.assertIsInstance(VerifyState().scope_files, list)
        self.assertEqual(VerifyState().scope_files, [])

    def test_default_verdict_empty_string(self):
        self.assertEqual(VerifyState().verdict, "")

    def test_scope_files_no_shared_default(self):
        """Verify field(default_factory=list) — no shared mutable default."""
        a = VerifyState()
        b = VerifyState()
        a.scope_files.append("file.py")
        self.assertEqual(b.scope_files, [])

    def test_out_path_default_not_review_md(self):
        """Verify out_path default is empty (not 'review.md' by mistake)."""
        self.assertEqual(VerifyState().out_path, "")


# ---------------------------------------------------------------------------
# CLI-level tests for check-status-and-flip --verdict (Fix B)
# ---------------------------------------------------------------------------


class TestCheckStatusAndFlipVerdictCLI(unittest.TestCase):
    """Test the --verdict flag on check-status-and-flip via the CLI main() entry point."""

    def _run(self, argv, feature_dir):
        """Run cli_main with --feature-dir pointing at feature_dir."""
        return cli_main(["check-status-and-flip", "--feature-dir", feature_dir] + argv)

    def test_verdict_flag_records_in_state_file(self):
        """--verdict APPROVED round-trips into verify-state.json."""
        with tempfile.TemporaryDirectory() as td:
            rc = self._run(["--to", "9", "--verdict", "APPROVED"], td)
            self.assertEqual(rc, 0)
            loaded = read_state(state_path(td))
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.verdict, "APPROVED")

    def test_verdict_needs_work_round_trips(self):
        """--verdict 'NEEDS WORK' (two-word value) round-trips into verify-state.json."""
        with tempfile.TemporaryDirectory() as td:
            rc = self._run(["--to", "9", "--verdict", "NEEDS WORK"], td)
            self.assertEqual(rc, 0)
            loaded = read_state(state_path(td))
            self.assertEqual(loaded.verdict, "NEEDS WORK")

    def test_without_verdict_flag_leaves_existing_verdict_unchanged(self):
        """A flip WITHOUT --verdict must not clear a previously-recorded verdict."""
        with tempfile.TemporaryDirectory() as td:
            # First flip: set verdict.
            self._run(["--to", "9", "--verdict", "APPROVED"], td)
            # Second flip: no --verdict flag.
            rc = self._run(["--to", "9", "--status", "complete"], td)
            self.assertEqual(rc, 0)
            loaded = read_state(state_path(td))
            self.assertEqual(loaded.verdict, "APPROVED")

    def test_without_verdict_flag_on_fresh_state_verdict_stays_empty(self):
        """A flip WITHOUT --verdict on a fresh state leaves verdict as ''."""
        with tempfile.TemporaryDirectory() as td:
            rc = self._run(["--to", "preflight"], td)
            self.assertEqual(rc, 0)
            loaded = read_state(state_path(td))
            self.assertEqual(loaded.verdict, "")

    def test_verdict_in_stdout_json(self):
        """The JSON emitted to stdout after a flip includes the verdict field."""
        import io
        from contextlib import redirect_stdout

        with tempfile.TemporaryDirectory() as td:
            buf = io.StringIO()
            with redirect_stdout(buf):
                self._run(["--to", "9", "--verdict", "REJECTED"], td)
            data = json.loads(buf.getvalue())
            self.assertEqual(data["verdict"], "REJECTED")


if __name__ == "__main__":
    unittest.main()
