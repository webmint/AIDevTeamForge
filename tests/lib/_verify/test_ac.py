"""Tests for src/devforge/lib/_verify/_ac.py and the parse-acs CLI verb.

Real-producer round-trip discipline:
  parse_acs is tested against the REAL fixture
  tests/lib/fixtures/specify-sample-migration.md — the file produced by
  specify_helper and committed to the test fixture directory.  No hand-authored
  AC strings are used as the primary test target.

Coverage:
  parse_acs (function level):
    - Happy path against the real specify-sample-migration.md fixture.
      Asserts AC-1..AC-7 extracted with correct text and checked=False.
    - Checked [x] variant — inline text fixture confirms checked=True.
    - Mixed checked/unchecked — combined inline fixture.
    - Subsection assignment — each AC's subsection matches the ### heading above it.
    - Empty string / no AC section → empty list (no crash).
    - File that does not exist → empty list (no crash).
    - AC section followed by ## 6 section — parser stops at the boundary.
    - Text before AC section is ignored.

  CLI round-trip via main([...]):
    - parse-acs --spec <real-fixture> → non-empty JSON array on stdout, exit 0.
    - parse-acs --spec <real-fixture> produces AC-1..AC-7 (count check).
    - Missing --spec argument → argparse error, exit != 0.
    - Non-existent spec path → exit 0, empty JSON array.
"""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"
_FIXTURES_DIR = _REPO_ROOT / "tests" / "lib" / "fixtures"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _verify._ac import merge_ac_results, parse_acs  # noqa: E402
from _verify._cli import main  # noqa: E402

# Path to the real specify-produced fixture.
_REAL_SPEC = str(_FIXTURES_DIR / "specify-sample-migration.md")


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _capture(argv):
    """Run main(argv) with captured stdout/stderr.  Returns (stdout, stderr, rc)."""
    buf_out = io.StringIO()
    buf_err = io.StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = buf_out, buf_err
    try:
        rc = main(argv)
    except SystemExit as exc:
        rc = exc.code if isinstance(exc.code, int) else 2
    finally:
        sys.stdout, sys.stderr = old_out, old_err
    return buf_out.getvalue(), buf_err.getvalue(), rc


# ---------------------------------------------------------------------------
# Tests — parse_acs function (real fixture)
# ---------------------------------------------------------------------------


class TestParseAcsRealFixture(unittest.TestCase):
    """Round-trip against the real specify-sample-migration.md fixture."""

    @classmethod
    def setUpClass(cls):
        cls.acs = parse_acs(_REAL_SPEC)

    def test_fixture_exists(self):
        """Confirm the real fixture file is present — if this fails the repo is broken."""
        self.assertTrue(
            os.path.isfile(_REAL_SPEC),
            "Real fixture missing: {0}".format(_REAL_SPEC),
        )

    def test_returns_seven_acs(self):
        """specify-sample-migration.md has exactly AC-1 through AC-7."""
        self.assertEqual(len(self.acs), 7, "Expected 7 ACs, got {0}: {1}".format(
            len(self.acs), [a["id"] for a in self.acs]
        ))

    def test_ids_sequential(self):
        """AC ids are AC-1..AC-7 in order."""
        expected = ["AC-{0}".format(i) for i in range(1, 8)]
        actual = [a["id"] for a in self.acs]
        self.assertEqual(actual, expected)

    def test_all_unchecked(self):
        """All ACs in the fixture have - [ ] (unchecked)."""
        for ac in self.acs:
            self.assertFalse(ac["checked"], "Expected unchecked: {0}".format(ac))

    def test_ac1_text(self):
        """AC-1 text matches the EARS sentence in the fixture."""
        ac1 = self.acs[0]
        self.assertEqual(ac1["id"], "AC-1")
        self.assertIn("lerna", ac1["text"])

    def test_ac7_text(self):
        """AC-7 text mentions yarn lockfiles — the last AC in the fixture."""
        ac7 = self.acs[6]
        self.assertEqual(ac7["id"], "AC-7")
        self.assertIn("yarn", ac7["text"].lower())

    def test_ac3_ears_when(self):
        """AC-3 is a WHEN…THEN EARS sentence — text starts with 'WHEN'."""
        ac3 = self.acs[2]
        self.assertEqual(ac3["id"], "AC-3")
        self.assertTrue(
            ac3["text"].upper().startswith("WHEN"),
            "AC-3 text should start with WHEN: {0!r}".format(ac3["text"]),
        )

    def test_subsection_populated(self):
        """Every AC carries a non-empty subsection string (### heading)."""
        for ac in self.acs:
            self.assertTrue(
                ac["subsection"],
                "AC {0} has empty subsection".format(ac["id"]),
            )

    def test_ac1_subsection(self):
        """AC-1 is under the '5.1 Tooling / artifact presence and absence' subsection."""
        ac1 = self.acs[0]
        self.assertIn("5.1", ac1["subsection"])

    def test_dict_shape(self):
        """Each AC dict has exactly the required keys."""
        required = {"id", "text", "checked", "subsection"}
        for ac in self.acs:
            self.assertEqual(set(ac.keys()), required)

    def test_text_is_stripped(self):
        """No AC text has leading or trailing whitespace."""
        for ac in self.acs:
            self.assertEqual(ac["text"], ac["text"].strip())


# ---------------------------------------------------------------------------
# Tests — checked variant and mixed state
# ---------------------------------------------------------------------------


class TestParseAcsChecked(unittest.TestCase):
    """parse_acs handles - [x] (checked) and - [X] (uppercase X) correctly."""

    def _spec(self, lines):
        """Wrap lines in a minimal spec with AC section."""
        header = (
            "# Spec\n\n"
            "## 5. Acceptance Criteria\n\n"
            "### 5.1 Functional\n\n"
        )
        return header + "\n".join(lines) + "\n\n## 6. Out of Scope\n\nN/A\n"

    def test_lowercase_x_checked(self):
        spec = self._spec(["- [x] **AC-1**: The system shall do it."])
        acs = parse_acs(spec)
        self.assertEqual(len(acs), 1)
        self.assertTrue(acs[0]["checked"])

    def test_uppercase_x_checked(self):
        spec = self._spec(["- [X] **AC-1**: The system shall do it."])
        acs = parse_acs(spec)
        self.assertEqual(len(acs), 1)
        self.assertTrue(acs[0]["checked"])

    def test_space_unchecked(self):
        spec = self._spec(["- [ ] **AC-1**: The system shall do it."])
        acs = parse_acs(spec)
        self.assertEqual(len(acs), 1)
        self.assertFalse(acs[0]["checked"])

    def test_mixed_checked_and_unchecked(self):
        spec = self._spec([
            "- [x] **AC-1**: Checked AC.",
            "- [ ] **AC-2**: Unchecked AC.",
            "- [x] **AC-3**: Also checked.",
        ])
        acs = parse_acs(spec)
        self.assertEqual(len(acs), 3)
        self.assertTrue(acs[0]["checked"])
        self.assertFalse(acs[1]["checked"])
        self.assertTrue(acs[2]["checked"])


# ---------------------------------------------------------------------------
# Tests — subsection tracking
# ---------------------------------------------------------------------------


class TestParseAcsSubsections(unittest.TestCase):
    """parse_acs tracks ### subsection headings correctly."""

    _SPEC = textwrap.dedent("""\
        # Spec

        ## 5. Acceptance Criteria

        ### 5.1 First subsection

        - [ ] **AC-1**: First AC.

        ### 5.2 Second subsection

        - [ ] **AC-2**: Second AC.
        - [ ] **AC-3**: Third AC.

        ## 6. Out of Scope

        N/A
    """)

    @classmethod
    def setUpClass(cls):
        cls.acs = parse_acs(cls._SPEC)

    def test_count(self):
        self.assertEqual(len(self.acs), 3)

    def test_ac1_subsection(self):
        self.assertIn("First subsection", self.acs[0]["subsection"])

    def test_ac2_subsection(self):
        self.assertIn("Second subsection", self.acs[1]["subsection"])

    def test_ac3_subsection_same_as_ac2(self):
        """AC-3 inherits the same subsection as AC-2 (no heading change)."""
        self.assertEqual(self.acs[1]["subsection"], self.acs[2]["subsection"])


# ---------------------------------------------------------------------------
# Tests — boundary + error conditions
# ---------------------------------------------------------------------------


class TestParseAcsBoundary(unittest.TestCase):
    """parse_acs handles edge cases without crashing."""

    def test_empty_string(self):
        self.assertEqual(parse_acs(""), [])

    def test_no_ac_section(self):
        spec = "# Spec\n\n## 1. Overview\n\nSome text.\n"
        self.assertEqual(parse_acs(spec), [])

    def test_nonexistent_file_path(self):
        """A path that doesn't exist as a file is treated as spec text (returns [])."""
        result = parse_acs("/nonexistent/path/does_not_exist.md")
        # os.path.exists returns False for this path, so parse_acs treats the
        # string as raw text. The string is not a spec, so result is [].
        self.assertEqual(result, [])

    def test_file_path_returns_acs(self):
        """When given a real file path, parse_acs reads it and returns ACs."""
        spec_text = (
            "# S\n\n"
            "## Acceptance Criteria\n\n"
            "### 5.1 A\n\n"
            "- [ ] **AC-1**: The system shall X.\n\n"
            "## 6. Out of Scope\n\n"
        )
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as fh:
            fh.write(spec_text)
            tmp_path = fh.name
        try:
            acs = parse_acs(tmp_path)
            self.assertEqual(len(acs), 1)
            self.assertEqual(acs[0]["id"], "AC-1")
        finally:
            os.unlink(tmp_path)

    def test_ac_section_stops_at_next_level2(self):
        """Parser stops when it sees ## 6. Out of Scope (not continuing into it)."""
        spec = (
            "# Spec\n\n"
            "## 5. Acceptance Criteria\n\n"
            "### 5.1 A\n\n"
            "- [ ] **AC-1**: Valid AC.\n\n"
            "## 6. Out of Scope\n\n"
            "- [ ] **AC-99**: Should NOT be parsed.\n"
        )
        acs = parse_acs(spec)
        ids = [a["id"] for a in acs]
        self.assertIn("AC-1", ids)
        self.assertNotIn("AC-99", ids)

    def test_na_subsections_skipped(self):
        """N/A lines in a subsection are skipped; AC lines are still parsed."""
        spec = (
            "## Acceptance Criteria\n\n"
            "### 5.1 A\n\n"
            "N/A — no applicable ACs in this category.\n\n"
            "### 5.2 B\n\n"
            "- [ ] **AC-1**: A real AC.\n\n"
            "## 6. Done\n"
        )
        acs = parse_acs(spec)
        self.assertEqual(len(acs), 1)
        self.assertEqual(acs[0]["id"], "AC-1")

    def test_verification_hint_line_not_captured_in_text(self):
        """The > Verification: hint line is not included in AC text."""
        spec = (
            "## Acceptance Criteria\n\n"
            "### 5.1 A\n\n"
            "- [ ] **AC-1**: The repository shall contain no occurrences of `lerna`.\n"
            "  > Verification: grep -rE 'lerna' . returns no matches\n\n"
            "## 6. Done\n"
        )
        acs = parse_acs(spec)
        self.assertEqual(len(acs), 1)
        # The text is only the AC line content, not the > hint.
        self.assertNotIn("Verification:", acs[0]["text"])


# ---------------------------------------------------------------------------
# Tests — CLI round-trip via main([...])
# ---------------------------------------------------------------------------


class TestParseAcsCLI(unittest.TestCase):
    """CLI round-trip tests for parse-acs verb."""

    def test_real_fixture_exit_0(self):
        """parse-acs against the real fixture exits 0."""
        _, _, rc = _capture(["parse-acs", "--spec", _REAL_SPEC])
        self.assertEqual(rc, 0)

    def test_real_fixture_json_array(self):
        """parse-acs against the real fixture emits a non-empty JSON array."""
        out, _, rc = _capture(["parse-acs", "--spec", _REAL_SPEC])
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)

    def test_real_fixture_count_seven(self):
        """parse-acs emits exactly 7 ACs for the migration fixture."""
        out, _, rc = _capture(["parse-acs", "--spec", _REAL_SPEC])
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(len(data), 7)

    def test_real_fixture_has_required_keys(self):
        """Each dict in the output has id, text, checked, subsection."""
        out, _, rc = _capture(["parse-acs", "--spec", _REAL_SPEC])
        data = json.loads(out)
        for ac in data:
            for key in ("id", "text", "checked", "subsection"):
                self.assertIn(key, ac)

    def test_real_fixture_ac1_id(self):
        """First AC in CLI output is AC-1."""
        out, _, rc = _capture(["parse-acs", "--spec", _REAL_SPEC])
        data = json.loads(out)
        self.assertEqual(data[0]["id"], "AC-1")

    def test_missing_spec_flag(self):
        """Missing --spec causes non-zero exit (argparse error)."""
        _, _, rc = _capture(["parse-acs"])
        self.assertNotEqual(rc, 0)

    def test_nonexistent_spec_path(self):
        """Non-existent spec path → exit 0, empty JSON array."""
        out, _, rc = _capture(["parse-acs", "--spec", "/nonexistent/spec.md"])
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data, [])


# ---------------------------------------------------------------------------
# Tests — merge_ac_results (function level)
# ---------------------------------------------------------------------------

# The ac-verifier's ### Results table contract (from ac-verifier.md ## Output):
#
#   ### Results
#   | AC | Status | Evidence |
#   |----|--------|----------|
#   | AC-1 | PASS | Snapshot confirms [X] visible after [Y] |
#   | AC-2 | FAIL | Expected 201, got 400: [details] |
#   | AC-3 | MANUAL | Cannot verify — [reason] |
#   | AC-4 | PASS (code) | Implementation in [file:line] satisfies criterion |
#
# This fixture is constructed to match the exact contract in ac-verifier.md.
# It covers AC-1..AC-5 (AC-6 and AC-7 from the real fixture are left uncovered
# so the UNVERIFIED fallback can be tested).

_AGENT_REPORT_ALL_STATUSES = """\
## AC Verification Report

### Classification
| AC | Description | Category | Method |
|----|-------------|----------|--------|
| AC-1 | Desc1 | frontend | Chrome MCP |
| AC-2 | Desc2 | backend | curl |
| AC-3 | Desc3 | manual | N/A |
| AC-4 | Desc4 | code-fallback | Code reading |
| AC-5 | Desc5 | code-fallback | Code reading |

### Results
| AC | Status | Evidence |
|----|--------|----------|
| AC-1 | PASS | Snapshot confirms lerna absent from output |
| AC-2 | FAIL | Expected dist artifacts match, but dist/lib missing |
| AC-3 | MANUAL | Cannot verify — requires running CI environment |
| AC-4 | PASS (code) | Implementation in scripts/check.sh:14 satisfies criterion |
| AC-5 | PARTIAL (code) | AC-5 partly satisfied; pnpm hook not present |

### Summary
- Total AC items: 5
- Passed: 2
- Failed: 1
- Partial: 1
- Manual (cannot automate): 1
"""


class TestMergeAcResultsRealFixture(unittest.TestCase):
    """merge_ac_results round-trip against the real parse_acs output + an
    agent report fixture matching the ac-verifier.md Output contract.

    The parse_acs call uses the REAL specify-sample-migration.md fixture
    (AC-1..AC-7).  The agent report covers AC-1..AC-4 and AC-5 (PARTIAL code).
    AC-6 and AC-7 have no agent row → UNVERIFIED.
    """

    @classmethod
    def setUpClass(cls):
        # Parse the real fixture to get the structured AC list.
        cls.acs = parse_acs(_REAL_SPEC)
        # Use the agent report that covers AC-1..AC-5; AC-6 and AC-7 are left
        # uncovered to exercise the UNVERIFIED fallback.
        cls.merged = merge_ac_results(cls.acs, _AGENT_REPORT_ALL_STATUSES)

    def test_merged_count_matches_acs(self):
        """Merged list has the same count as the input AC list (7)."""
        self.assertEqual(len(self.merged), len(self.acs))
        self.assertEqual(len(self.merged), 7)

    def test_merged_ac1_pass(self):
        """AC-1 is PASS from the agent's Results table."""
        ac1 = self.merged[0]
        self.assertEqual(ac1["id"], "AC-1")
        self.assertEqual(ac1["status"], "PASS")
        self.assertIn("lerna", ac1["evidence"])

    def test_merged_ac2_fail(self):
        """AC-2 is FAIL with evidence from the agent's Results table."""
        ac2 = self.merged[1]
        self.assertEqual(ac2["id"], "AC-2")
        self.assertEqual(ac2["status"], "FAIL")
        self.assertTrue(len(ac2["evidence"]) > 0)

    def test_merged_ac3_manual(self):
        """AC-3 is MANUAL from the agent's Results table."""
        ac3 = self.merged[2]
        self.assertEqual(ac3["id"], "AC-3")
        self.assertEqual(ac3["status"], "MANUAL")

    def test_merged_ac4_pass_code(self):
        """AC-4 is PASS (code) — the code-reading fallback variant."""
        ac4 = self.merged[3]
        self.assertEqual(ac4["id"], "AC-4")
        self.assertEqual(ac4["status"], "PASS (code)")
        self.assertIn("scripts/check.sh", ac4["evidence"])

    def test_merged_ac5_partial_code(self):
        """AC-5 is PARTIAL (code) — from the second report fixture."""
        ac5 = self.merged[4]
        self.assertEqual(ac5["id"], "AC-5")
        self.assertEqual(ac5["status"], "PARTIAL (code)")

    def test_merged_ac6_unverified(self):
        """AC-6 has no agent row → UNVERIFIED with empty evidence."""
        ac6 = self.merged[5]
        self.assertEqual(ac6["id"], "AC-6")
        self.assertEqual(ac6["status"], "UNVERIFIED")
        self.assertEqual(ac6["evidence"], "")

    def test_merged_ac7_unverified(self):
        """AC-7 has no agent row → UNVERIFIED."""
        ac7 = self.merged[6]
        self.assertEqual(ac7["id"], "AC-7")
        self.assertEqual(ac7["status"], "UNVERIFIED")

    def test_merged_preserves_original_fields(self):
        """Each merged dict retains the original id/text/checked/subsection fields."""
        for orig, merged in zip(self.acs, self.merged):
            self.assertEqual(merged["id"], orig["id"])
            self.assertEqual(merged["text"], orig["text"])
            self.assertEqual(merged["checked"], orig["checked"])
            self.assertEqual(merged["subsection"], orig["subsection"])

    def test_merged_dict_shape(self):
        """Each merged dict has exactly the 6 expected keys."""
        expected_keys = {"id", "text", "checked", "subsection", "status", "evidence"}
        for item in self.merged:
            self.assertEqual(set(item.keys()), expected_keys)

    def test_input_acs_not_mutated(self):
        """The original parse_acs output is not mutated by the merge."""
        for orig in self.acs:
            self.assertNotIn("status", orig)
            self.assertNotIn("evidence", orig)


class TestMergeAcResultsEdgeCases(unittest.TestCase):
    """Edge cases for merge_ac_results."""

    def _simple_acs(self, ids):
        """Build a minimal parse_acs-shaped list for the given AC ids."""
        return [
            {"id": ac_id, "text": "Some text.", "checked": False, "subsection": "5.1 A"}
            for ac_id in ids
        ]

    def test_empty_acs_list(self):
        """Empty acs list → empty merged list."""
        result = merge_ac_results([], _AGENT_REPORT_ALL_STATUSES)
        self.assertEqual(result, [])

    def test_empty_report_all_unverified(self):
        """Empty agent report → all ACs are UNVERIFIED."""
        acs = self._simple_acs(["AC-1", "AC-2"])
        result = merge_ac_results(acs, "")
        self.assertEqual(len(result), 2)
        for item in result:
            self.assertEqual(item["status"], "UNVERIFIED")
            self.assertEqual(item["evidence"], "")

    def test_unknown_agent_rows_ignored(self):
        """Agent rows for AC ids not in acs are silently ignored."""
        acs = self._simple_acs(["AC-1"])
        # Report has AC-99 which is not in acs.
        report = (
            "### Results\n"
            "| AC | Status | Evidence |\n"
            "|----|--------|----------|\n"
            "| AC-99 | PASS | Some evidence |\n"
            "| AC-1 | FAIL | Evidence for AC-1 |\n"
        )
        result = merge_ac_results(acs, report)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], "AC-1")
        self.assertEqual(result[0]["status"], "FAIL")

    def test_partial_coverage_ac_without_row_is_unverified(self):
        """When the agent covers only some ACs, uncovered ones are UNVERIFIED."""
        acs = self._simple_acs(["AC-1", "AC-2", "AC-3"])
        report = (
            "### Results\n"
            "| AC | Status | Evidence |\n"
            "|----|--------|----------|\n"
            "| AC-2 | PASS | Evidence |\n"
        )
        result = merge_ac_results(acs, report)
        self.assertEqual(result[0]["id"], "AC-1")
        self.assertEqual(result[0]["status"], "UNVERIFIED")
        self.assertEqual(result[1]["id"], "AC-2")
        self.assertEqual(result[1]["status"], "PASS")
        self.assertEqual(result[2]["id"], "AC-3")
        self.assertEqual(result[2]["status"], "UNVERIFIED")

    def test_fail_code_variant(self):
        """FAIL (code) status is stored verbatim."""
        acs = self._simple_acs(["AC-1"])
        report = (
            "### Results\n"
            "| AC | Status | Evidence |\n"
            "|----|--------|----------|\n"
            "| AC-1 | FAIL (code) | Code reading shows path missing |\n"
        )
        result = merge_ac_results(acs, report)
        self.assertEqual(result[0]["status"], "FAIL (code)")

    def test_evidence_cell_stripped(self):
        """Evidence cell is stripped of leading/trailing whitespace."""
        acs = self._simple_acs(["AC-1"])
        report = (
            "### Results\n"
            "| AC | Status | Evidence |\n"
            "|----|--------|----------|\n"
            "| AC-1 | PASS |  Evidence with spaces  |\n"
        )
        result = merge_ac_results(acs, report)
        self.assertEqual(result[0]["evidence"], "Evidence with spaces")

    def test_no_results_section_all_unverified(self):
        """Report with no ### Results section → all ACs are UNVERIFIED."""
        acs = self._simple_acs(["AC-1", "AC-2"])
        report = "## AC Verification Report\n\n### Classification\n| AC | Desc | Cat | Method |\n"
        result = merge_ac_results(acs, report)
        for item in result:
            self.assertEqual(item["status"], "UNVERIFIED")

    def test_results_section_stops_at_next_heading(self):
        """Parser stops at the next ### heading after ### Results."""
        acs = self._simple_acs(["AC-1", "AC-2"])
        report = (
            "### Results\n"
            "| AC | Status | Evidence |\n"
            "|----|--------|----------|\n"
            "| AC-1 | PASS | Evidence |\n"
            "\n"
            "### Summary\n"
            "| AC-2 | FAIL | Should not be parsed as a data row |\n"
        )
        result = merge_ac_results(acs, report)
        self.assertEqual(result[0]["status"], "PASS")
        # AC-2 is in the Summary section (after the stop heading) → UNVERIFIED.
        self.assertEqual(result[1]["status"], "UNVERIFIED")

    def test_header_row_not_treated_as_data(self):
        """The ``| AC | Status | Evidence |`` header row is not treated as AC data."""
        acs = self._simple_acs(["AC-1"])
        report = (
            "### Results\n"
            "| AC | Status | Evidence |\n"
            "|----|--------|----------|\n"
            "| AC-1 | PASS | Ok |\n"
        )
        result = merge_ac_results(acs, report)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["status"], "PASS")


# ---------------------------------------------------------------------------
# Tests — merge-ac-results CLI verb
# ---------------------------------------------------------------------------


class TestMergeAcResultsCLI(unittest.TestCase):
    """CLI round-trip tests for the merge-ac-results verb."""

    @classmethod
    def setUpClass(cls):
        # Write parse_acs output from the real fixture to a temp JSON file.
        cls.acs_data = parse_acs(_REAL_SPEC)
        cls.tmp_dir = tempfile.mkdtemp()
        cls.acs_path = os.path.join(cls.tmp_dir, "acs.json")
        cls.report_path = os.path.join(cls.tmp_dir, "agent_report.md")
        with open(cls.acs_path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(cls.acs_data))
        # Write a minimal agent report covering AC-1.
        with open(cls.report_path, "w", encoding="utf-8") as fh:
            fh.write(
                "### Results\n"
                "| AC | Status | Evidence |\n"
                "|----|--------|----------|\n"
                "| AC-1 | PASS | Confirmed via snapshot |\n"
            )

    @classmethod
    def tearDownClass(cls):
        import shutil
        shutil.rmtree(cls.tmp_dir, ignore_errors=True)

    def test_exit_0_on_valid_inputs(self):
        _, _, rc = _capture([
            "merge-ac-results",
            "--acs", self.acs_path,
            "--agent-report", self.report_path,
        ])
        self.assertEqual(rc, 0)

    def test_emits_valid_json_array(self):
        out, _, rc = _capture([
            "merge-ac-results",
            "--acs", self.acs_path,
            "--agent-report", self.report_path,
        ])
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 7)

    def test_ac1_has_pass_status(self):
        out, _, rc = _capture([
            "merge-ac-results",
            "--acs", self.acs_path,
            "--agent-report", self.report_path,
        ])
        data = json.loads(out)
        ac1 = next(d for d in data if d["id"] == "AC-1")
        self.assertEqual(ac1["status"], "PASS")

    def test_ac2_is_unverified(self):
        """AC-2 is not in the agent report → UNVERIFIED."""
        out, _, _ = _capture([
            "merge-ac-results",
            "--acs", self.acs_path,
            "--agent-report", self.report_path,
        ])
        data = json.loads(out)
        ac2 = next(d for d in data if d["id"] == "AC-2")
        self.assertEqual(ac2["status"], "UNVERIFIED")

    def test_missing_acs_flag_exits_2(self):
        _, _, rc = _capture([
            "merge-ac-results",
            "--agent-report", self.report_path,
        ])
        self.assertNotEqual(rc, 0)

    def test_missing_agent_report_flag_exits_2(self):
        _, _, rc = _capture([
            "merge-ac-results",
            "--acs", self.acs_path,
        ])
        self.assertNotEqual(rc, 0)

    def test_unreadable_agent_report_produces_all_unverified(self):
        """Unreadable agent report → all ACs UNVERIFIED, exit 0."""
        out, err, rc = _capture([
            "merge-ac-results",
            "--acs", self.acs_path,
            "--agent-report", "/nonexistent/report.md",
        ])
        self.assertEqual(rc, 0)
        data = json.loads(out)
        for item in data:
            self.assertEqual(item["status"], "UNVERIFIED")

    def test_each_dict_has_six_keys(self):
        out, _, _ = _capture([
            "merge-ac-results",
            "--acs", self.acs_path,
            "--agent-report", self.report_path,
        ])
        data = json.loads(out)
        expected = {"id", "text", "checked", "subsection", "status", "evidence"}
        for item in data:
            self.assertEqual(set(item.keys()), expected)


if __name__ == "__main__":
    unittest.main()
