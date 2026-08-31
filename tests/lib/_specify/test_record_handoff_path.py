"""Tests for specify_helper record-handoff-path (cmd_record_handoff_path).

91-FEATURE-DIR-IDENTITY-AND-PROVENANCE-PLAN.md Phase 3's residual:
src/commands/specify/main.md Phase 0.4's `cold` arm resolves a bucketed
feature directory (specs/<YYYY>/<MM>/<leaf>/) exactly like `yes-most-recent`
does, but skips import-handoff -- the only verb that ever wrote
state["source"]["handoff_path"] -- so resolve_bucketed_feature_dir
(_schema.py) had nothing to read back and write-design-anchor /
finalize-handoff both exited 2 on a bucketed cold pick. record-handoff-path
is the fix: it records the SAME path import-handoff would have, without
reading the handoff's content.

These are unit tests of cmd_record_handoff_path called directly with a fake
argparse.Namespace (mirroring test_finalize_handoff.py's own convention).
The real-producer round trip through the actual CLI, allocate_feature_dir,
and write-design-anchor / finalize-handoff lives in
tests/lib/test_specify_helper.py::TestBucketedPathColdArmReachesDesignAnchorAndHandoff.

Stdlib only. Python 3.8+. No third-party deps.
"""

import argparse
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

# ---------------------------------------------------------------------------
# Import path setup.
# ---------------------------------------------------------------------------

_LIB_DIR = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "src" / "devforge" / "lib"
)
if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _specify._cmds_handoff import cmd_record_handoff_path  # noqa: E402
from _specify._state import default_state  # noqa: E402


def _make_args(devforge_dir, handoff_path=None):
    return argparse.Namespace(
        devforge_dir=str(devforge_dir),
        handoff_path=handoff_path,
    )


def _write_state(devforge_dir, state):
    Path(devforge_dir).mkdir(parents=True, exist_ok=True)
    state_path = Path(devforge_dir) / "specify-state.json"
    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    return state_path


def _run_capturing_stderr(args):
    """Call cmd_record_handoff_path, returning (rc, stderr_text)."""
    captured = io.StringIO()
    old_stderr = sys.stderr
    sys.stderr = captured
    try:
        rc = cmd_record_handoff_path(args)
    finally:
        sys.stderr = old_stderr
    return rc, captured.getvalue()


class TestRecordHandoffPath(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        # repo_root == self.tmp; devforge_dir sits directly under it, matching
        # every real /specify install (devforge_dir.parent == repo_root).
        self.devforge_dir = self.tmp / ".devforge"
        self.devforge_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self._tmp.cleanup()

    def _state_path(self):
        return self.devforge_dir / "specify-state.json"

    def _read_state(self):
        return json.loads(self._state_path().read_text(encoding="utf-8"))

    # -- Boundary: missing / empty --handoff-path -------------------------

    def test_missing_handoff_path_arg_exits_2(self):
        args = _make_args(self.devforge_dir, handoff_path=None)
        rc, err = _run_capturing_stderr(args)
        self.assertEqual(rc, 2)
        self.assertIn("--handoff-path is required", err)

    def test_empty_string_handoff_path_arg_exits_2(self):
        """Empty string is falsy, same as omitted -- boundary value."""
        args = _make_args(self.devforge_dir, handoff_path="")
        rc, err = _run_capturing_stderr(args)
        self.assertEqual(rc, 2)
        self.assertIn("--handoff-path is required", err)

    # -- Boundary: nonexistent path -----------------------------------------

    def test_nonexistent_handoff_path_exits_2(self):
        missing = self.tmp / "specs" / "2026" / "08" / "ghost" / "research-handoff.json"
        args = _make_args(self.devforge_dir, handoff_path=str(missing))
        rc, err = _run_capturing_stderr(args)
        self.assertEqual(rc, 2)
        self.assertIn("handoff-path not found", err)
        # No state file created as a side effect of a failed call.
        self.assertFalse(self._state_path().exists())

    # -- Happy path: records handoff_path only, root-relative ---------------

    def test_records_root_relative_handoff_path(self):
        feature_dir = self.tmp / "specs" / "2026" / "08" / "cold-feature"
        feature_dir.mkdir(parents=True)
        handoff_out = feature_dir / "research-handoff.json"
        handoff_out.write_text("{}\n", encoding="utf-8")

        _write_state(self.devforge_dir, default_state())
        args = _make_args(self.devforge_dir, handoff_path=str(handoff_out))
        rc, err = _run_capturing_stderr(args)
        self.assertEqual(rc, 0, err)

        state = self._read_state()
        self.assertEqual(
            state["source"]["handoff_path"],
            "specs/2026/08/cold-feature/research-handoff.json",
        )
        # No leading '/' -- root-relative, matching import-handoff's own
        # convention (68-INTAKE-OWNS-FEATURE-DIR-PLAN.md D9(d)).
        self.assertFalse(state["source"]["handoff_path"].startswith("/"))

    def test_does_not_set_handoff_kind_or_any_content_field(self):
        """The whole point of this verb: it records WHERE, never WHAT.
        handoff_kind and every content-bearing field stay at default_state()'s
        values -- proving no content pre-seed happened."""
        feature_dir = self.tmp / "specs" / "2026" / "08" / "cold-feature"
        feature_dir.mkdir(parents=True)
        handoff_out = feature_dir / "research-handoff.json"
        handoff_out.write_text("{}\n", encoding="utf-8")

        fresh = default_state()
        _write_state(self.devforge_dir, fresh)
        args = _make_args(self.devforge_dir, handoff_path=str(handoff_out))
        rc, err = _run_capturing_stderr(args)
        self.assertEqual(rc, 0, err)

        state = self._read_state()
        self.assertIsNone(state["source"]["handoff_kind"])
        self.assertIsNone(state["source"]["research_completed_at"])
        self.assertIsNone(state["source"]["discover_completed_at"])
        self.assertIsNone(state["source"]["discover_recommended_summary"])
        self.assertIsNone(state["spec_type"])
        self.assertIs(state["spec_type_seeded_by_upstream"], False)
        self.assertEqual(state["constraints"], [])
        self.assertEqual(state["affected_areas"], [])
        self.assertEqual(state["risks"], [])
        self.assertEqual(state["open_questions"], [])
        self.assertEqual(
            state["design_anchor"], {"kind": "", "file": "", "selectors": []},
        )
        # Everything else in the fresh default is untouched too.
        untouched = dict(fresh)
        untouched["source"] = state["source"]  # only source.handoff_path changes
        self.assertEqual(state, untouched)

    def test_relative_handoff_path_resolved_against_cwd(self):
        """Mirrors import-handoff's own cwd-relative resolution."""
        feature_dir = self.tmp / "specs" / "2026" / "08" / "cold-feature"
        feature_dir.mkdir(parents=True)
        handoff_out = feature_dir / "research-handoff.json"
        handoff_out.write_text("{}\n", encoding="utf-8")

        _write_state(self.devforge_dir, default_state())
        args = _make_args(
            self.devforge_dir,
            handoff_path="specs/2026/08/cold-feature/research-handoff.json",
        )
        import os
        original_cwd = os.getcwd()
        os.chdir(str(self.tmp))
        try:
            rc, err = _run_capturing_stderr(args)
        finally:
            os.chdir(original_cwd)
        self.assertEqual(rc, 0, err)

        state = self._read_state()
        self.assertEqual(
            state["source"]["handoff_path"],
            "specs/2026/08/cold-feature/research-handoff.json",
        )

    def test_outside_repo_root_falls_back_to_absolute_path(self):
        """A handoff sitting outside repo_root (devforge_dir's parent)
        cannot be made root-relative -- _root_relative's documented
        fallback is the absolute string, matching import-handoff's own
        outside-root behavior (TestImportHandoffOutsideRoot in
        tests/lib/test_specify_helper.py)."""
        with tempfile.TemporaryDirectory() as other_tmp:
            other_path = Path(other_tmp)
            handoff_out = other_path / "research-handoff.json"
            handoff_out.write_text("{}\n", encoding="utf-8")

            _write_state(self.devforge_dir, default_state())
            args = _make_args(self.devforge_dir, handoff_path=str(handoff_out))
            rc, err = _run_capturing_stderr(args)
            self.assertEqual(rc, 0, err)

            state = self._read_state()
            self.assertEqual(
                Path(state["source"]["handoff_path"]).resolve(),
                handoff_out.resolve(),
            )
            self.assertTrue(Path(state["source"]["handoff_path"]).is_absolute())

    # -- Resumption: idempotent double-call ----------------------------------

    def test_idempotent_double_call(self):
        feature_dir = self.tmp / "specs" / "2026" / "08" / "cold-feature"
        feature_dir.mkdir(parents=True)
        handoff_out = feature_dir / "research-handoff.json"
        handoff_out.write_text("{}\n", encoding="utf-8")

        _write_state(self.devforge_dir, default_state())
        args = _make_args(self.devforge_dir, handoff_path=str(handoff_out))

        rc1, err1 = _run_capturing_stderr(args)
        self.assertEqual(rc1, 0, err1)
        state_after_first = self._read_state()

        rc2, err2 = _run_capturing_stderr(args)
        self.assertEqual(rc2, 0, err2)
        state_after_second = self._read_state()

        self.assertEqual(state_after_first, state_after_second)

    # -- Malformed / legacy state shape --------------------------------------

    def test_missing_source_key_in_state_does_not_crash(self):
        """A pre-plan-91 state dict with no 'source' key at all -- the same
        defensive rebuild import-handoff's two arms already perform."""
        state = default_state()
        del state["source"]
        _write_state(self.devforge_dir, state)

        feature_dir = self.tmp / "specs" / "2026" / "08" / "cold-feature"
        feature_dir.mkdir(parents=True)
        handoff_out = feature_dir / "research-handoff.json"
        handoff_out.write_text("{}\n", encoding="utf-8")

        args = _make_args(self.devforge_dir, handoff_path=str(handoff_out))
        rc, err = _run_capturing_stderr(args)
        self.assertEqual(rc, 0, err)

        state_after = self._read_state()
        self.assertEqual(
            state_after["source"]["handoff_path"],
            "specs/2026/08/cold-feature/research-handoff.json",
        )
        self.assertIsNone(state_after["source"]["handoff_kind"])

    def test_stdout_reports_recorded_path(self):
        feature_dir = self.tmp / "specs" / "2026" / "08" / "cold-feature"
        feature_dir.mkdir(parents=True)
        handoff_out = feature_dir / "research-handoff.json"
        handoff_out.write_text("{}\n", encoding="utf-8")

        _write_state(self.devforge_dir, default_state())
        args = _make_args(self.devforge_dir, handoff_path=str(handoff_out))

        captured = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        try:
            rc = cmd_record_handoff_path(args)
        finally:
            sys.stdout = old_stdout
        self.assertEqual(rc, 0)
        self.assertIn(
            "recorded: specs/2026/08/cold-feature/research-handoff.json",
            captured.getvalue(),
        )


if __name__ == "__main__":
    unittest.main()
