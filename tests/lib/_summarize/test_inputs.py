"""Tests for src/devforge/lib/_summarize/_inputs.py.

Real-producer round-trip discipline:
  - read_verification: round-trips against a REAL verify_helper render_report
    output, produced by calling the real _verify._report.render_report with
    real producer inputs (real merge_ac_results, real compute_verdict, etc.).
    NOT a hand-authored verification.md.

  - parse_completion_notes: round-trips against a REAL implement_helper
    mark-complete-filled task file, produced by calling the real
    _cmds_complete._fill_completion_notes on a skeleton task file.
    NOT a hand-authored Completion Notes section.

  - read_plan_decisions: round-trips against:
    (a) the REAL plan_handoff_fixture.md (tests/lib/fixtures/plan_handoff_fixture.md)
        which uses "### Key Design Decisions" (shape A — current /plan template).
    (b) the REAL 008-sample-feature/plan.md fixture which uses
        "## Architecture Decisions" (shape B — older plans).
    Both round-trips assert the parsed decisions match the fixture content.

  - D9 verification: read_plan_decisions reads plan.md paths only — the test
    confirms _inputs.py imports NO plan-handoff.json references.

Coverage:
  read_verification:
    - APPROVED verdict + 3 ACs (PASS / PARTIAL / UNVERIFIED)
    - NEEDS WORK verdict
    - REJECTED verdict
    - empty ac_results produces no AC rows
    - evidence with escaped pipes (\\|) is unescaped
    - file not found → error string returned
    - verdict not found → verdict == ""
    - AC table header row is not included in ac_list

  parse_completion_notes:
    - files_changed parsed from real mark-complete output (comma-separated)
    - expects_met / produces_met parsed correctly
    - notes parsed; "(none)" becomes ""
    - has_unverified False when no unverified boxes
    - has_unverified True when a Done-When box carries the unverified annotation
    - has_notes False when section is absent
    - multiple files in files_changed list

  read_plan_decisions:
    - shape A fixture: "### Key Design Decisions" → correct decisions list
    - shape B fixture: "## Architecture Decisions" → correct decisions list
    - no-decisions heading → empty list, no error
    - file not found → error string returned

  cmd_read_verification / cmd_parse_completion_notes / cmd_read_plan_decisions:
    - missing --path exits 2
    - happy path emits valid JSON (one test each)
"""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"
_FIXTURES_DIR = _REPO_ROOT / "tests" / "lib" / "fixtures"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

# Parsers under test
from _summarize._inputs import (  # noqa: E402
    read_verification,
    parse_completion_notes,
    read_plan_decisions,
    cmd_read_verification,
    cmd_parse_completion_notes,
    cmd_read_plan_decisions,
)

# ---------------------------------------------------------------------------
# Real producers used to create test fixtures
# ---------------------------------------------------------------------------

# _verify._report.render_report — the verification.md producer.
from _verify._report import render_report as _render_verify_report  # noqa: E402
from _verify._ac import merge_ac_results  # noqa: E402
from _verify._verdict import compute_verdict  # noqa: E402

# _implement._cmds_complete — the Completion Notes producer.
from _implement._cmds_complete import _fill_completion_notes  # noqa: E402


# ---------------------------------------------------------------------------
# Real fixture paths
# ---------------------------------------------------------------------------

_PLAN_FIXTURE_SHAPE_A = str(
    _FIXTURES_DIR / "plan_handoff_fixture.md"
)  # "### Key Design Decisions" (current /plan template)

_PLAN_FIXTURE_SHAPE_B = str(
    _FIXTURES_DIR / "specs" / "008-sample-feature" / "plan.md"
)  # "## Architecture Decisions" (older plans)


# ---------------------------------------------------------------------------
# Helpers: produce real verification.md content
# ---------------------------------------------------------------------------


def _ac_result(ac_id, status, evidence="See code review"):
    # type: (str, str, str) -> Dict
    """Build a minimal ac_result dict as merge_ac_results would produce."""
    return {"id": ac_id, "status": status, "evidence": evidence}


def _make_review_findings(missing=True, confirmed_count=0, contested_count=0):
    # type: (bool, int, int) -> Dict
    """Build a minimal review_findings dict as read_review_findings would produce."""
    if missing:
        return {"missing": True, "confirmed": [], "contested": [], "summary": {}}
    return {
        "missing": False,
        "confirmed": [],
        "contested": [],
        "summary": {
            "confirmed_count": confirmed_count,
            "contested_count": contested_count,
            "dismissed_count": 0,
            "uncertain_count": 0,
            "critical": 0, "high": 0, "medium": 0, "info": 0,
        },
    }


def _make_hygiene():
    # type: () -> Dict
    return {
        "scope_creep": [],
        "leftover_artifacts": [],
        "scope_creep_checked": False,
    }


def _render_real_verification(
    verdict_str="APPROVED",
    ac_results=None,
    feature="specs/001-test",
    date_str="2026-06-17",
):
    # type: (str, Optional[List[Dict]], str, str) -> str
    """Produce a REAL verification.md string via the actual render_report producer."""
    if ac_results is None:
        ac_results = [
            _ac_result("AC-1", "PASS", "All unit tests pass"),
            _ac_result("AC-2", "PARTIAL", "Manual step pending"),
            _ac_result("AC-3", "UNVERIFIED", ""),
        ]
    verdict = {
        "verdict": verdict_str,
        "reasons": ["All ACs satisfied"] if verdict_str == "APPROVED" else ["AC-2 failed"],
        "blockers": [],
    }
    review_findings = _make_review_findings(missing=True)
    hygiene = _make_hygiene()
    return _render_verify_report(
        verdict=verdict,
        ac_results=ac_results,
        review_findings=review_findings,
        hygiene=hygiene,
        feature=feature,
        date_str=date_str,
        mechanical_status="pass",
        ac_verification_mode="code-only",
    )


# ---------------------------------------------------------------------------
# Helpers: produce real Completion Notes content
# ---------------------------------------------------------------------------


def _make_skeleton_task():
    # type: () -> str
    """Return a minimal task file skeleton with a ## Completion Notes placeholder."""
    return (
        "# Task 001: Add feature\n\n"
        "**Status**: In Progress\n\n"
        "## Done When\n\n"
        "- [ ] Type check passes\n"
        "- [ ] Tests pass\n\n"
        "## Completion Notes\n\n"
        "[Filled in by /implement after completion]\n"
        "**Completed**: [date/time]\n"
        "**Files changed**: [actual files]\n"
        "**Contract**: Expects [X/Y verified] | Produces [X/Y verified]\n"
        "**Notes**: [deviations or observations]\n"
    )


def _make_real_completed_task(
    files=None,
    expects_met="2/2",
    produces_met="1/1",
    notes="No deviations.",
    completed_at="2026-06-17T10:00:00Z",
):
    # type: (...) -> str
    """Fill a skeleton task using the REAL _fill_completion_notes producer."""
    if files is None:
        files = ["src/feature.py", "tests/test_feature.py"]
    files_str = ", ".join(files) if files else "(none)"
    skeleton = _make_skeleton_task()
    return _fill_completion_notes(
        skeleton,
        completed_at=completed_at,
        files_changed=files_str,
        expects_met=expects_met,
        produces_met=produces_met,
        notes=notes,
    )


# ---------------------------------------------------------------------------
# TestReadVerification — real-producer round-trips
# ---------------------------------------------------------------------------


class TestReadVerificationRealProducer(unittest.TestCase):
    """Round-trip: produce verification.md via the real render_report, then parse it."""

    def test_approved_verdict_parsed(self):
        content = _render_real_verification(verdict_str="APPROVED")
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as fh:
            fh.write(content)
            path = fh.name
        try:
            result, err = read_verification(path)
            self.assertIsNone(err)
            self.assertEqual(result["verdict"], "APPROVED")
        finally:
            os.unlink(path)

    def test_needs_work_verdict_parsed(self):
        content = _render_real_verification(verdict_str="NEEDS WORK")
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as fh:
            fh.write(content)
            path = fh.name
        try:
            result, err = read_verification(path)
            self.assertIsNone(err)
            self.assertEqual(result["verdict"], "NEEDS WORK")
        finally:
            os.unlink(path)

    def test_rejected_verdict_parsed(self):
        content = _render_real_verification(verdict_str="REJECTED")
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as fh:
            fh.write(content)
            path = fh.name
        try:
            result, err = read_verification(path)
            self.assertIsNone(err)
            self.assertEqual(result["verdict"], "REJECTED")
        finally:
            os.unlink(path)

    def test_ac_list_parsed_from_real_report(self):
        """All three AC rows from the real render_report are parsed correctly."""
        ac_inputs = [
            _ac_result("AC-1", "PASS", "All unit tests pass"),
            _ac_result("AC-2", "PARTIAL", "Manual step pending"),
            _ac_result("AC-3", "UNVERIFIED", "Not verified"),
        ]
        content = _render_real_verification(
            verdict_str="APPROVED",
            ac_results=ac_inputs,
        )
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as fh:
            fh.write(content)
            path = fh.name
        try:
            result, err = read_verification(path)
            self.assertIsNone(err)
            ac_list = result["ac_list"]
            self.assertEqual(len(ac_list), 3)
            # IDs match.
            self.assertEqual(ac_list[0]["id"], "AC-1")
            self.assertEqual(ac_list[1]["id"], "AC-2")
            self.assertEqual(ac_list[2]["id"], "AC-3")
            # Statuses match.
            self.assertEqual(ac_list[0]["status"], "PASS")
            self.assertEqual(ac_list[1]["status"], "PARTIAL")
            self.assertEqual(ac_list[2]["status"], "UNVERIFIED")
        finally:
            os.unlink(path)

    def test_ac_evidence_from_real_report(self):
        """Evidence text from the real render_report is captured."""
        ac_inputs = [_ac_result("AC-1", "PASS", "Unit tests pass")]
        content = _render_real_verification(ac_results=ac_inputs)
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as fh:
            fh.write(content)
            path = fh.name
        try:
            result, err = read_verification(path)
            self.assertIsNone(err)
            self.assertGreater(len(result["ac_list"]), 0)
            self.assertIn("Unit tests pass", result["ac_list"][0]["evidence"])
        finally:
            os.unlink(path)

    def test_empty_ac_results_yields_no_rows(self):
        """When no ACs are defined, ac_list is empty."""
        content = _render_real_verification(ac_results=[])
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as fh:
            fh.write(content)
            path = fh.name
        try:
            result, err = read_verification(path)
            self.assertIsNone(err)
            self.assertEqual(result["ac_list"], [])
        finally:
            os.unlink(path)

    def test_result_path_key_matches_input(self):
        content = _render_real_verification()
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as fh:
            fh.write(content)
            path = fh.name
        try:
            result, err = read_verification(path)
            self.assertIsNone(err)
            self.assertEqual(result["path"], path)
        finally:
            os.unlink(path)

    def test_evidence_with_pipe_round_trips(self):
        """Pipe characters in evidence are escaped by render_report and unescaped on parse.

        render_report escapes a literal '|' in evidence to '\\|' before
        writing the markdown table (to avoid breaking the table structure).
        The parser must unescape '\\|' back to '|' so the caller sees the
        original string.
        """
        # Pass evidence with a literal pipe.  render_report will escape it to \\|.
        ac_inputs = [_ac_result("AC-1", "PASS", "value1 | value2")]
        content = _render_real_verification(ac_results=ac_inputs)
        # Confirm render_report DID escape the pipe in the raw content.
        self.assertIn(r"\|", content,
                      msg="render_report should escape '|' to '\\|' in table cells")
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as fh:
            fh.write(content)
            path = fh.name
        try:
            result, err = read_verification(path)
            self.assertIsNone(err)
            # After parsing, the pipe should be unescaped back to '|'.
            evidence = result["ac_list"][0]["evidence"]
            self.assertIn("|", evidence,
                          msg="Parser should unescape '\\|' back to '|'")
            self.assertNotIn(r"\|", evidence,
                             msg="No residual escaped pipes in parsed evidence")
        finally:
            os.unlink(path)


class TestReadVerificationEdgeCases(unittest.TestCase):
    """Edge cases: missing file, verdict not present."""

    def test_file_not_found_returns_error(self):
        result, err = read_verification("/nonexistent/path/verification.md")
        self.assertEqual(result, {})
        self.assertIsNotNone(err)
        self.assertIn("verification.md", err)

    def test_verdict_missing_returns_empty_string(self):
        content = "## Acceptance Criteria\n\n| AC | Status | Evidence |\n|---|---|---|\n| AC-1 | PASS | ok |\n"
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as fh:
            fh.write(content)
            path = fh.name
        try:
            result, err = read_verification(path)
            self.assertIsNone(err)
            self.assertEqual(result["verdict"], "")
        finally:
            os.unlink(path)

    def test_header_row_not_in_ac_list(self):
        """The AC table header row (AC | Status | Evidence) is NOT in ac_list."""
        content = _render_real_verification(ac_results=[_ac_result("AC-1", "PASS")])
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as fh:
            fh.write(content)
            path = fh.name
        try:
            result, err = read_verification(path)
            self.assertIsNone(err)
            for ac in result["ac_list"]:
                self.assertNotEqual(ac["id"].lower(), "ac")
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# Fix 1: TestReadVerificationEmptyEvidence — empty evidence round-trips
# ---------------------------------------------------------------------------

# All status values that render_report may emit for an AC row.
_ALL_AC_STATUSES = [
    "PASS", "FAIL", "PARTIAL", "MANUAL",
    "PASS (code)", "FAIL (code)", "PARTIAL (code)", "UNVERIFIED",
]


class TestReadVerificationEmptyEvidence(unittest.TestCase):
    """Fix 1 regression: ACs with EMPTY evidence must NOT be dropped.

    The real producer render_report writes "| AC-N | STATUS |  |" when
    evidence is "" — the trailing empty evidence cell was previously
    mis-dropped by the two-step filter (strip then remove-empty).
    The corrected parts[1:-1] slice preserves that empty cell so the
    row reaches the ac_list with evidence == "".
    """

    def _round_trip_status(self, status):
        # type: (str) -> Dict
        """Produce a real verification.md with one AC (given status, empty
        evidence), parse it, and return the ac_list entry."""
        ac_inputs = [_ac_result("AC-1", status, "")]
        content = _render_real_verification(ac_results=ac_inputs)
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as fh:
            fh.write(content)
            path = fh.name
        try:
            result, err = read_verification(path)
            self.assertIsNone(err, msg="Parse error for status {0!r}".format(status))
            ac_list = result["ac_list"]
            self.assertEqual(
                len(ac_list), 1,
                msg="AC with empty evidence for status {0!r} was dropped — "
                    "ac_list has {1} entries".format(status, len(ac_list)),
            )
            return ac_list[0]
        finally:
            os.unlink(path)

    def test_unverified_empty_evidence_not_dropped(self):
        """The canonical empty-evidence case: UNVERIFIED with no evidence text."""
        ac = self._round_trip_status("UNVERIFIED")
        self.assertEqual(ac["id"], "AC-1")
        self.assertEqual(ac["status"], "UNVERIFIED")
        self.assertEqual(ac["evidence"], "")

    def test_all_statuses_with_empty_evidence_survive(self):
        """All 8 AC status values with empty evidence are parsed (none dropped)."""
        for status in _ALL_AC_STATUSES:
            with self.subTest(status=status):
                ac = self._round_trip_status(status)
                self.assertEqual(ac["status"], status,
                                 msg="status mismatch for {0!r}".format(status))
                self.assertEqual(ac["evidence"], "",
                                 msg="evidence should be '' for {0!r}".format(status))

    def test_empty_evidence_alongside_nonempty(self):
        """Mix of empty and non-empty evidence: all rows present and correct."""
        ac_inputs = [
            _ac_result("AC-1", "PASS", "Tests pass"),
            _ac_result("AC-2", "UNVERIFIED", ""),
            _ac_result("AC-3", "PARTIAL", ""),
            _ac_result("AC-4", "FAIL", "Assertion error on line 42"),
        ]
        content = _render_real_verification(ac_results=ac_inputs)
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as fh:
            fh.write(content)
            path = fh.name
        try:
            result, err = read_verification(path)
            self.assertIsNone(err)
            ac_list = result["ac_list"]
            self.assertEqual(len(ac_list), 4, msg="Expected 4 ACs; got {0}".format(len(ac_list)))
            self.assertEqual(ac_list[0]["evidence"], "Tests pass")
            self.assertEqual(ac_list[1]["evidence"], "")
            self.assertEqual(ac_list[2]["evidence"], "")
            self.assertEqual(ac_list[3]["evidence"], "Assertion error on line 42")
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# Fix 3: TestParseCompletionNotesCommaLimitation — documented mis-split
# ---------------------------------------------------------------------------


class TestParseCompletionNotesCommaLimitation(unittest.TestCase):
    """Fix 3: document and assert the comma-in-filename mis-split behaviour.

    The producer joins file paths with ', '; a comma inside a filename would
    cause parse_completion_notes to over-split.  This test asserts the
    DOCUMENTED limitation so future readers see it explicitly rather than
    tracing the bug from scratch.
    """

    def test_comma_in_filename_causes_missplit(self):
        """A filename containing a comma mis-splits into two fake names.

        This is the DOCUMENTED limitation (see parse_completion_notes docstring).
        The test records the behaviour; do NOT "fix" it here — the producer
        (_implement mark-complete) is out of scope.
        """
        # Simulate a task text where the Files-changed value contains a comma
        # inside a filename (as if the producer had written it literally).
        task_text = (
            "# Task 001\n\n"
            "## Completion Notes\n\n"
            "**Completed**: 2026-06-18T10:00:00Z\n"
            "**Files changed**: src/foo,bar.py, tests/test.py\n"
            "**Contract**: Expects 1/1 | Produces 1/1\n"
            "**Notes**: (none)\n"
        )
        result = parse_completion_notes(task_text)
        # The comma in "foo,bar.py" causes it to split into "src/foo" and "bar.py"
        # plus "tests/test.py" — so we get 3 entries, not 2.
        self.assertEqual(len(result["files_changed"]), 3,
                         msg="Documented mis-split: expected 3 tokens from comma-in-name")
        self.assertIn("src/foo", result["files_changed"])
        self.assertIn("bar.py", result["files_changed"])
        self.assertIn("tests/test.py", result["files_changed"])


# ---------------------------------------------------------------------------
# TestReadPlanDecisionsPhantomHeading — Fix 2 regression
# ---------------------------------------------------------------------------


class TestReadPlanDecisionsPhantomHeading(unittest.TestCase):
    """Fix 2: verify that '## Key Design Decisions' (double-hash) is NOT matched.

    The current /plan template emits '### Key Design Decisions' (triple-hash).
    The double-hash variant was a phantom entry in _PLAN_DECISIONS_HEADINGS
    with zero real instances; it has been removed.  This test confirms the
    parser does NOT recognise the phantom heading, so we catch any regression
    that re-introduces it.
    """

    def test_double_hash_key_design_decisions_not_matched(self):
        """A plan.md with only '## Key Design Decisions' (double-hash) → empty decisions."""
        content = (
            "# Plan: Foo\n\n"
            "## Key Design Decisions\n\n"
            "| Decision | Chosen Approach | Why | Alternatives Rejected |\n"
            "| --- | --- | --- | --- |\n"
            "| Use caching | Redis | Speed | Memcached |\n"
        )
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as fh:
            fh.write(content)
            path = fh.name
        try:
            result, err = read_plan_decisions(path)
            self.assertIsNone(err)
            self.assertEqual(
                result["decisions"], [],
                msg="Phantom '## Key Design Decisions' (double-hash) must NOT be matched",
            )
        finally:
            os.unlink(path)

    def test_triple_hash_key_design_decisions_still_matched(self):
        """'### Key Design Decisions' (triple-hash, current template) is still parsed."""
        content = (
            "# Plan: Foo\n\n"
            "### Key Design Decisions\n\n"
            "| Decision | Chosen Approach | Why | Alternatives Rejected |\n"
            "| --- | --- | --- | --- |\n"
            "| Use caching | Redis | Speed | Memcached |\n"
        )
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as fh:
            fh.write(content)
            path = fh.name
        try:
            result, err = read_plan_decisions(path)
            self.assertIsNone(err)
            self.assertEqual(len(result["decisions"]), 1)
            self.assertEqual(result["decisions"][0]["decision"], "Use caching")
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# TestDeadSymbolsRemoved — Fix 4 + Fix 5 regression
# ---------------------------------------------------------------------------


class TestDeadSymbolsRemoved(unittest.TestCase):
    """Fix 4 + 5: confirm deleted dead symbols are no longer in _inputs.py source."""

    def test_ac_row_re_deleted(self):
        """_AC_ROW_RE was a dead symbol; it must no longer be defined."""
        from _summarize import _inputs
        self.assertFalse(
            hasattr(_inputs, "_AC_ROW_RE"),
            msg="_AC_ROW_RE is dead code and must be removed from _inputs.py",
        )

    def test_is_table_header_row_deleted(self):
        """_is_table_header_row was a dead function; it must no longer exist."""
        from _summarize import _inputs
        self.assertFalse(
            hasattr(_inputs, "_is_table_header_row"),
            msg="_is_table_header_row is dead code and must be removed from _inputs.py",
        )

    def test_unverified_annotation_deleted(self):
        """_UNVERIFIED_ANNOTATION was an unused constant; it must no longer exist."""
        from _summarize import _inputs
        self.assertFalse(
            hasattr(_inputs, "_UNVERIFIED_ANNOTATION"),
            msg="_UNVERIFIED_ANNOTATION is unused and must be removed from _inputs.py",
        )


# ---------------------------------------------------------------------------
# TestParseCompletionNotes — real-producer round-trips
# ---------------------------------------------------------------------------


class TestParseCompletionNotesRealProducer(unittest.TestCase):
    """Round-trip: fill a task via the real _fill_completion_notes, then parse it."""

    def test_files_changed_list_parsed(self):
        """files_changed is a list split from the comma-separated string."""
        files = ["src/feature.py", "tests/test_feature.py"]
        task_text = _make_real_completed_task(files=files)
        result = parse_completion_notes(task_text)
        self.assertTrue(result["has_notes"])
        self.assertCountEqual(result["files_changed"], files)

    def test_expects_met_parsed(self):
        task_text = _make_real_completed_task(expects_met="3/3")
        result = parse_completion_notes(task_text)
        self.assertEqual(result["expects_met"], "3/3")

    def test_produces_met_parsed(self):
        task_text = _make_real_completed_task(produces_met="2/2")
        result = parse_completion_notes(task_text)
        self.assertEqual(result["produces_met"], "2/2")

    def test_notes_text_parsed(self):
        task_text = _make_real_completed_task(notes="Used a different approach.")
        result = parse_completion_notes(task_text)
        self.assertEqual(result["notes"], "Used a different approach.")

    def test_notes_none_becomes_empty_string(self):
        """When the notes value is "(none)", the parser normalizes it to ""."""
        task_text = _make_real_completed_task(notes="(none)")
        # But _make_real_completed_task passes "(none)" directly; _fill_completion_notes
        # writes it as "**Notes**: (none)".  The parser should normalize to "".
        # Actually: if notes="" is passed to _fill_completion_notes, the handler
        # writes "(none)".  Simulate that path.
        skeleton = _make_skeleton_task()
        task_text_none = _fill_completion_notes(
            skeleton,
            completed_at="2026-06-17T10:00:00Z",
            files_changed="src/a.py",
            expects_met="1/1",
            produces_met="1/1",
            notes="(none)",
        )
        result = parse_completion_notes(task_text_none)
        self.assertEqual(result["notes"], "")

    def test_completed_at_timestamp_parsed(self):
        task_text = _make_real_completed_task(completed_at="2026-06-17T10:00:00Z")
        result = parse_completion_notes(task_text)
        self.assertEqual(result["completed_at"], "2026-06-17T10:00:00Z")

    def test_no_files_yields_empty_list(self):
        """When files_changed is '(none)', files_changed list is empty."""
        skeleton = _make_skeleton_task()
        task_text = _fill_completion_notes(
            skeleton,
            completed_at="2026-06-17T10:00:00Z",
            files_changed="(none)",
            expects_met="0/0",
            produces_met="0/0",
            notes="nothing to do",
        )
        result = parse_completion_notes(task_text)
        self.assertEqual(result["files_changed"], [])

    def test_has_notes_true_when_section_present(self):
        task_text = _make_real_completed_task()
        result = parse_completion_notes(task_text)
        self.assertTrue(result["has_notes"])

    def test_has_notes_false_when_section_absent(self):
        """A task file without ## Completion Notes → has_notes=False."""
        text = "# Task 001\n\n**Status**: In Progress\n\n## Done When\n\n- [ ] pass\n"
        result = parse_completion_notes(text)
        self.assertFalse(result["has_notes"])
        self.assertEqual(result["files_changed"], [])
        self.assertEqual(result["notes"], "")

    def test_has_unverified_false_when_all_ticked(self):
        """All Done-When boxes ticked → has_unverified=False."""
        task_text = _make_real_completed_task()
        # The skeleton has unticked boxes; _fill_completion_notes doesn't tick them.
        # We need to simulate the full mark-complete flow: tick the boxes.
        from _implement._cmds_complete import _tick_done_when_boxes
        ticked = _tick_done_when_boxes(task_text, [])
        filled = _fill_completion_notes(
            ticked,
            completed_at="2026-06-17T10:00:00Z",
            files_changed="src/a.py",
            expects_met="2/2",
            produces_met="1/1",
            notes="none",
        )
        result = parse_completion_notes(filled)
        self.assertFalse(result["has_unverified"])

    def test_has_unverified_true_when_box_annotated(self):
        """A Done-When box annotated as unverified → has_unverified=True."""
        from _implement._cmds_complete import _tick_done_when_boxes
        task_text = _make_real_completed_task()
        # Simulate: tick all boxes except "Type check" which is unverified.
        ticked = _tick_done_when_boxes(task_text, ["Type check"])
        result = parse_completion_notes(ticked)
        self.assertTrue(result["has_unverified"])

    def test_multiple_files_split_correctly(self):
        """Multiple files are split correctly from the comma-separated string."""
        files = ["src/a.py", "src/b.py", "src/c.py", "tests/test.py"]
        task_text = _make_real_completed_task(files=files)
        result = parse_completion_notes(task_text)
        self.assertEqual(len(result["files_changed"]), 4)
        self.assertCountEqual(result["files_changed"], files)


# ---------------------------------------------------------------------------
# TestReadPlanDecisions — real-producer round-trips
# ---------------------------------------------------------------------------


class TestReadPlanDecisionsShapeA(unittest.TestCase):
    """Shape A: '### Key Design Decisions' (current /plan template).
    Uses tests/lib/fixtures/plan_handoff_fixture.md — a REAL plan fixture.
    """

    def _assert_fixture_exists(self):
        if not os.path.isfile(_PLAN_FIXTURE_SHAPE_A):
            self.skipTest(
                "Shape A fixture not found: {0}".format(_PLAN_FIXTURE_SHAPE_A)
            )

    def test_shape_a_detected(self):
        self._assert_fixture_exists()
        result, err = read_plan_decisions(_PLAN_FIXTURE_SHAPE_A)
        self.assertIsNone(err)
        self.assertEqual(result["shape"], "A")

    def test_shape_a_heading_text(self):
        self._assert_fixture_exists()
        result, err = read_plan_decisions(_PLAN_FIXTURE_SHAPE_A)
        self.assertIsNone(err)
        self.assertIn("Key Design Decisions", result["heading"])

    def test_shape_a_decisions_nonempty(self):
        self._assert_fixture_exists()
        result, err = read_plan_decisions(_PLAN_FIXTURE_SHAPE_A)
        self.assertIsNone(err)
        self.assertGreater(len(result["decisions"]), 0)

    def test_shape_a_decision_row_keys(self):
        self._assert_fixture_exists()
        result, err = read_plan_decisions(_PLAN_FIXTURE_SHAPE_A)
        self.assertIsNone(err)
        for dec in result["decisions"]:
            for key in ("decision", "chosen", "rationale", "rejected"):
                self.assertIn(key, dec, msg="Missing key: {0}".format(key))

    def test_shape_a_known_decision_content(self):
        """The fixture contains 'Filter location' and 'Match strategy' decisions."""
        self._assert_fixture_exists()
        result, err = read_plan_decisions(_PLAN_FIXTURE_SHAPE_A)
        self.assertIsNone(err)
        decisions_text = " ".join(
            dec["decision"] for dec in result["decisions"]
        )
        # Verify at least one expected decision from the real fixture is parsed.
        self.assertTrue(
            "Filter" in decisions_text or "Match" in decisions_text,
            msg="Expected filter/match decisions, got: {0}".format(decisions_text),
        )

    def test_shape_a_rejected_column_present(self):
        """Shape A has an 'Alternatives Rejected' column → rejected field populated."""
        self._assert_fixture_exists()
        result, err = read_plan_decisions(_PLAN_FIXTURE_SHAPE_A)
        self.assertIsNone(err)
        # At least one non-placeholder row should have a non-empty rejected field.
        non_empty_rejected = [
            d["rejected"] for d in result["decisions"] if d["rejected"]
        ]
        self.assertGreater(
            len(non_empty_rejected), 0,
            msg="Expected at least one non-empty rejected field",
        )

    def test_path_key_in_result(self):
        self._assert_fixture_exists()
        result, err = read_plan_decisions(_PLAN_FIXTURE_SHAPE_A)
        self.assertIsNone(err)
        self.assertEqual(result["path"], _PLAN_FIXTURE_SHAPE_A)


class TestReadPlanDecisionsShapeB(unittest.TestCase):
    """Shape B: '## Architecture Decisions' (older /plan output).
    Uses tests/lib/fixtures/specs/008-sample-feature/plan.md — a REAL plan fixture.
    """

    def _assert_fixture_exists(self):
        if not os.path.isfile(_PLAN_FIXTURE_SHAPE_B):
            self.skipTest(
                "Shape B fixture not found: {0}".format(_PLAN_FIXTURE_SHAPE_B)
            )

    def test_shape_b_detected(self):
        self._assert_fixture_exists()
        result, err = read_plan_decisions(_PLAN_FIXTURE_SHAPE_B)
        self.assertIsNone(err)
        self.assertEqual(result["shape"], "B")

    def test_shape_b_heading_text(self):
        self._assert_fixture_exists()
        result, err = read_plan_decisions(_PLAN_FIXTURE_SHAPE_B)
        self.assertIsNone(err)
        self.assertIn("Architecture Decisions", result["heading"])

    def test_shape_b_decisions_nonempty(self):
        self._assert_fixture_exists()
        result, err = read_plan_decisions(_PLAN_FIXTURE_SHAPE_B)
        self.assertIsNone(err)
        self.assertGreater(len(result["decisions"]), 0)

    def test_shape_b_decision_row_keys(self):
        self._assert_fixture_exists()
        result, err = read_plan_decisions(_PLAN_FIXTURE_SHAPE_B)
        self.assertIsNone(err)
        for dec in result["decisions"]:
            for key in ("decision", "chosen", "rationale", "rejected"):
                self.assertIn(key, dec, msg="Missing key: {0}".format(key))

    def test_shape_b_rejected_is_empty(self):
        """Shape B (## Architecture Decisions) has no Alternatives Rejected column."""
        self._assert_fixture_exists()
        result, err = read_plan_decisions(_PLAN_FIXTURE_SHAPE_B)
        self.assertIsNone(err)
        for dec in result["decisions"]:
            self.assertEqual(
                dec["rejected"], "",
                msg="Shape B should have empty rejected, got: {0}".format(dec["rejected"]),
            )

    def test_shape_b_known_content(self):
        """The 008 fixture has 'Filter location' and 'Match strategy' decisions."""
        self._assert_fixture_exists()
        result, err = read_plan_decisions(_PLAN_FIXTURE_SHAPE_B)
        self.assertIsNone(err)
        decisions_text = " ".join(dec["decision"] for dec in result["decisions"])
        self.assertTrue(
            "Filter" in decisions_text or "Match" in decisions_text,
            msg="Expected known decisions, got: {0}".format(decisions_text),
        )


class TestReadPlanDecisionsEdgeCases(unittest.TestCase):
    """Edge cases for read_plan_decisions."""

    def test_no_decisions_heading_yields_empty_list(self):
        """A plan.md with no recognized decisions heading → empty decisions, no error."""
        content = "# Plan: Foo\n\n## Summary\n\nSome text.\n"
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as fh:
            fh.write(content)
            path = fh.name
        try:
            result, err = read_plan_decisions(path)
            self.assertIsNone(err)
            self.assertEqual(result["decisions"], [])
        finally:
            os.unlink(path)

    def test_file_not_found_returns_error(self):
        result, err = read_plan_decisions("/nonexistent/plan.md")
        self.assertEqual(result, {})
        self.assertIsNotNone(err)
        self.assertIn("plan.md", err)

    def test_placeholder_rows_excluded(self):
        """Rows where all cells are [placeholder] are not included in decisions."""
        content = (
            "# Plan\n\n"
            "### Key Design Decisions\n\n"
            "| Decision | Chosen Approach | Why | Alternatives Rejected |\n"
            "| --- | --- | --- | --- |\n"
            "| Real decision | Real approach | Real why | Real alternative |\n"
            "| [decision] | [approach] | [rationale] | [alternatives] |\n"
        )
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as fh:
            fh.write(content)
            path = fh.name
        try:
            result, err = read_plan_decisions(path)
            self.assertIsNone(err)
            # Only the non-placeholder row should be included.
            real_rows = [d for d in result["decisions"] if "Real" in d["decision"]]
            self.assertEqual(len(real_rows), 1)
        finally:
            os.unlink(path)

    def test_no_plan_handoff_import_in_code(self):
        """D9: _inputs.py must NOT import or open plan-handoff.json in executable code.

        The docstring may MENTION plan-handoff.json to explain what we don't do —
        that's fine and deliberate.  What matters is that no import statement,
        open() call, or json.load() reads plan-handoff.json at runtime.
        We check only non-docstring lines (those not inside triple-quote blocks).
        """
        inputs_src = _LIB_DIR / "_summarize" / "_inputs.py"
        with open(str(inputs_src), "r", encoding="utf-8") as fh:
            src_text = fh.read()

        # Strip the module-level docstring (first triple-quoted string).
        # A simple approach: check that no "import" line references plan_handoff,
        # and no open()/load() line references "plan-handoff.json".
        lines = src_text.splitlines()
        in_docstring = False
        docstring_char = None
        code_lines = []
        for line in lines:
            stripped = line.strip()
            if not in_docstring:
                # Detect start of a triple-quoted string.
                if stripped.startswith('"""') or stripped.startswith("'''"):
                    char = stripped[:3]
                    # If it's also the end on the same line, skip it entirely.
                    if stripped.count(char) >= 2 and len(stripped) > 3:
                        continue  # Single-line docstring.
                    in_docstring = True
                    docstring_char = char
                    continue
                code_lines.append(line)
            else:
                # Inside docstring: look for closing triple-quote.
                if docstring_char and docstring_char in stripped:
                    in_docstring = False
                # Don't add docstring lines to code_lines.

        code_text = "\n".join(code_lines)

        # No import statement should name plan_handoff.
        import_lines = [l for l in code_lines if l.strip().startswith("import") or
                        "from " in l and "import" in l]
        for l in import_lines:
            self.assertNotIn(
                "plan_handoff", l,
                msg="D9 violation: import of plan_handoff in {0}".format(l),
            )

        # No open() or load() call targeting plan-handoff.json in code.
        self.assertNotIn(
            '"plan-handoff.json"', code_text,
            msg="D9 violation: open/load of plan-handoff.json in executable code",
        )
        self.assertNotIn(
            "'plan-handoff.json'", code_text,
            msg="D9 violation: open/load of plan-handoff.json in executable code",
        )


# ---------------------------------------------------------------------------
# TestCmdHandlers — CLI exit-code + JSON emission
# ---------------------------------------------------------------------------


class _MockArgs:
    """Minimal namespace mimic for argparse.Namespace."""
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class TestCmdReadVerification(unittest.TestCase):
    def test_missing_path_exits_2(self):
        args = _MockArgs(verification_path="")
        rc = cmd_read_verification(args)
        self.assertEqual(rc, 2)

    def test_happy_path_emits_json(self):
        content = _render_real_verification()
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as fh:
            fh.write(content)
            path = fh.name
        try:
            args = _MockArgs(verification_path=path)
            captured = io.StringIO()
            old_stdout = sys.stdout
            sys.stdout = captured
            try:
                rc = cmd_read_verification(args)
            finally:
                sys.stdout = old_stdout
            self.assertEqual(rc, 0)
            data = json.loads(captured.getvalue())
            self.assertIn("ac_list", data)
            self.assertIn("verdict", data)
        finally:
            os.unlink(path)


class TestCmdParseCompletionNotes(unittest.TestCase):
    def test_missing_task_file_exits_2(self):
        args = _MockArgs(task_files=[])
        rc = cmd_parse_completion_notes(args)
        self.assertEqual(rc, 2)

    def test_happy_path_emits_json(self):
        task_text = _make_real_completed_task()
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as fh:
            fh.write(task_text)
            path = fh.name
        try:
            args = _MockArgs(task_files=[path])
            captured = io.StringIO()
            old_stdout = sys.stdout
            sys.stdout = captured
            try:
                rc = cmd_parse_completion_notes(args)
            finally:
                sys.stdout = old_stdout
            self.assertEqual(rc, 0)
            data = json.loads(captured.getvalue())
            self.assertIsInstance(data, list)
            self.assertEqual(len(data), 1)
            self.assertIn("files_changed", data[0])
        finally:
            os.unlink(path)

    def test_two_task_files_emits_two_entries(self):
        t1 = _make_real_completed_task(files=["src/a.py"])
        t2 = _make_real_completed_task(files=["src/b.py"])
        paths = []
        try:
            for txt in (t1, t2):
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".md", delete=False, encoding="utf-8"
                ) as fh:
                    fh.write(txt)
                    paths.append(fh.name)
            args = _MockArgs(task_files=paths)
            captured = io.StringIO()
            old_stdout = sys.stdout
            sys.stdout = captured
            try:
                rc = cmd_parse_completion_notes(args)
            finally:
                sys.stdout = old_stdout
            self.assertEqual(rc, 0)
            data = json.loads(captured.getvalue())
            self.assertEqual(len(data), 2)
        finally:
            for p in paths:
                if os.path.exists(p):
                    os.unlink(p)


class TestCmdReadPlanDecisions(unittest.TestCase):
    def test_missing_path_exits_2(self):
        args = _MockArgs(plan_path="")
        rc = cmd_read_plan_decisions(args)
        self.assertEqual(rc, 2)

    def test_happy_path_emits_json(self):
        if not os.path.isfile(_PLAN_FIXTURE_SHAPE_A):
            self.skipTest("Shape A fixture not found")
        args = _MockArgs(plan_path=_PLAN_FIXTURE_SHAPE_A)
        captured = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        try:
            rc = cmd_read_plan_decisions(args)
        finally:
            sys.stdout = old_stdout
        self.assertEqual(rc, 0)
        data = json.loads(captured.getvalue())
        self.assertIn("decisions", data)
        self.assertIn("shape", data)
