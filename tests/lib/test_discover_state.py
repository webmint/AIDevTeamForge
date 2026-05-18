"""Tests for src/devforge/lib/_discover/_state.py — defaults + IO + transactions.

Carved out of tests/lib/test_discover_helper.py during Phase A1 of
REFACTOR-MONOLITHIC-HELPERS-PLAN. Covers:

  Schemas
    default_memo_state    — 8 dimensions present, all Missing state,
                            empty references/gaps/conflicts.
    default_report_state  — all 18+ keys present at defaults.

  Subcommand round-trip
    reset-memo + reset-report — write JSON; idempotent.
    read-memo + read-report   — defaults when missing; round-trip after reset.

  Atomicity
    _state_transaction body raise → state file unchanged; no .json.tmp debris.

Subprocess pattern: each test runs in its own tempfile.TemporaryDirectory.
Stdlib only. Python 3.8+.
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"
_HELPER_PY = _LIB_DIR / "discover_helper.py"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _discover._state import (  # noqa: E402
    MEMO_FILE_NAME,
    REPORT_FILE_NAME,
    RUBRIC_DIMENSIONS,
    _state_transaction,
    default_memo_state,
    default_report_state,
)


def _run(argv, cwd=None):
    """Run discover_helper.py with argv; capture stdout/stderr/exit."""
    return subprocess.run(
        [sys.executable, str(_HELPER_PY)] + list(argv),
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        check=False,
    )


# ---------------------------------------------------------------------------
# Schema defaults.
# ---------------------------------------------------------------------------


class TestDefaultMemoState(unittest.TestCase):
    def test_eight_dimensions_present(self):
        memo = default_memo_state()
        dims = memo["dimensions"]
        self.assertEqual(set(dims.keys()), set(RUBRIC_DIMENSIONS))
        self.assertEqual(len(dims), 8)

    def test_all_dimensions_missing_state(self):
        memo = default_memo_state()
        for d in RUBRIC_DIMENSIONS:
            rec = memo["dimensions"][d]
            self.assertIsNone(rec["value"], "dimension {0} value".format(d))
            self.assertEqual(rec["state"], "Missing", "dimension {0} state".format(d))
            self.assertEqual(rec["turns"], 0, "dimension {0} turns".format(d))

    def test_empty_lists(self):
        memo = default_memo_state()
        self.assertEqual(memo["references"], [])
        self.assertEqual(memo["gaps"], [])
        self.assertEqual(memo["conflicts"], [])

    def test_scalars_none(self):
        memo = default_memo_state()
        self.assertIsNone(memo["topic"])
        self.assertIsNone(memo["topic_slug"])
        self.assertIsNone(memo["date"])
        self.assertFalse(memo["override_recorded"])

    def test_rubric_dimensions_locked_order(self):
        self.assertEqual(
            RUBRIC_DIMENSIONS,
            (
                "functional_scope",
                "users",
                "inputs_outputs",
                "integration_points",
                "constraints",
                "non_goals",
                "success_criteria",
                "edge_cases",
            ),
        )


class TestDefaultReportState(unittest.TestCase):
    _REQUIRED_KEYS = (
        "topic",
        "date",
        "topic_slug",
        "summary",
        "prior_art",
        "integration_touchpoints",
        "fit_assessments",
        "overall_fit",
        "effort_estimate",
        "fit_rationale",
        "design_options",
        "recommended_option",
        "build_vs_buy",
        "derisk_plan",
        "constitution_constraints",
        "verdict",
        "recommendation",
        "next_step_text",
        "open_uncertainties",
    )

    def test_all_keys_present(self):
        rep = default_report_state()
        for key in self._REQUIRED_KEYS:
            self.assertIn(key, rep, "key missing: {0}".format(key))

    def test_count_at_least_18(self):
        rep = default_report_state()
        # Schema has 19 keys; guard against future accidental deletions.
        self.assertGreaterEqual(len(rep), 18)

    def test_none_scalars(self):
        rep = default_report_state()
        for key in (
            "topic", "date", "topic_slug", "summary",
            "overall_fit", "effort_estimate", "fit_rationale",
            "recommended_option", "build_vs_buy",
            "verdict", "recommendation", "next_step_text",
        ):
            self.assertIsNone(rep[key], "key {0} should default None".format(key))

    def test_empty_lists(self):
        rep = default_report_state()
        for key in (
            "prior_art", "integration_touchpoints", "fit_assessments",
            "design_options", "derisk_plan", "constitution_constraints",
            "open_uncertainties",
        ):
            self.assertEqual(rep[key], [], "key {0} should default []".format(key))


# ---------------------------------------------------------------------------
# reset-memo subcommand.
# ---------------------------------------------------------------------------


class TestResetMemo(unittest.TestCase):
    def test_file_created(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = _run(["--devforge-dir", str(devforge), "reset-memo"])
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue((devforge / MEMO_FILE_NAME).exists())

    def test_file_matches_default_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = _run(["--devforge-dir", str(devforge), "reset-memo"])
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads(
                (devforge / MEMO_FILE_NAME).read_text(encoding="utf-8")
            )
            self.assertEqual(data, default_memo_state())

    def test_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run(["--devforge-dir", str(devforge), "reset-memo"])
            first = (devforge / MEMO_FILE_NAME).read_bytes()
            _run(["--devforge-dir", str(devforge), "reset-memo"])
            second = (devforge / MEMO_FILE_NAME).read_bytes()
            self.assertEqual(first, second)


# ---------------------------------------------------------------------------
# reset-report subcommand.
# ---------------------------------------------------------------------------


class TestResetReport(unittest.TestCase):
    def test_file_created(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = _run(["--devforge-dir", str(devforge), "reset-report"])
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue((devforge / REPORT_FILE_NAME).exists())

    def test_file_matches_default_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = _run(["--devforge-dir", str(devforge), "reset-report"])
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads(
                (devforge / REPORT_FILE_NAME).read_text(encoding="utf-8")
            )
            self.assertEqual(data, default_report_state())

    def test_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run(["--devforge-dir", str(devforge), "reset-report"])
            first = (devforge / REPORT_FILE_NAME).read_bytes()
            _run(["--devforge-dir", str(devforge), "reset-report"])
            second = (devforge / REPORT_FILE_NAME).read_bytes()
            self.assertEqual(first, second)


# ---------------------------------------------------------------------------
# read-memo / read-report subcommands.
# ---------------------------------------------------------------------------


class TestReadMemo(unittest.TestCase):
    def test_defaults_when_file_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = _run(["--devforge-dir", str(devforge), "read-memo"])
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads(r.stdout)
            self.assertEqual(data, default_memo_state())

    def test_round_trip_after_reset(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run(["--devforge-dir", str(devforge), "reset-memo"])
            r = _run(["--devforge-dir", str(devforge), "read-memo"])
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads(r.stdout)
            self.assertEqual(data, default_memo_state())

    def test_stdout_is_valid_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = _run(["--devforge-dir", str(devforge), "read-memo"])
            self.assertEqual(r.returncode, 0)
            parsed = json.loads(r.stdout)
            self.assertIsInstance(parsed, dict)


class TestReadReport(unittest.TestCase):
    def test_defaults_when_file_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = _run(["--devforge-dir", str(devforge), "read-report"])
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads(r.stdout)
            self.assertEqual(data, default_report_state())

    def test_round_trip_after_reset(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run(["--devforge-dir", str(devforge), "reset-report"])
            r = _run(["--devforge-dir", str(devforge), "read-report"])
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads(r.stdout)
            self.assertEqual(data, default_report_state())

    def test_stdout_is_valid_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = _run(["--devforge-dir", str(devforge), "read-report"])
            self.assertEqual(r.returncode, 0)
            parsed = json.loads(r.stdout)
            self.assertIsInstance(parsed, dict)


# ---------------------------------------------------------------------------
# Atomicity — direct _state_transaction invocation.
# ---------------------------------------------------------------------------


class TestAtomicity(unittest.TestCase):
    def test_body_raise_leaves_state_unchanged(self):
        """A transaction body that raises must not corrupt the state file."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            devforge.mkdir()
            # Establish baseline state via reset-memo.
            _run(["--devforge-dir", str(devforge), "reset-memo"])
            baseline = json.loads(
                (devforge / MEMO_FILE_NAME).read_text(encoding="utf-8")
            )
            # Directly call _state_transaction with a body that raises.
            try:
                with _state_transaction(devforge, "memo") as memo:
                    memo["topic"] = "SHOULD NOT PERSIST"
                    raise RuntimeError("deliberate failure")
            except RuntimeError:
                pass
            after = json.loads(
                (devforge / MEMO_FILE_NAME).read_text(encoding="utf-8")
            )
            self.assertEqual(after, baseline)

    def test_no_tmp_file_debris_after_raise(self):
        """A failed transaction must clean up its .json.tmp file."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            devforge.mkdir()
            _run(["--devforge-dir", str(devforge), "reset-memo"])
            try:
                with _state_transaction(devforge, "memo") as memo:
                    memo["topic"] = "about to fail"
                    raise RuntimeError("deliberate failure")
            except RuntimeError:
                pass
            tmp_files = list(devforge.glob("*.json.tmp"))
            self.assertEqual(tmp_files, [], "leftover .json.tmp files: {0}".format(tmp_files))

    def test_successful_transaction_writes_file(self):
        """A successful transaction must persist the mutated state."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            devforge.mkdir()
            _run(["--devforge-dir", str(devforge), "reset-memo"])
            with _state_transaction(devforge, "memo") as memo:
                memo["topic"] = "Persisted topic"
            after = json.loads(
                (devforge / MEMO_FILE_NAME).read_text(encoding="utf-8")
            )
            self.assertEqual(after["topic"], "Persisted topic")

    def test_no_tmp_file_debris_after_success(self):
        """A successful transaction must leave no .json.tmp files behind."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            devforge.mkdir()
            _run(["--devforge-dir", str(devforge), "reset-memo"])
            with _state_transaction(devforge, "memo") as memo:
                memo["topic"] = "clean write"
            tmp_files = list(devforge.glob("*.json.tmp"))
            self.assertEqual(tmp_files, [], "leftover .json.tmp files: {0}".format(tmp_files))


if __name__ == "__main__":
    unittest.main()
