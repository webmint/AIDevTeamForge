"""Tests for Phase 1.5 finding landing mechanism.

Covers:
- round-trip: record-finding (unlanded) → add-ac --finding-ref → verify-coverage passes
- round-trip via record-constraint --finding-ref
- round-trip via record-out-of-scope --finding-ref (confirm flip, not just store)
- round-trip via record-risk --finding-ref
- multi-ref: one AC with two --finding-ref lands both findings
- set-finding-landed standalone flip → verify-coverage passes
- error: --finding-ref naming unknown id → exit 2 + stderr names it
- error: set-finding-landed unknown --finding-id → exit 2 + stderr names it
- error: set-finding-landed --landed-in unlanded → exit 2
- idempotent: re-landing to same bucket is no-op success
- re-land: landing to different bucket succeeds (overwrites)
- OOS --finding-ref with empty string → no flip, existing behaviour preserved

All tests use real cmd_* producers (no hand-edited state JSON) via the
actual argparse CLI (specify_helper.main) so they round-trip through the
real producer and consumer.

Stdlib only. Python 3.8+. No third-party deps.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Import path setup.
# ---------------------------------------------------------------------------

_LIB_DIR = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "src" / "devforge" / "lib"
)
if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

import specify_helper  # noqa: E402 (launcher re-exports main)
from _specify._cli import main  # noqa: E402
from _specify._state import _load_state  # noqa: E402


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _run(*argv: str, devforge_dir: str) -> int:
    """Run specify_helper.main with --devforge-dir prepended."""
    return main(["--devforge-dir", devforge_dir] + list(argv))


def _run_capture_stderr(*argv: str, devforge_dir: str):
    """Run, return (exit_code, stderr_text)."""
    buf = io.StringIO()
    old = sys.stderr
    sys.stderr = buf
    try:
        rc = main(["--devforge-dir", devforge_dir] + list(argv))
    finally:
        sys.stderr = old
    return rc, buf.getvalue()


def _run_capture_stdout(*argv: str, devforge_dir: str):
    """Run, return (exit_code, stdout_text)."""
    buf = io.StringIO()
    old = sys.stdout
    sys.stdout = buf
    try:
        rc = main(["--devforge-dir", devforge_dir] + list(argv))
    finally:
        sys.stdout = old
    return rc, buf.getvalue()


def _reset(devforge_dir: str) -> None:
    _run("reset-state", devforge_dir=devforge_dir)


def _record_finding(
    devforge_dir: str,
    source_path: str = "constitution.md",
    content: str = "Test finding content",
) -> str:
    """Record a finding and return its finding_id (from stdout)."""
    buf = io.StringIO()
    old = sys.stdout
    sys.stdout = buf
    try:
        rc = main([
            "--devforge-dir", devforge_dir,
            "record-finding",
            "--source-path", source_path,
            "--content", content,
        ])
    finally:
        sys.stdout = old
    assert rc == 0, "record-finding failed"
    return buf.getvalue().strip()


def _load(devforge_dir: str) -> Dict[str, Any]:
    return _load_state(devforge_dir)


def _finding_by_id(state: Dict[str, Any], fid: str) -> Optional[Dict[str, Any]]:
    for f in state["findings"]:
        if f.get("finding_id") == fid:
            return f
    return None


# ---------------------------------------------------------------------------
# Shared setup mixin
# ---------------------------------------------------------------------------


class _TmpDirMixin(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self.devforge_dir = str(Path(self._tmp) / ".devforge")
        _reset(self.devforge_dir)


# ---------------------------------------------------------------------------
# AC landing tests
# ---------------------------------------------------------------------------


class TestAddAcLanding(_TmpDirMixin):
    def _add_ac(self, finding_ref: Optional[str] = None) -> str:
        """Add an AC that passes all validators; return its ac_id."""
        argv = [
            "add-ac",
            "--subsection", "behavior_change",
            "--ears-variant", "event_driven",
            "--statement", "WHEN a user logs in, the system shall emit an audit event.",
            "--verification-command", "pytest tests/",
        ]
        if finding_ref:
            argv += ["--finding-ref", finding_ref]
        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            rc = main(["--devforge-dir", self.devforge_dir] + argv)
        finally:
            sys.stdout = old
        self.assertEqual(rc, 0, "add-ac failed")
        return buf.getvalue().strip()

    def test_add_ac_without_finding_ref_does_not_flip(self):
        fid = _record_finding(self.devforge_dir)
        self._add_ac()
        state = _load(self.devforge_dir)
        f = _finding_by_id(state, fid)
        self.assertIsNotNone(f)
        self.assertEqual(f["landed_in"], "unlanded")

    def test_add_ac_with_finding_ref_flips_landed_in(self):
        fid = _record_finding(self.devforge_dir)
        ac_id = self._add_ac(finding_ref=fid)
        state = _load(self.devforge_dir)
        f = _finding_by_id(state, fid)
        self.assertIsNotNone(f)
        self.assertEqual(f["landed_in"], "AC")
        self.assertEqual(f["landed_ref"], ac_id)

    def test_add_ac_with_finding_ref_verify_coverage_passes(self):
        fid = _record_finding(self.devforge_dir)
        self._add_ac(finding_ref=fid)
        rc = _run("verify-coverage", devforge_dir=self.devforge_dir)
        self.assertEqual(rc, 0)

    def test_add_ac_multi_ref_lands_both_findings(self):
        fid1 = _record_finding(
            self.devforge_dir, content="Finding one for multi-ref test",
        )
        fid2 = _record_finding(
            self.devforge_dir, content="Finding two for multi-ref test",
        )
        # Use two --finding-ref flags
        argv = [
            "--devforge-dir", self.devforge_dir,
            "add-ac",
            "--subsection", "behavior_change",
            "--ears-variant", "event_driven",
            "--statement", "WHEN a user logs in, the system shall emit an audit event.",
            "--finding-ref", fid1,
            "--finding-ref", fid2,
        ]
        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            rc = main(argv)
        finally:
            sys.stdout = old
        self.assertEqual(rc, 0)
        ac_id = buf.getvalue().strip()
        state = _load(self.devforge_dir)
        f1 = _finding_by_id(state, fid1)
        f2 = _finding_by_id(state, fid2)
        self.assertEqual(f1["landed_in"], "AC")
        self.assertEqual(f1["landed_ref"], ac_id)
        self.assertEqual(f2["landed_in"], "AC")
        self.assertEqual(f2["landed_ref"], ac_id)

    def test_add_ac_multi_ref_verify_coverage_passes_for_both(self):
        fid1 = _record_finding(
            self.devforge_dir, content="Finding alpha",
        )
        fid2 = _record_finding(
            self.devforge_dir, content="Finding beta",
        )
        main([
            "--devforge-dir", self.devforge_dir,
            "add-ac",
            "--subsection", "behavior_change",
            "--ears-variant", "event_driven",
            "--statement", "WHEN a user logs in, the system shall emit an audit event.",
            "--finding-ref", fid1,
            "--finding-ref", fid2,
        ])
        rc = _run("verify-coverage", devforge_dir=self.devforge_dir)
        self.assertEqual(rc, 0)

    def test_add_ac_unknown_finding_ref_exits_nonzero(self):
        rc, stderr = _run_capture_stderr(
            "add-ac",
            "--subsection", "behavior_change",
            "--ears-variant", "event_driven",
            "--statement", "WHEN a user logs in, the system shall emit an audit event.",
            "--finding-ref", "F-does-not-exist-99",
            devforge_dir=self.devforge_dir,
        )
        self.assertEqual(rc, 2)
        self.assertIn("F-does-not-exist-99", stderr)

    def test_add_ac_unknown_finding_ref_does_not_add_ac(self):
        _run_capture_stderr(
            "add-ac",
            "--subsection", "behavior_change",
            "--ears-variant", "event_driven",
            "--statement", "WHEN a user logs in, the system shall emit an audit event.",
            "--finding-ref", "F-ghost-1",
            devforge_dir=self.devforge_dir,
        )
        state = _load(self.devforge_dir)
        self.assertEqual(len(state["acceptance_criteria"]), 0)

    def test_add_ac_mixed_valid_and_ghost_ref_exits_2_no_partial_write(self):
        """Mixed valid + ghost finding-ref: exit 2, AC not appended, valid finding stays unlanded."""
        fid_valid = _record_finding(
            self.devforge_dir, content="Valid finding for mixed-ref test",
        )
        rc, stderr = _run_capture_stderr(
            "add-ac",
            "--subsection", "behavior_change",
            "--ears-variant", "event_driven",
            "--statement", "WHEN a user logs in, the system shall emit an audit event.",
            "--finding-ref", fid_valid,
            "--finding-ref", "F-ghost-999",
            devforge_dir=self.devforge_dir,
        )
        self.assertEqual(rc, 2)
        self.assertIn("F-ghost-999", stderr)
        state = _load(self.devforge_dir)
        # No AC was appended
        self.assertEqual(len(state["acceptance_criteria"]), 0)
        # The valid finding was NOT partially landed
        f = _finding_by_id(state, fid_valid)
        self.assertIsNotNone(f)
        self.assertEqual(f["landed_in"], "unlanded")


# ---------------------------------------------------------------------------
# Constraint landing tests
# ---------------------------------------------------------------------------


class TestRecordConstraintLanding(_TmpDirMixin):
    def test_constraint_with_finding_ref_flips_landed_in(self):
        fid = _record_finding(self.devforge_dir)
        rc = _run(
            "record-constraint",
            "--kind", "follow",
            "--content", "Must follow the existing pattern",
            "--finding-ref", fid,
            devforge_dir=self.devforge_dir,
        )
        self.assertEqual(rc, 0)
        state = _load(self.devforge_dir)
        f = _finding_by_id(state, fid)
        self.assertEqual(f["landed_in"], "Constraint")
        self.assertEqual(f["landed_ref"], "Constraint-1")

    def test_constraint_with_finding_ref_verify_coverage_passes(self):
        fid = _record_finding(self.devforge_dir)
        _run(
            "record-constraint",
            "--kind", "follow",
            "--content", "Must follow the existing pattern",
            "--finding-ref", fid,
            devforge_dir=self.devforge_dir,
        )
        rc = _run("verify-coverage", devforge_dir=self.devforge_dir)
        self.assertEqual(rc, 0)

    def test_constraint_ref_label_increments_with_position(self):
        fid1 = _record_finding(
            self.devforge_dir, content="Constraint finding one",
        )
        fid2 = _record_finding(
            self.devforge_dir, content="Constraint finding two",
        )
        # First constraint lands fid1 → Constraint-1
        _run(
            "record-constraint",
            "--kind", "follow",
            "--content", "First constraint",
            "--finding-ref", fid1,
            devforge_dir=self.devforge_dir,
        )
        # Second constraint (no ref) just appended
        _run(
            "record-constraint",
            "--kind", "not_break",
            "--content", "Second constraint no ref",
            devforge_dir=self.devforge_dir,
        )
        # Third constraint lands fid2 → Constraint-3
        _run(
            "record-constraint",
            "--kind", "follow",
            "--content", "Third constraint",
            "--finding-ref", fid2,
            devforge_dir=self.devforge_dir,
        )
        state = _load(self.devforge_dir)
        f1 = _finding_by_id(state, fid1)
        f2 = _finding_by_id(state, fid2)
        self.assertEqual(f1["landed_ref"], "Constraint-1")
        self.assertEqual(f2["landed_ref"], "Constraint-3")

    def test_constraint_multi_ref_lands_both(self):
        fid1 = _record_finding(
            self.devforge_dir, content="Constraint multi-ref one",
        )
        fid2 = _record_finding(
            self.devforge_dir, content="Constraint multi-ref two",
        )
        rc = _run(
            "record-constraint",
            "--kind", "follow",
            "--content", "Constraint landing two findings",
            "--finding-ref", fid1,
            "--finding-ref", fid2,
            devforge_dir=self.devforge_dir,
        )
        self.assertEqual(rc, 0)
        state = _load(self.devforge_dir)
        f1 = _finding_by_id(state, fid1)
        f2 = _finding_by_id(state, fid2)
        self.assertEqual(f1["landed_in"], "Constraint")
        self.assertEqual(f2["landed_in"], "Constraint")

    def test_constraint_unknown_finding_ref_exits_nonzero(self):
        rc, stderr = _run_capture_stderr(
            "record-constraint",
            "--kind", "follow",
            "--content", "Does not matter",
            "--finding-ref", "F-unknown-99",
            devforge_dir=self.devforge_dir,
        )
        self.assertEqual(rc, 2)
        self.assertIn("F-unknown-99", stderr)

    def test_constraint_unknown_ref_does_not_append(self):
        _run_capture_stderr(
            "record-constraint",
            "--kind", "follow",
            "--content", "Should not be stored",
            "--finding-ref", "F-ghost-1",
            devforge_dir=self.devforge_dir,
        )
        state = _load(self.devforge_dir)
        self.assertEqual(len(state["constraints"]), 0)

    def test_constraint_mixed_valid_and_ghost_ref_exits_2_no_partial_write(self):
        """Mixed valid + ghost finding-ref: exit 2, constraint not appended, valid finding stays unlanded."""
        fid_valid = _record_finding(
            self.devforge_dir, content="Valid finding for constraint mixed-ref test",
        )
        rc, stderr = _run_capture_stderr(
            "record-constraint",
            "--kind", "follow",
            "--content", "Constraint that should not be stored",
            "--finding-ref", fid_valid,
            "--finding-ref", "F-ghost-999",
            devforge_dir=self.devforge_dir,
        )
        self.assertEqual(rc, 2)
        self.assertIn("F-ghost-999", stderr)
        state = _load(self.devforge_dir)
        # No constraint was appended
        self.assertEqual(len(state["constraints"]), 0)
        # The valid finding was NOT partially landed
        f = _finding_by_id(state, fid_valid)
        self.assertIsNotNone(f)
        self.assertEqual(f["landed_in"], "unlanded")


# ---------------------------------------------------------------------------
# OOS landing tests (the OOS was already storing finding_ref but NOT flipping)
# ---------------------------------------------------------------------------


class TestRecordOutOfScopeLanding(_TmpDirMixin):
    def test_oos_with_finding_ref_flips_landed_in(self):
        fid = _record_finding(self.devforge_dir)
        rc = _run(
            "record-out-of-scope",
            "--content", "Real-time streaming is out of scope",
            "--finding-ref", fid,
            devforge_dir=self.devforge_dir,
        )
        self.assertEqual(rc, 0)
        state = _load(self.devforge_dir)
        f = _finding_by_id(state, fid)
        self.assertEqual(f["landed_in"], "OOS")
        self.assertEqual(f["landed_ref"], "OOS-1")

    def test_oos_still_stores_finding_ref_on_entry(self):
        """OOS entry retains the finding_ref field (existing behaviour)."""
        fid = _record_finding(self.devforge_dir)
        _run(
            "record-out-of-scope",
            "--content", "Real-time streaming is out of scope",
            "--finding-ref", fid,
            devforge_dir=self.devforge_dir,
        )
        state = _load(self.devforge_dir)
        self.assertEqual(state["out_of_scope"][0]["finding_ref"], fid)

    def test_oos_with_finding_ref_verify_coverage_passes(self):
        fid = _record_finding(self.devforge_dir)
        _run(
            "record-out-of-scope",
            "--content", "Real-time streaming is out of scope",
            "--finding-ref", fid,
            devforge_dir=self.devforge_dir,
        )
        rc = _run("verify-coverage", devforge_dir=self.devforge_dir)
        self.assertEqual(rc, 0)

    def test_oos_without_finding_ref_does_not_flip(self):
        fid = _record_finding(self.devforge_dir)
        _run(
            "record-out-of-scope",
            "--content", "Something unrelated is out of scope",
            devforge_dir=self.devforge_dir,
        )
        state = _load(self.devforge_dir)
        f = _finding_by_id(state, fid)
        self.assertEqual(f["landed_in"], "unlanded")

    def test_oos_unknown_finding_ref_exits_nonzero(self):
        rc, stderr = _run_capture_stderr(
            "record-out-of-scope",
            "--content", "Something",
            "--finding-ref", "F-ghost-77",
            devforge_dir=self.devforge_dir,
        )
        self.assertEqual(rc, 2)
        self.assertIn("F-ghost-77", stderr)

    def test_oos_unknown_ref_does_not_append(self):
        _run_capture_stderr(
            "record-out-of-scope",
            "--content", "Should not be stored",
            "--finding-ref", "F-ghost-1",
            devforge_dir=self.devforge_dir,
        )
        state = _load(self.devforge_dir)
        self.assertEqual(len(state["out_of_scope"]), 0)

    def test_oos_ref_label_tracks_position(self):
        fid1 = _record_finding(
            self.devforge_dir, content="OOS finding one",
        )
        fid2 = _record_finding(
            self.devforge_dir, content="OOS finding two",
        )
        # Append two OOS entries without refs, then a third with ref
        _run(
            "record-out-of-scope",
            "--content", "No-ref entry one",
            devforge_dir=self.devforge_dir,
        )
        _run(
            "record-out-of-scope",
            "--content", "No-ref entry two",
            devforge_dir=self.devforge_dir,
        )
        _run(
            "record-out-of-scope",
            "--content", "Ref entry",
            "--finding-ref", fid1,
            devforge_dir=self.devforge_dir,
        )
        state = _load(self.devforge_dir)
        f1 = _finding_by_id(state, fid1)
        self.assertEqual(f1["landed_ref"], "OOS-3")


# ---------------------------------------------------------------------------
# Risk landing tests
# ---------------------------------------------------------------------------


class TestRecordRiskLanding(_TmpDirMixin):
    def test_risk_with_finding_ref_flips_landed_in(self):
        fid = _record_finding(self.devforge_dir)
        rc = _run(
            "record-risk",
            "--risk", "Deployment delay",
            "--likelihood", "Med",
            "--impact", "High",
            "--mitigation", "Add feature flag",
            "--finding-ref", fid,
            devforge_dir=self.devforge_dir,
        )
        self.assertEqual(rc, 0)
        state = _load(self.devforge_dir)
        f = _finding_by_id(state, fid)
        self.assertEqual(f["landed_in"], "Risk")
        self.assertEqual(f["landed_ref"], "Risk-1")

    def test_risk_with_finding_ref_verify_coverage_passes(self):
        fid = _record_finding(self.devforge_dir)
        _run(
            "record-risk",
            "--risk", "Deployment delay",
            "--likelihood", "Med",
            "--impact", "High",
            "--mitigation", "Add feature flag",
            "--finding-ref", fid,
            devforge_dir=self.devforge_dir,
        )
        rc = _run("verify-coverage", devforge_dir=self.devforge_dir)
        self.assertEqual(rc, 0)

    def test_risk_multi_ref_lands_both(self):
        fid1 = _record_finding(
            self.devforge_dir, content="Risk multi-ref one",
        )
        fid2 = _record_finding(
            self.devforge_dir, content="Risk multi-ref two",
        )
        _run(
            "record-risk",
            "--risk", "Shared risk",
            "--likelihood", "Low",
            "--impact", "Med",
            "--mitigation", "Monitor",
            "--finding-ref", fid1,
            "--finding-ref", fid2,
            devforge_dir=self.devforge_dir,
        )
        state = _load(self.devforge_dir)
        f1 = _finding_by_id(state, fid1)
        f2 = _finding_by_id(state, fid2)
        self.assertEqual(f1["landed_in"], "Risk")
        self.assertEqual(f2["landed_in"], "Risk")

    def test_risk_unknown_finding_ref_exits_nonzero(self):
        rc, stderr = _run_capture_stderr(
            "record-risk",
            "--risk", "Some risk",
            "--likelihood", "Low",
            "--impact", "Low",
            "--mitigation", "None",
            "--finding-ref", "F-ghost-55",
            devforge_dir=self.devforge_dir,
        )
        self.assertEqual(rc, 2)
        self.assertIn("F-ghost-55", stderr)

    def test_risk_unknown_ref_does_not_append(self):
        _run_capture_stderr(
            "record-risk",
            "--risk", "Should not be stored",
            "--likelihood", "Low",
            "--impact", "Low",
            "--mitigation", "None",
            "--finding-ref", "F-ghost-1",
            devforge_dir=self.devforge_dir,
        )
        state = _load(self.devforge_dir)
        self.assertEqual(len(state["risks"]), 0)

    def test_risk_mixed_valid_and_ghost_ref_exits_2_no_partial_write(self):
        """Mixed valid + ghost finding-ref: exit 2, risk not appended, valid finding stays unlanded."""
        fid_valid = _record_finding(
            self.devforge_dir, content="Valid finding for risk mixed-ref test",
        )
        rc, stderr = _run_capture_stderr(
            "record-risk",
            "--risk", "Risk that should not be stored",
            "--likelihood", "Low",
            "--impact", "Low",
            "--mitigation", "None",
            "--finding-ref", fid_valid,
            "--finding-ref", "F-ghost-999",
            devforge_dir=self.devforge_dir,
        )
        self.assertEqual(rc, 2)
        self.assertIn("F-ghost-999", stderr)
        state = _load(self.devforge_dir)
        # No risk was appended
        self.assertEqual(len(state["risks"]), 0)
        # The valid finding was NOT partially landed
        f = _finding_by_id(state, fid_valid)
        self.assertIsNotNone(f)
        self.assertEqual(f["landed_in"], "unlanded")


# ---------------------------------------------------------------------------
# set-finding-landed standalone tests
# ---------------------------------------------------------------------------


class TestSetFindingLanded(_TmpDirMixin):
    def test_standalone_flip_flips_landed_in(self):
        fid = _record_finding(self.devforge_dir)
        rc = _run(
            "set-finding-landed",
            "--finding-id", fid,
            "--landed-in", "AC",
            "--landed-ref", "AC-1",
            devforge_dir=self.devforge_dir,
        )
        self.assertEqual(rc, 0)
        state = _load(self.devforge_dir)
        f = _finding_by_id(state, fid)
        self.assertEqual(f["landed_in"], "AC")
        self.assertEqual(f["landed_ref"], "AC-1")

    def test_standalone_flip_verify_coverage_passes(self):
        fid = _record_finding(self.devforge_dir)
        _run(
            "set-finding-landed",
            "--finding-id", fid,
            "--landed-in", "OOS",
            devforge_dir=self.devforge_dir,
        )
        rc = _run("verify-coverage", devforge_dir=self.devforge_dir)
        self.assertEqual(rc, 0)

    def test_standalone_flip_without_landed_ref_sets_empty(self):
        fid = _record_finding(self.devforge_dir)
        _run(
            "set-finding-landed",
            "--finding-id", fid,
            "--landed-in", "Risk",
            devforge_dir=self.devforge_dir,
        )
        state = _load(self.devforge_dir)
        f = _finding_by_id(state, fid)
        self.assertEqual(f["landed_ref"], "")

    def test_standalone_unknown_finding_id_exits_nonzero(self):
        rc, stderr = _run_capture_stderr(
            "set-finding-landed",
            "--finding-id", "F-ghost-999",
            "--landed-in", "AC",
            devforge_dir=self.devforge_dir,
        )
        self.assertEqual(rc, 2)
        self.assertIn("F-ghost-999", stderr)

    def test_standalone_unlanded_rejected(self):
        """--landed-in unlanded must fail (argparse choices rejects it)."""
        fid = _record_finding(self.devforge_dir)
        # argparse will call sys.exit(2) for invalid choice — catch SystemExit
        buf = io.StringIO()
        old_err = sys.stderr
        sys.stderr = buf
        try:
            with self.assertRaises(SystemExit) as cm:
                main([
                    "--devforge-dir", self.devforge_dir,
                    "set-finding-landed",
                    "--finding-id", fid,
                    "--landed-in", "unlanded",
                ])
        finally:
            sys.stderr = old_err
        self.assertEqual(cm.exception.code, 2)

    def test_standalone_all_buckets_accepted(self):
        for bucket in ("AC", "Constraint", "OOS", "Risk"):
            with self.subTest(bucket=bucket):
                # Fresh state per bucket
                _reset(self.devforge_dir)
                fid = _record_finding(self.devforge_dir, content=bucket)
                rc = _run(
                    "set-finding-landed",
                    "--finding-id", fid,
                    "--landed-in", bucket,
                    devforge_dir=self.devforge_dir,
                )
                self.assertEqual(rc, 0)
                state = _load(self.devforge_dir)
                f = _finding_by_id(state, fid)
                self.assertEqual(f["landed_in"], bucket)


# ---------------------------------------------------------------------------
# Idempotency + re-land tests
# ---------------------------------------------------------------------------


class TestLandingIdempotencyAndReland(_TmpDirMixin):
    def test_same_bucket_reland_is_success(self):
        """Re-landing to the same bucket succeeds (no-op on values, exit 0)."""
        fid = _record_finding(self.devforge_dir)
        _run(
            "set-finding-landed",
            "--finding-id", fid,
            "--landed-in", "AC",
            "--landed-ref", "AC-1",
            devforge_dir=self.devforge_dir,
        )
        rc = _run(
            "set-finding-landed",
            "--finding-id", fid,
            "--landed-in", "AC",
            "--landed-ref", "AC-1",
            devforge_dir=self.devforge_dir,
        )
        self.assertEqual(rc, 0)
        state = _load(self.devforge_dir)
        f = _finding_by_id(state, fid)
        self.assertEqual(f["landed_in"], "AC")

    def test_different_bucket_reland_overwrites(self):
        """Re-landing to a different bucket succeeds and overwrites."""
        fid = _record_finding(self.devforge_dir)
        _run(
            "set-finding-landed",
            "--finding-id", fid,
            "--landed-in", "AC",
            "--landed-ref", "AC-1",
            devforge_dir=self.devforge_dir,
        )
        rc = _run(
            "set-finding-landed",
            "--finding-id", fid,
            "--landed-in", "Risk",
            "--landed-ref", "Risk-1",
            devforge_dir=self.devforge_dir,
        )
        self.assertEqual(rc, 0)
        state = _load(self.devforge_dir)
        f = _finding_by_id(state, fid)
        self.assertEqual(f["landed_in"], "Risk")
        self.assertEqual(f["landed_ref"], "Risk-1")

    def test_setter_reland_via_different_setter_overwrites(self):
        """Landing via AC setter then re-landing via OOS setter overwrites."""
        fid = _record_finding(self.devforge_dir)
        # Land via AC
        main([
            "--devforge-dir", self.devforge_dir,
            "add-ac",
            "--subsection", "behavior_change",
            "--ears-variant", "event_driven",
            "--statement", "WHEN a user logs in, the system shall emit an audit event.",
            "--finding-ref", fid,
        ])
        state = _load(self.devforge_dir)
        f = _finding_by_id(state, fid)
        self.assertEqual(f["landed_in"], "AC")
        # Re-land via OOS
        _run(
            "record-out-of-scope",
            "--content", "Now out of scope",
            "--finding-ref", fid,
            devforge_dir=self.devforge_dir,
        )
        state = _load(self.devforge_dir)
        f = _finding_by_id(state, fid)
        self.assertEqual(f["landed_in"], "OOS")


# ---------------------------------------------------------------------------
# Full phase-1.5 → verify-coverage round-trip (all four buckets)
# ---------------------------------------------------------------------------


class TestFullRoundTrip(_TmpDirMixin):
    """Each test records a finding, lands it via the real setter, and asserts
    verify-coverage exits 0. These are the definitive "real-producer" tests."""

    def test_ac_round_trip(self):
        fid = _record_finding(self.devforge_dir, content="AC round trip finding")
        main([
            "--devforge-dir", self.devforge_dir,
            "add-ac",
            "--subsection", "behavior_change",
            "--ears-variant", "event_driven",
            "--statement", "WHEN a request arrives, the system shall process it.",
            "--finding-ref", fid,
        ])
        rc = _run("verify-coverage", devforge_dir=self.devforge_dir)
        self.assertEqual(rc, 0)

    def test_constraint_round_trip(self):
        fid = _record_finding(self.devforge_dir, content="Constraint round trip finding")
        _run(
            "record-constraint",
            "--kind", "not_break",
            "--content", "Must not break existing API",
            "--finding-ref", fid,
            devforge_dir=self.devforge_dir,
        )
        rc = _run("verify-coverage", devforge_dir=self.devforge_dir)
        self.assertEqual(rc, 0)

    def test_oos_round_trip(self):
        fid = _record_finding(self.devforge_dir, content="OOS round trip finding")
        _run(
            "record-out-of-scope",
            "--content", "Mobile push notifications",
            "--finding-ref", fid,
            devforge_dir=self.devforge_dir,
        )
        rc = _run("verify-coverage", devforge_dir=self.devforge_dir)
        self.assertEqual(rc, 0)

    def test_risk_round_trip(self):
        fid = _record_finding(self.devforge_dir, content="Risk round trip finding")
        _run(
            "record-risk",
            "--risk", "Performance regression",
            "--likelihood", "Low",
            "--impact", "High",
            "--mitigation", "Load test before merge",
            "--finding-ref", fid,
            devforge_dir=self.devforge_dir,
        )
        rc = _run("verify-coverage", devforge_dir=self.devforge_dir)
        self.assertEqual(rc, 0)

    def test_set_finding_landed_round_trip(self):
        fid = _record_finding(self.devforge_dir, content="Direct set round trip")
        _run(
            "set-finding-landed",
            "--finding-id", fid,
            "--landed-in", "Constraint",
            "--landed-ref", "Constraint-1",
            devforge_dir=self.devforge_dir,
        )
        rc = _run("verify-coverage", devforge_dir=self.devforge_dir)
        self.assertEqual(rc, 0)

    def test_mixed_buckets_all_pass(self):
        """Four findings, each landed in a different bucket, all pass coverage."""
        fid_ac = _record_finding(
            self.devforge_dir, content="Goes to AC",
        )
        fid_constraint = _record_finding(
            self.devforge_dir, content="Goes to Constraint",
        )
        fid_oos = _record_finding(
            self.devforge_dir, content="Goes to OOS",
        )
        fid_risk = _record_finding(
            self.devforge_dir, content="Goes to Risk",
        )

        main([
            "--devforge-dir", self.devforge_dir,
            "add-ac",
            "--subsection", "behavior_change",
            "--ears-variant", "event_driven",
            "--statement", "WHEN a request arrives, the system shall process it.",
            "--finding-ref", fid_ac,
        ])
        _run(
            "record-constraint",
            "--kind", "follow",
            "--content", "Must follow REST conventions",
            "--finding-ref", fid_constraint,
            devforge_dir=self.devforge_dir,
        )
        _run(
            "record-out-of-scope",
            "--content", "Mobile notifications",
            "--finding-ref", fid_oos,
            devforge_dir=self.devforge_dir,
        )
        _run(
            "record-risk",
            "--risk", "Latency increase",
            "--likelihood", "Low",
            "--impact", "Med",
            "--mitigation", "Load test",
            "--finding-ref", fid_risk,
            devforge_dir=self.devforge_dir,
        )

        rc = _run("verify-coverage", devforge_dir=self.devforge_dir)
        self.assertEqual(rc, 0)

    def test_verify_coverage_fails_without_any_landing(self):
        """Control: unlanded finding still fails verify-coverage."""
        _record_finding(self.devforge_dir, content="Unlanded finding")
        rc = _run("verify-coverage", devforge_dir=self.devforge_dir)
        self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()
