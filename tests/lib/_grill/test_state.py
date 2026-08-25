"""Tests for src/devforge/lib/_grill/_state.py.

Coverage:
  state_path          — returns absolute path ending in grill-state.json
  read_state          — missing file, corrupt JSON, round-trip, unknown-key tolerance
  write_state         — atomic write; parent dir created on demand
  flip_phase          — from absent state, from existing state, with status, empty raises
  GrillState          — default values, list field isolation
  GRILL_PHASES        — constant contains the expected flow phases
  adversary_ran       — True for complete/clean (each its own test), False for
                         failed/missing/unset, pre-change-file round trip
  compute_plan_sha256 — write/read round trip stability, single-char-edit
                         sensitivity, unicode content
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

from _grill._state import (  # noqa: E402
    GRILL_PHASES,
    GrillState,
    adversary_ran,
    compute_plan_sha256,
    flip_phase,
    read_state,
    state_path,
    write_state,
)
# adversary_status vocabulary: the values below are asserted from
# _shared._consume's own constants, not re-typed as bare literals, so this
# test file cannot drift from the source of truth it is verifying against.
from _shared._consume import STATUS_FAILED, STATUS_MISSING  # noqa: E402


class TestStatePath(unittest.TestCase):
    def test_returns_absolute_path(self):
        result = state_path("/some/feature")
        self.assertTrue(os.path.isabs(result))

    def test_path_ends_with_state_json(self):
        result = state_path("/some/feature")
        self.assertTrue(result.endswith("grill-state.json"))

    def test_relative_root_becomes_absolute(self):
        result = state_path("relative/path")
        self.assertTrue(os.path.isabs(result))

    def test_expected_structure(self):
        result = state_path("/specs/001-auth")
        self.assertEqual(result, "/specs/001-auth/grill-state.json")

    def test_different_feature_dirs_give_different_paths(self):
        p1 = state_path("/specs/001-auth")
        p2 = state_path("/specs/002-dashboard")
        self.assertNotEqual(p1, p2)


class TestReadState(unittest.TestCase):
    def test_missing_file_returns_none(self):
        self.assertIsNone(read_state("/nonexistent/path/grill-state.json"))

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
            sp = os.path.join(td, "grill-state.json")
            original = GrillState(
                phase="attack",
                feature_dir="specs/001-auth",
                status="in_progress",
                out_path="specs/001-auth/grill.md",
                scope_files=["src/auth/login.py", "src/auth/middleware.py"],
                agent_assignments=["security-reviewer", "qa-reviewer"],
            )
            write_state(sp, original)
            loaded = read_state(sp)
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.phase, "attack")
            self.assertEqual(loaded.feature_dir, "specs/001-auth")
            self.assertEqual(loaded.status, "in_progress")
            self.assertEqual(loaded.out_path, "specs/001-auth/grill.md")
            self.assertEqual(
                loaded.scope_files, ["src/auth/login.py", "src/auth/middleware.py"]
            )
            self.assertEqual(
                loaded.agent_assignments, ["security-reviewer", "qa-reviewer"]
            )

    def test_unknown_keys_tolerated(self):
        with tempfile.TemporaryDirectory() as td:
            sp = os.path.join(td, "grill-state.json")
            data = {
                "phase": "validate",
                "feature_dir": "specs/002-dashboard",
                "status": "complete",
                "out_path": "specs/002-dashboard/grill.md",
                "scope_files": [],
                "agent_assignments": [],
                "future_unknown_field": "ignored",
                "another_unknown": 42,
            }
            with open(sp, "w", encoding="utf-8") as fh:
                json.dump(data, fh)
            state = read_state(sp)
            self.assertIsNotNone(state)
            self.assertEqual(state.phase, "validate")
            self.assertEqual(state.status, "complete")
            # Unknown fields should not appear on the object.
            self.assertFalse(hasattr(state, "future_unknown_field"))
            self.assertFalse(hasattr(state, "another_unknown"))


class TestWriteState(unittest.TestCase):
    def test_creates_parent_dir(self):
        with tempfile.TemporaryDirectory() as td:
            sp = os.path.join(td, "specs", "001-auth", "grill-state.json")
            self.assertFalse(os.path.exists(sp))
            write_state(sp, GrillState())
            self.assertTrue(os.path.exists(sp))

    def test_output_is_valid_json(self):
        with tempfile.TemporaryDirectory() as td:
            sp = os.path.join(td, "grill-state.json")
            write_state(sp, GrillState(phase="scope"))
            with open(sp, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            self.assertEqual(data["phase"], "scope")

    def test_atomic_write_no_leftover_tmp(self):
        """No .json.tmp files should remain after a successful write."""
        with tempfile.TemporaryDirectory() as td:
            sp = os.path.join(td, "grill-state.json")
            write_state(sp, GrillState())
            tmp_files = [f for f in os.listdir(td) if f.endswith(".json.tmp")]
            self.assertEqual(tmp_files, [])

    def test_written_json_has_all_fields(self):
        with tempfile.TemporaryDirectory() as td:
            sp = os.path.join(td, "grill-state.json")
            write_state(sp, GrillState())
            with open(sp, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            for key in ("phase", "feature_dir", "status", "out_path",
                        "scope_files", "agent_assignments"):
                self.assertIn(key, data)

    def test_output_path_contains_grill_md_when_set(self):
        """out_path naming convention: grill.md, not review.md."""
        with tempfile.TemporaryDirectory() as td:
            sp = os.path.join(td, "grill-state.json")
            write_state(sp, GrillState(out_path="specs/001-auth/grill.md"))
            with open(sp, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            self.assertIn("grill.md", data["out_path"])


class TestFlipPhase(unittest.TestCase):
    def test_from_absent_state_creates_fresh(self):
        with tempfile.TemporaryDirectory() as td:
            sp = os.path.join(td, "grill-state.json")
            state = flip_phase(sp, "scope")
            self.assertEqual(state.phase, "scope")
            self.assertEqual(state.status, "in_progress")  # default
            self.assertTrue(os.path.exists(sp))

    def test_from_existing_state_updates_phase(self):
        with tempfile.TemporaryDirectory() as td:
            sp = os.path.join(td, "grill-state.json")
            write_state(
                sp,
                GrillState(phase="scope", feature_dir="specs/001", status="in_progress"),
            )
            state = flip_phase(sp, "attack")
            self.assertEqual(state.phase, "attack")
            # Other fields preserved.
            self.assertEqual(state.feature_dir, "specs/001")
            self.assertEqual(state.status, "in_progress")

    def test_with_status_update(self):
        with tempfile.TemporaryDirectory() as td:
            sp = os.path.join(td, "grill-state.json")
            state = flip_phase(sp, "report", to_status="complete")
            self.assertEqual(state.phase, "report")
            self.assertEqual(state.status, "complete")

    def test_without_to_status_leaves_status_unchanged(self):
        with tempfile.TemporaryDirectory() as td:
            sp = os.path.join(td, "grill-state.json")
            write_state(sp, GrillState(phase="refute", status="in_progress"))
            state = flip_phase(sp, "classify")
            self.assertEqual(state.status, "in_progress")

    def test_empty_phase_raises_value_error(self):
        with tempfile.TemporaryDirectory() as td:
            sp = os.path.join(td, "grill-state.json")
            with self.assertRaises(ValueError):
                flip_phase(sp, "")

    def test_whitespace_only_phase_raises_value_error(self):
        with tempfile.TemporaryDirectory() as td:
            sp = os.path.join(td, "grill-state.json")
            with self.assertRaises(ValueError):
                flip_phase(sp, "   ")

    def test_result_persisted_to_disk(self):
        with tempfile.TemporaryDirectory() as td:
            sp = os.path.join(td, "grill-state.json")
            flip_phase(sp, "report", to_status="complete")
            loaded = read_state(sp)
            self.assertEqual(loaded.phase, "report")
            self.assertEqual(loaded.status, "complete")

    def test_all_grill_phases_accepted(self):
        """Each canonical grill phase can be written and read back."""
        with tempfile.TemporaryDirectory() as td:
            sp = os.path.join(td, "grill-state.json")
            for phase in GRILL_PHASES:
                state = flip_phase(sp, phase)
                self.assertEqual(state.phase, phase)

    def test_feature_dir_in_path_resolves_correctly(self):
        """state_path + flip_phase resolve correctly when path is inside feature dir."""
        with tempfile.TemporaryDirectory() as td:
            feature_dir = os.path.join(td, "specs", "001-auth")
            os.makedirs(feature_dir, exist_ok=True)
            sp = state_path(feature_dir)
            state = flip_phase(sp, "scope")
            self.assertTrue(sp.endswith("grill-state.json"))
            self.assertEqual(state.phase, "scope")


class TestGrillStateDefaults(unittest.TestCase):
    def test_default_phase_empty_string(self):
        self.assertEqual(GrillState().phase, "")

    def test_default_feature_dir_empty_string(self):
        self.assertEqual(GrillState().feature_dir, "")

    def test_default_status_in_progress(self):
        self.assertEqual(GrillState().status, "in_progress")

    def test_default_out_path_empty_string(self):
        self.assertEqual(GrillState().out_path, "")

    def test_default_scope_files_is_list(self):
        self.assertIsInstance(GrillState().scope_files, list)
        self.assertEqual(GrillState().scope_files, [])

    def test_default_agent_assignments_is_list(self):
        self.assertIsInstance(GrillState().agent_assignments, list)
        self.assertEqual(GrillState().agent_assignments, [])

    def test_scope_files_no_shared_default(self):
        """Verify field(default_factory=list) — no shared mutable default."""
        a = GrillState()
        b = GrillState()
        a.scope_files.append("file.py")
        self.assertEqual(b.scope_files, [])

    def test_agent_assignments_no_shared_default(self):
        a = GrillState()
        b = GrillState()
        a.agent_assignments.append("security-reviewer")
        self.assertEqual(b.agent_assignments, [])


class TestGrillPhasesConstant(unittest.TestCase):
    def test_all_expected_phases_present(self):
        expected = ("scope", "attack", "validate", "refute", "classify", "report")
        for phase in expected:
            self.assertIn(phase, GRILL_PHASES)

    def test_phases_count(self):
        self.assertEqual(len(GRILL_PHASES), 6)

    def test_phases_is_tuple(self):
        self.assertIsInstance(GRILL_PHASES, tuple)


class TestAdversaryStatusDefault(unittest.TestCase):
    def test_default_adversary_status_empty_string(self):
        """Never defaults to a satisfying value — the unset sentinel is ''."""
        self.assertEqual(GrillState().adversary_status, "")

    def test_default_plan_sha256_empty_string(self):
        self.assertEqual(GrillState().plan_sha256, "")


class TestAdversaryRan(unittest.TestCase):
    def test_true_for_complete(self):
        """Own test — the gate accepts 'complete'."""
        state = GrillState(adversary_status="complete")
        self.assertTrue(adversary_ran(state))

    def test_true_for_clean(self):
        """Own test, NOT folded into the 'complete' case — a clean run (the
        adversary ran and grounded zero findings) is a genuine pass and the
        whole design rests on this distinction being visible on its own.
        """
        state = GrillState(adversary_status="clean")
        self.assertTrue(adversary_ran(state))

    def test_false_for_failed_missing_and_unset(self):
        self.assertFalse(adversary_ran(GrillState(adversary_status=STATUS_FAILED)))
        self.assertFalse(adversary_ran(GrillState(adversary_status=STATUS_MISSING)))
        self.assertFalse(adversary_ran(GrillState(adversary_status="")))

    def test_pre_change_file_round_trips_to_not_ran(self):
        """A grill-state.json written WITHOUT adversary_status (simulating a
        file from before this field existed) must read back successfully
        with adversary_status == '' and adversary_ran() == False — never a
        crash, and never a silent default to satisfied.
        """
        with tempfile.TemporaryDirectory() as td:
            sp = os.path.join(td, "grill-state.json")
            pre_change_data = {
                "phase": "report",
                "feature_dir": "specs/001-auth",
                "status": "complete",
                "out_path": "specs/001-auth/grill.md",
                "scope_files": [],
                "agent_assignments": [],
            }
            with open(sp, "w", encoding="utf-8") as fh:
                json.dump(pre_change_data, fh)

            state = read_state(sp)

            self.assertIsNotNone(state)
            self.assertEqual(state.adversary_status, "")
            self.assertFalse(adversary_ran(state))


class TestComputePlanSha256(unittest.TestCase):
    def test_round_trip_stable(self):
        """Same content, re-read, re-hashed → identical digest."""
        with tempfile.TemporaryDirectory() as td:
            plan_path = os.path.join(td, "plan.md")
            with open(plan_path, "w", encoding="utf-8") as fh:
                fh.write("# Plan\n\nSome plan content.\n")

            digest_1 = compute_plan_sha256(plan_path)
            digest_2 = compute_plan_sha256(plan_path)
            self.assertEqual(digest_1, digest_2)
            self.assertEqual(len(digest_1), 64)  # sha256 hex digest length

    def test_persisted_on_state_survives_write_read_round_trip(self):
        with tempfile.TemporaryDirectory() as td:
            plan_path = os.path.join(td, "plan.md")
            with open(plan_path, "w", encoding="utf-8") as fh:
                fh.write("# Plan\n\nOriginal content.\n")
            digest = compute_plan_sha256(plan_path)

            sp = os.path.join(td, "grill-state.json")
            write_state(sp, GrillState(plan_sha256=digest))
            loaded = read_state(sp)

            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.plan_sha256, digest)

    def test_single_character_edit_changes_digest(self):
        with tempfile.TemporaryDirectory() as td:
            plan_path = os.path.join(td, "plan.md")
            with open(plan_path, "w", encoding="utf-8") as fh:
                fh.write("# Plan\n\nOriginal content.\n")
            original_digest = compute_plan_sha256(plan_path)

            with open(plan_path, "w", encoding="utf-8") as fh:
                fh.write("# Plan\n\nOriginel content.\n")  # one char changed
            edited_digest = compute_plan_sha256(plan_path)

            self.assertNotEqual(original_digest, edited_digest)

    def test_unicode_content_hashes_without_error(self):
        """compute_plan_sha256 opens 'rb' (raw bytes, no text decoding), so
        non-ASCII plan content carries no real risk -- this test documents
        that rather than guarding against a plausible failure. Uses
        non-alphabetic Unicode (an em dash, accented Latin, an emoji) so the
        test file's own content stays English per this repo's file-content
        convention, while still exercising multi-byte UTF-8 sequences.
        """
        with tempfile.TemporaryDirectory() as td:
            plan_path = os.path.join(td, "plan.md")
            with open(plan_path, "w", encoding="utf-8") as fh:
                fh.write("# Plan\n\nCafé naıve — done \U0001F600.\n")

            digest = compute_plan_sha256(plan_path)

            self.assertEqual(len(digest), 64)
            # Stable on re-hash, same as the ASCII case.
            self.assertEqual(digest, compute_plan_sha256(plan_path))


if __name__ == "__main__":
    unittest.main()
