"""Tests for src/devforge/lib/_spec_check/_report.py.

Covers:
  - recommend_disposition: sat/unsat/unknown.
  - _atom_to_str / _constraint_to_str: every op, both bool values, both
    enum ops, assertion + implication.
  - render_report: UNSAT case, SAT case, nothing-formalized case, unknown
    case, an implication-present D9 reachability note, invalid disposition
    -> ValueError, the feature/date_str header, and the two coverage N/K
    scoping edge branches (uncovered row + ghost-entry non-inflation).
  - write_spec_check_report: file written, path returned, dir created,
    overwrite idempotent.
  - Plan 82 D4/OQ-2: the coverage line's third (J) term -- all four
    K>0/K==0 x J>0/J==0 combos, each pinned as an exact full-string match;
    the "## UNRESOLVED SUBJECTS" section (rendered / omitted); the
    "**Spec hash**" header line (rendered / omitted).
"""

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _spec_check._report import (  # noqa: E402
    SPEC_CHECK_DISPOSITIONS,
    _atom_to_str,
    _constraint_to_str,
    recommend_disposition,
    render_report,
    write_spec_check_report,
)
from _spec_check._solve import SolveResult  # noqa: E402
from _spec_check.ir_schema import (  # noqa: E402
    Atom,
    Constraint,
    Coverage,
    SpecCheckIR,
    SubjectResolution,
    Variable,
)


# ---------------------------------------------------------------------------
# Shared fixtures.
# ---------------------------------------------------------------------------

_FEATURE = "specs/001-widget"
_DATE = "2026-07-15"


def _acs():
    return [
        {
            "id": "AC-1",
            "text": "The response time shall be under 100ms.",
            "checked": False,
            "subsection": "5.1 Performance",
        },
        {
            "id": "AC-2",
            "text": "IF the user is an admin THEN the order state shall not be pending.",
            "checked": False,
            "subsection": "5.2 Orders",
        },
        {
            "id": "AC-3",
            "text": "The app shall feel responsive.",
            "checked": False,
            "subsection": "5.3 UX",
        },
    ]


def _ir_with_implication():
    variables = [
        Variable(name="response_ms", sort="Int", gloss="Response time in milliseconds"),
        Variable(name="is_admin", sort="Bool", gloss="Whether the current user has admin role"),
        Variable(
            name="order_state",
            sort="Enum",
            gloss="Current state of the order",
            domain=["pending", "shipped"],
        ),
    ]
    constraints = [
        Constraint(
            ac_id="AC-1",
            kind="assertion",
            consequent=[Atom(var="response_ms", op="<", value=100)],
        ),
        Constraint(
            ac_id="AC-2",
            kind="implication",
            antecedent=[Atom(var="is_admin", op="=", value=True)],
            consequent=[Atom(var="order_state", op="!=", value="pending")],
        ),
    ]
    coverage = [
        Coverage(ac_id="AC-1", status="formalized"),
        Coverage(ac_id="AC-2", status="formalized"),
        Coverage(ac_id="AC-3", status="skipped_prose", reason="vague, not measurable"),
    ]
    return SpecCheckIR(variables=variables, constraints=constraints, coverage=coverage)


def _ir_nothing_formalized():
    coverage = [
        Coverage(ac_id="AC-1", status="skipped_prose", reason="vague"),
        Coverage(ac_id="AC-2", status="skipped_unsupported", reason="multi-var arithmetic"),
        Coverage(ac_id="AC-3", status="skipped_prose", reason="vague"),
    ]
    return SpecCheckIR(variables=[], constraints=[], coverage=coverage)


# ---------------------------------------------------------------------------
# recommend_disposition
# ---------------------------------------------------------------------------


class TestRecommendDisposition(unittest.TestCase):
    def test_unsat_recommends_revise_spec(self):
        result = SolveResult(status="unsat", unsat_core=["AC-1", "AC-2"])
        self.assertEqual(recommend_disposition(result), "REVISE-SPEC")

    def test_sat_recommends_consistent(self):
        result = SolveResult(status="sat", unsat_core=[])
        self.assertEqual(recommend_disposition(result), "CONSISTENT")

    def test_unknown_recommends_consistent(self):
        result = SolveResult(status="unknown", unsat_core=[])
        self.assertEqual(recommend_disposition(result), "CONSISTENT")

    def test_never_returns_dismiss(self):
        for status in ("sat", "unsat", "unknown"):
            core = ["AC-1"] if status == "unsat" else []
            result = SolveResult(status=status, unsat_core=core)
            self.assertNotEqual(recommend_disposition(result), "DISMISS")


# ---------------------------------------------------------------------------
# _atom_to_str
# ---------------------------------------------------------------------------


class TestAtomToStr(unittest.TestCase):
    def test_numeric_lt(self):
        self.assertEqual(
            _atom_to_str(Atom(var="response_ms", op="<", value=100)),
            "response_ms < 100",
        )

    def test_numeric_le(self):
        self.assertEqual(
            _atom_to_str(Atom(var="x", op="<=", value=5)), "x <= 5"
        )

    def test_numeric_eq(self):
        self.assertEqual(
            _atom_to_str(Atom(var="x", op="=", value=5)), "x = 5"
        )

    def test_numeric_ne(self):
        self.assertEqual(
            _atom_to_str(Atom(var="x", op="!=", value=5)), "x != 5"
        )

    def test_numeric_gt(self):
        self.assertEqual(
            _atom_to_str(Atom(var="x", op=">", value=5)), "x > 5"
        )

    def test_numeric_ge(self):
        self.assertEqual(
            _atom_to_str(Atom(var="x", op=">=", value=5)), "x >= 5"
        )

    def test_bool_true(self):
        self.assertEqual(
            _atom_to_str(Atom(var="is_admin", op="=", value=True)), "is_admin"
        )

    def test_bool_false(self):
        self.assertEqual(
            _atom_to_str(Atom(var="is_admin", op="=", value=False)),
            "NOT is_admin",
        )

    def test_enum_eq(self):
        self.assertEqual(
            _atom_to_str(Atom(var="order_state", op="=", value="shipped")),
            "order_state = shipped",
        )

    def test_enum_ne(self):
        self.assertEqual(
            _atom_to_str(Atom(var="order_state", op="!=", value="pending")),
            "order_state != pending",
        )


# ---------------------------------------------------------------------------
# _constraint_to_str
# ---------------------------------------------------------------------------


class TestConstraintToStr(unittest.TestCase):
    def test_assertion_single_atom(self):
        c = Constraint(
            ac_id="AC-1",
            kind="assertion",
            consequent=[Atom(var="response_ms", op="<", value=100)],
        )
        self.assertEqual(_constraint_to_str(c), "response_ms < 100")

    def test_assertion_multi_atom_and_joined(self):
        c = Constraint(
            ac_id="AC-1",
            kind="assertion",
            consequent=[
                Atom(var="response_ms", op="<", value=100),
                Atom(var="is_admin", op="=", value=True),
            ],
        )
        self.assertEqual(
            _constraint_to_str(c), "response_ms < 100 AND is_admin"
        )

    def test_implication(self):
        c = Constraint(
            ac_id="AC-2",
            kind="implication",
            antecedent=[Atom(var="is_admin", op="=", value=True)],
            consequent=[Atom(var="order_state", op="!=", value="pending")],
        )
        self.assertEqual(
            _constraint_to_str(c),
            "IF is_admin THEN order_state != pending",
        )


# ---------------------------------------------------------------------------
# render_report
# ---------------------------------------------------------------------------


class TestRenderReportUnsat(unittest.TestCase):
    def setUp(self):
        self.ir = _ir_with_implication()
        self.acs = _acs()
        self.solve_result = SolveResult(status="unsat", unsat_core=["AC-1", "AC-2"])
        self.report = render_report(
            _FEATURE, _DATE, self.solve_result, self.ir, self.acs, "REVISE-SPEC"
        )

    def test_header_has_feature_and_date(self):
        self.assertIn("# Spec-Check: {0}".format(_FEATURE), self.report)
        self.assertIn("**Feature**: {0}".format(_FEATURE), self.report)
        self.assertIn("**Date**: {0}".format(_DATE), self.report)

    def test_d11_scope_line_verbatim(self):
        expected = (
            "> **Scope:** /devforge:spec-check is a consistency prover, not a "
            "mind-reader. It checks whether your acceptance criteria "
            "contradict *each other* -- not whether they are what you "
            "*meant*. A single coherent-but-wrong AC will pass."
        )
        self.assertIn(expected, self.report)

    def test_recommendation_section_names_core_acs(self):
        self.assertIn("## Recommendation", self.report)
        self.assertIn("REVISE-SPEC", self.report)
        self.assertIn("`AC-1`", self.report)
        self.assertIn("`AC-2`", self.report)

    def test_reading_section_has_variable_glosses(self):
        self.assertIn("## How your ACs were read as logic", self.report)
        self.assertIn("Response time in milliseconds", self.report)
        self.assertIn("Whether the current user has admin role", self.report)
        self.assertIn("Current state of the order", self.report)

    def test_reading_section_juxtaposes_original_and_logic(self):
        self.assertIn("AC-1", self.report)
        self.assertIn("The response time shall be under 100ms.", self.report)
        self.assertIn("response_ms < 100", self.report)
        self.assertIn("IF is_admin THEN order_state != pending", self.report)

    def test_contradiction_section_names_exactly_unsat_core(self):
        self.assertIn("## Contradiction", self.report)
        contradiction_section = self.report.split("## Contradiction", 1)[1]
        contradiction_section = contradiction_section.split("## Coverage", 1)[0]
        self.assertIn("AC-1", contradiction_section)
        self.assertIn("AC-2", contradiction_section)
        self.assertNotIn("AC-3", contradiction_section)

    def test_coverage_section_checked_n_of_m(self):
        self.assertIn("## Coverage", self.report)
        self.assertIn("Checked 2 of 3 acceptance criteria", self.report)
        self.assertIn("(1 unformalizable)", self.report)

    def test_reachability_note_present(self):
        self.assertIn(
            "conditional (IF/WHEN) acceptance criteria are checked under",
            self.report,
        )


class TestRenderReportSat(unittest.TestCase):
    def setUp(self):
        self.ir = _ir_with_implication()
        self.acs = _acs()
        self.solve_result = SolveResult(status="sat", unsat_core=[])
        self.report = render_report(
            _FEATURE, _DATE, self.solve_result, self.ir, self.acs, "CONSISTENT"
        )

    def test_recommends_consistent(self):
        self.assertIn("CONSISTENT", self.report)
        self.assertIn(
            "No contradiction found over the formalized subset.", self.report
        )

    def test_no_contradiction_section(self):
        self.assertNotIn("## Contradiction", self.report)

    def test_coverage_ledger_present(self):
        self.assertIn("## Coverage", self.report)
        self.assertIn("Checked 2 of 3 acceptance criteria", self.report)


class TestRenderReportNothingFormalized(unittest.TestCase):
    def test_consistent_with_nothing_formalized_reason(self):
        ir = _ir_nothing_formalized()
        acs = _acs()
        solve_result = SolveResult(status="sat", unsat_core=[])
        report = render_report(_FEATURE, _DATE, solve_result, ir, acs, "CONSISTENT")
        self.assertIn("CONSISTENT", report)
        self.assertIn("No formalizable logic found -- nothing was proven.", report)
        self.assertNotIn(
            "No contradiction found over the formalized subset.", report
        )
        self.assertNotIn("## Contradiction", report)


class TestRenderReportUnknown(unittest.TestCase):
    def test_unknown_caveat_line_present_no_contradiction(self):
        ir = _ir_with_implication()
        acs = _acs()
        solve_result = SolveResult(status="unknown", unsat_core=[])
        report = render_report(_FEATURE, _DATE, solve_result, ir, acs, "CONSISTENT")
        self.assertIn(
            "The solver could not decide (returned `unknown`); no "
            "contradiction was proven, but none was ruled out.",
            report,
        )
        self.assertNotIn("## Contradiction", report)


class TestRenderReportNoImplication(unittest.TestCase):
    def test_reachability_note_absent_without_implication(self):
        variables = [
            Variable(name="response_ms", sort="Int", gloss="Response time in ms"),
        ]
        constraints = [
            Constraint(
                ac_id="AC-1",
                kind="assertion",
                consequent=[Atom(var="response_ms", op="<", value=100)],
            )
        ]
        coverage = [
            Coverage(ac_id="AC-1", status="formalized"),
            Coverage(ac_id="AC-2", status="skipped_prose", reason="vague"),
            Coverage(ac_id="AC-3", status="skipped_prose", reason="vague"),
        ]
        ir = SpecCheckIR(variables=variables, constraints=constraints, coverage=coverage)
        solve_result = SolveResult(status="sat", unsat_core=[])
        report = render_report(_FEATURE, _DATE, solve_result, ir, _acs(), "CONSISTENT")
        self.assertNotIn(
            "conditional (IF/WHEN) acceptance criteria are checked under",
            report,
        )


class TestRenderReportCoverageEdges(unittest.TestCase):
    """F1 fix + F4 tests: coverage N/K counts scoped to acs, both edge
    branches (an AC with no Coverage entry; a Coverage entry not in acs)."""

    def test_coverage_uncovered_row_for_ac_with_no_entry(self):
        # AC-2 has no matching Coverage entry -> renders "uncovered" and
        # still counts toward M.
        acs = [
            {"id": "AC-1", "text": "The response time shall be under 100ms."},
            {"id": "AC-2", "text": "The order shall be logged."},
        ]
        variables = [
            Variable(name="response_ms", sort="Int", gloss="Response time in ms"),
        ]
        constraints = [
            Constraint(
                ac_id="AC-1",
                kind="assertion",
                consequent=[Atom(var="response_ms", op="<", value=100)],
            )
        ]
        coverage = [Coverage(ac_id="AC-1", status="formalized")]
        ir = SpecCheckIR(variables=variables, constraints=constraints, coverage=coverage)
        solve_result = SolveResult(status="sat", unsat_core=[])
        report = render_report(_FEATURE, _DATE, solve_result, ir, acs, "CONSISTENT")
        self.assertIn("- AC-2: uncovered", report)
        self.assertIn("Checked 1 of 2 acceptance criteria", report)

    def test_ghost_coverage_entry_not_in_acs_does_not_inflate_counts(self):
        # A Coverage entry (AC-99) whose ac_id is absent from acs must not
        # push N/K past M = len(acs). Repro from the finding: 1 AC + a
        # ghost AC-99 formalized coverage entry must NOT render
        # "Checked 2 of 1".
        acs = [{"id": "AC-1", "text": "The response time shall be under 100ms."}]
        variables = [
            Variable(name="response_ms", sort="Int", gloss="Response time in ms"),
        ]
        constraints = [
            Constraint(
                ac_id="AC-1",
                kind="assertion",
                consequent=[Atom(var="response_ms", op="<", value=100)],
            ),
            Constraint(
                ac_id="AC-99",
                kind="assertion",
                consequent=[Atom(var="response_ms", op=">", value=0)],
            ),
        ]
        coverage = [
            Coverage(ac_id="AC-1", status="formalized"),
            Coverage(ac_id="AC-99", status="formalized"),
        ]
        ir = SpecCheckIR(variables=variables, constraints=constraints, coverage=coverage)
        solve_result = SolveResult(status="sat", unsat_core=[])
        report = render_report(_FEATURE, _DATE, solve_result, ir, acs, "CONSISTENT")
        self.assertIn("Checked 1 of 1 acceptance criteria", report)
        self.assertNotIn("Checked 2 of 1", report)


class TestRenderReportInvalidDisposition(unittest.TestCase):
    def test_invalid_disposition_raises_value_error(self):
        ir = _ir_with_implication()
        solve_result = SolveResult(status="sat", unsat_core=[])
        with self.assertRaises(ValueError):
            render_report(
                _FEATURE, _DATE, solve_result, ir, _acs(), "NOT-A-REAL-DISPOSITION"
            )

    def test_all_valid_dispositions_accepted(self):
        # DISMISS is a legal render_report input (a human-supplied override)
        # even though recommend_disposition() never produces it.
        ir = _ir_with_implication()
        solve_result = SolveResult(status="sat", unsat_core=[])
        for disposition in SPEC_CHECK_DISPOSITIONS:
            report = render_report(
                _FEATURE, _DATE, solve_result, ir, _acs(), disposition
            )
            self.assertIn(disposition, report)


# ---------------------------------------------------------------------------
# write_spec_check_report
# ---------------------------------------------------------------------------


class TestWriteSpecCheckReport(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="spec-check-report-test-")
        self.addCleanup(shutil.rmtree, self.tmp_dir, ignore_errors=True)

    def test_writes_file_and_returns_path(self):
        feature_dir = os.path.join(self.tmp_dir, "specs", "001-widget")
        path = write_spec_check_report(feature_dir, "# hello\n")
        self.assertEqual(path, os.path.join(feature_dir, "spec-check.md"))
        self.assertTrue(os.path.isfile(path))
        with open(path, encoding="utf-8") as fh:
            self.assertEqual(fh.read(), "# hello\n")

    def test_creates_missing_feature_dir(self):
        feature_dir = os.path.join(self.tmp_dir, "does", "not", "exist", "yet")
        self.assertFalse(os.path.isdir(feature_dir))
        write_spec_check_report(feature_dir, "content")
        self.assertTrue(os.path.isdir(feature_dir))

    def test_overwrite_is_idempotent(self):
        feature_dir = os.path.join(self.tmp_dir, "specs", "002-gadget")
        write_spec_check_report(feature_dir, "first version\n")
        path = write_spec_check_report(feature_dir, "second version\n")
        with open(path, encoding="utf-8") as fh:
            self.assertEqual(fh.read(), "second version\n")

    def test_no_leftover_temp_files(self):
        feature_dir = os.path.join(self.tmp_dir, "specs", "003-thing")
        write_spec_check_report(feature_dir, "content\n")
        entries = os.listdir(feature_dir)
        self.assertEqual(entries, ["spec-check.md"])


# ---------------------------------------------------------------------------
# render_report -- D13 stability extension.
# ---------------------------------------------------------------------------


class TestRenderReportStability(unittest.TestCase):
    def test_no_stability_byte_identical_to_omitted_kwarg(self):
        # Pin back-compat: passing stability=None explicitly must render
        # byte-identical output to a call that never mentions the kwarg
        # at all (the pre-D13 call shape).
        ir = _ir_with_implication()
        acs = _acs()
        solve_result = SolveResult(status="sat", unsat_core=[])
        report_no_kwarg = render_report(
            _FEATURE, _DATE, solve_result, ir, acs, "CONSISTENT"
        )
        report_explicit_none = render_report(
            _FEATURE, _DATE, solve_result, ir, acs, "CONSISTENT", stability=None
        )
        self.assertEqual(report_no_kwarg, report_explicit_none)
        self.assertNotIn("Formalization stability", report_no_kwarg)
        self.assertNotIn("Formalization unstable", report_no_kwarg)

    def test_confirmed_unsat_stability_line_present(self):
        ir = _ir_with_implication()
        acs = _acs()
        solve_result = SolveResult(status="unsat", unsat_core=["AC-1", "AC-2"])
        stability = {"reproduced_in": 2, "of": 2, "verdict": "confirmed_unsat"}
        report = render_report(
            _FEATURE, _DATE, solve_result, ir, acs, "REVISE-SPEC",
            stability=stability,
        )
        self.assertIn(
            "**Formalization stability:** contradiction core reproduced "
            "in 2/2 formalization passes.",
            report,
        )
        self.assertNotIn("Formalization unstable", report)

    def test_unstable_caveat_present_and_recommendation_not_revise_spec(self):
        # Feed a synthesized sat solve-result (the D13 cry-wolf mapping) --
        # the recommendation must be CONSISTENT, never REVISE-SPEC, while
        # the unstable caveat is still surfaced.
        ir = _ir_with_implication()
        acs = _acs()
        solve_result = SolveResult(status="sat", unsat_core=[])
        stability = {"reproduced_in": 1, "of": 2, "verdict": "unstable"}
        report = render_report(
            _FEATURE, _DATE, solve_result, ir, acs, "CONSISTENT",
            stability=stability,
        )
        self.assertIn(
            "**Formalization unstable:** a contradiction appeared in some "
            "but not a majority of 1/2 passes -- NOT treated as "
            "confirmed; re-run `/devforge:spec-check` or inspect the "
            "formalization.",
            report,
        )
        self.assertNotIn("REVISE-SPEC", report)
        self.assertIn("CONSISTENT", report)
        self.assertNotIn("Formalization stability:", report)


# ---------------------------------------------------------------------------
# render_report -- Plan 82 D4/OQ-2 extension.
# ---------------------------------------------------------------------------


def _ir_one_ac_fully_formalized():
    """K==0, J==0: a single AC, formalized, nothing skipped/unresolved."""
    variables = [Variable(name="x", sort="Int", gloss="a count")]
    constraints = [
        Constraint(
            ac_id="AC-1",
            kind="assertion",
            consequent=[Atom(var="x", op="<", value=100)],
        )
    ]
    coverage = [Coverage(ac_id="AC-1", status="formalized")]
    return SpecCheckIR(variables=variables, constraints=constraints, coverage=coverage)


def _acs_one():
    return [{"id": "AC-1", "text": "The count shall be under 100."}]


def _ir_with_unresolved_subject_and_skip():
    """K>0, J>0: one formalized, one skipped_prose, one unresolved_subject."""
    variables = [
        Variable(name="response_ms", sort="Int", gloss="Response time in ms"),
        Variable(
            name="shipped_state",
            sort="Bool",
            gloss="order has shipped",
            subject_resolution=SubjectResolution(
                status="unresolved",
                searched="grepped 'shipped' and 'mark_shipped' across "
                "src/, 0 hits",
            ),
        ),
    ]
    constraints = [
        Constraint(
            ac_id="AC-1",
            kind="assertion",
            consequent=[Atom(var="response_ms", op="<", value=100)],
        ),
    ]
    coverage = [
        Coverage(ac_id="AC-1", status="formalized"),
        Coverage(ac_id="AC-2", status="unresolved_subject", subject="shipped_state"),
        Coverage(ac_id="AC-3", status="skipped_prose", reason="vague, not measurable"),
    ]
    return SpecCheckIR(variables=variables, constraints=constraints, coverage=coverage)


def _ir_with_unresolved_subject_no_skip():
    """K==0, J>0: one formalized, one unresolved_subject, zero skipped."""
    variables = [
        Variable(name="x", sort="Int", gloss="a count"),
        Variable(
            name="y",
            sort="Bool",
            gloss="a flag nothing constructs",
            subject_resolution=SubjectResolution(
                status="unresolved", searched="grepped src/, 0 hits"
            ),
        ),
    ]
    constraints = [
        Constraint(
            ac_id="AC-1",
            kind="assertion",
            consequent=[Atom(var="x", op="<", value=100)],
        ),
    ]
    coverage = [
        Coverage(ac_id="AC-1", status="formalized"),
        Coverage(ac_id="AC-2", status="unresolved_subject", subject="y"),
    ]
    return SpecCheckIR(variables=variables, constraints=constraints, coverage=coverage)


def _ir_with_two_unresolved_subjects():
    """K>0, J==2: pluralization pin fixture -- two DISTINCT unresolved
    subjects (not the same variable counted twice)."""
    variables = [
        Variable(name="x", sort="Int", gloss="a count"),
        Variable(
            name="y",
            sort="Bool",
            gloss="a flag nothing constructs",
            subject_resolution=SubjectResolution(
                status="unresolved", searched="grepped src/, 0 hits"
            ),
        ),
        Variable(
            name="z",
            sort="Bool",
            gloss="another flag nothing constructs",
            subject_resolution=SubjectResolution(
                status="unresolved", searched="grepped src/, 0 hits (z)"
            ),
        ),
    ]
    constraints = [
        Constraint(
            ac_id="AC-1",
            kind="assertion",
            consequent=[Atom(var="x", op="<", value=100)],
        ),
    ]
    coverage = [
        Coverage(ac_id="AC-1", status="formalized"),
        Coverage(ac_id="AC-2", status="unresolved_subject", subject="y"),
        Coverage(ac_id="AC-3", status="unresolved_subject", subject="z"),
        Coverage(ac_id="AC-4", status="skipped_prose", reason="vague"),
    ]
    return SpecCheckIR(variables=variables, constraints=constraints, coverage=coverage)


class TestCoverageLineFourCombos(unittest.TestCase):
    """Plan 82 D4: the coverage-line third (J) term, all four K>0/K==0 x
    J>0/J==0 combos, each pinned as an exact composed-line full-string
    match (not just substring pieces)."""

    def test_k_gt0_j_eq0_byte_identical_to_pre_d4_format(self):
        # Back-compat anchor: this is the SAME fixture/format the pre-D4
        # test_coverage_section_checked_n_of_m already pins piecewise --
        # here pinned as one exact composed string.
        ir = _ir_with_implication()
        acs = _acs()
        solve_result = SolveResult(status="unsat", unsat_core=["AC-1", "AC-2"])
        report = render_report(
            _FEATURE, _DATE, solve_result, ir, acs, "REVISE-SPEC"
        )
        self.assertIn(
            "**Checked 2 of 3 acceptance criteria** (1 unformalizable).",
            report,
        )
        self.assertNotIn("unresolved subjects", report)

    def test_k_eq0_j_eq0(self):
        ir = _ir_one_ac_fully_formalized()
        acs = _acs_one()
        solve_result = SolveResult(status="sat", unsat_core=[])
        report = render_report(_FEATURE, _DATE, solve_result, ir, acs, "CONSISTENT")
        self.assertIn(
            "**Checked 1 of 1 acceptance criteria** (0 unformalizable).",
            report,
        )
        self.assertNotIn("unresolved subjects", report)

    def test_k_gt0_j_eq1_singular(self):
        # J==1 pins the SINGULAR "unresolved subject" (nit fix) -- not
        # "unresolved subjects".
        ir = _ir_with_unresolved_subject_and_skip()
        acs = _acs()
        solve_result = SolveResult(status="sat", unsat_core=[])
        report = render_report(_FEATURE, _DATE, solve_result, ir, acs, "CONSISTENT")
        self.assertIn(
            "**Checked 1 of 3 acceptance criteria** (1 unformalizable; "
            "1 unresolved subject).",
            report,
        )
        self.assertNotIn("1 unresolved subjects)", report)

    def test_k_eq0_j_eq1_singular(self):
        ir = _ir_with_unresolved_subject_no_skip()
        acs = [
            {"id": "AC-1", "text": "The count shall be under 100."},
            {"id": "AC-2", "text": "The flag shall not be set."},
        ]
        solve_result = SolveResult(status="sat", unsat_core=[])
        report = render_report(_FEATURE, _DATE, solve_result, ir, acs, "CONSISTENT")
        self.assertIn(
            "**Checked 1 of 2 acceptance criteria** (0 unformalizable; "
            "1 unresolved subject).",
            report,
        )
        self.assertNotIn("1 unresolved subjects)", report)

    def test_k_gt0_j_gt1_plural(self):
        # J>1 pins the PLURAL "unresolved subjects" -- the nit fix must
        # not over-correct into always-singular.
        ir = _ir_with_two_unresolved_subjects()
        acs = [
            {"id": "AC-1", "text": "t1"},
            {"id": "AC-2", "text": "t2"},
            {"id": "AC-3", "text": "t3"},
            {"id": "AC-4", "text": "t4"},
        ]
        solve_result = SolveResult(status="sat", unsat_core=[])
        report = render_report(_FEATURE, _DATE, solve_result, ir, acs, "CONSISTENT")
        self.assertIn(
            "**Checked 1 of 4 acceptance criteria** (1 unformalizable; "
            "2 unresolved subjects).",
            report,
        )

    def test_unresolved_subject_row_shows_subject_name(self):
        ir = _ir_with_unresolved_subject_and_skip()
        acs = _acs()
        solve_result = SolveResult(status="sat", unsat_core=[])
        report = render_report(_FEATURE, _DATE, solve_result, ir, acs, "CONSISTENT")
        self.assertIn(
            "- AC-2: unresolved_subject (subject: shipped_state)", report
        )


class TestRenderReportUnresolvedSubjectsSection(unittest.TestCase):
    """Plan 82 D4: the '## UNRESOLVED SUBJECTS' section -- rendered only
    when unresolved_subjects is a non-empty list; placed right after
    Recommendation, before 'How your ACs were read'."""

    def _base_call(self, unresolved_subjects):
        ir = _ir_with_implication()
        acs = _acs()
        solve_result = SolveResult(status="sat", unsat_core=[])
        return render_report(
            _FEATURE,
            _DATE,
            solve_result,
            ir,
            acs,
            "CONSISTENT",
            unresolved_subjects=unresolved_subjects,
        )

    def test_omitted_renders_nothing_extra_byte_identical(self):
        report_no_kwarg = render_report(
            _FEATURE, _DATE, SolveResult(status="sat", unsat_core=[]),
            _ir_with_implication(), _acs(), "CONSISTENT",
        )
        report_explicit_none = self._base_call(None)
        report_explicit_empty = self._base_call([])
        self.assertEqual(report_no_kwarg, report_explicit_none)
        self.assertEqual(report_no_kwarg, report_explicit_empty)
        self.assertNotIn("## UNRESOLVED SUBJECTS", report_no_kwarg)

    def test_non_empty_renders_section_with_variable_gloss_and_ac_ids(self):
        unresolved = [
            {
                "variable": "shipped_state",
                "gloss": "order has shipped",
                "ac_ids": ["AC-4", "AC-9"],
                "passes": [
                    {
                        "pass": 1,
                        "outcome": "unresolved",
                        "searched": "grepped 'shipped', 0 hits",
                        "citation_error": None,
                    },
                    {
                        "pass": 2,
                        "outcome": "citation_failed",
                        "searched": None,
                        "citation_error": (
                            "variable 'shipped_state': cited file "
                            "'src/missing.py' does not exist under "
                            "workspace root"
                        ),
                    },
                ],
            }
        ]
        report = self._base_call(unresolved)
        self.assertIn("## UNRESOLVED SUBJECTS", report)
        self.assertIn("shipped_state", report)
        self.assertIn("order has shipped", report)
        self.assertIn("`AC-4`", report)
        self.assertIn("`AC-9`", report)
        self.assertIn(
            "pass 1: searched -- grepped 'shipped', 0 hits", report
        )
        self.assertIn(
            "pass 2: claimed resolved, but the citation check failed -- "
            "variable 'shipped_state': cited file 'src/missing.py' does "
            "not exist under workspace root",
            report,
        )

    def test_section_placed_right_after_recommendation_before_reading(self):
        unresolved = [
            {
                "variable": "z",
                "gloss": "g",
                "ac_ids": [],
                "passes": [
                    {
                        "pass": 1,
                        "outcome": "unresolved",
                        "searched": "s",
                        "citation_error": None,
                    }
                ],
            }
        ]
        report = self._base_call(unresolved)
        rec_idx = report.index("## Recommendation")
        unresolved_idx = report.index("## UNRESOLVED SUBJECTS")
        reading_idx = report.index("## How your ACs were read as logic")
        self.assertLess(rec_idx, unresolved_idx)
        self.assertLess(unresolved_idx, reading_idx)

    def test_empty_ac_ids_renders_none_named(self):
        unresolved = [
            {
                "variable": "z",
                "gloss": "g",
                "ac_ids": [],
                "passes": [
                    {
                        "pass": 1,
                        "outcome": "unresolved",
                        "searched": "s",
                        "citation_error": None,
                    }
                ],
            }
        ]
        report = self._base_call(unresolved)
        self.assertIn("(none named)", report)


class TestRenderReportSpecHash(unittest.TestCase):
    """Plan 82 OQ-2: the '**Spec hash**' header line."""

    _HASH = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

    def test_omitted_renders_nothing_extra_byte_identical(self):
        ir = _ir_with_implication()
        acs = _acs()
        solve_result = SolveResult(status="sat", unsat_core=[])
        report_no_kwarg = render_report(
            _FEATURE, _DATE, solve_result, ir, acs, "CONSISTENT"
        )
        report_explicit_none = render_report(
            _FEATURE, _DATE, solve_result, ir, acs, "CONSISTENT", spec_sha256=None
        )
        self.assertEqual(report_no_kwarg, report_explicit_none)
        self.assertNotIn("**Spec hash**", report_no_kwarg)

    def test_given_hash_renders_greppable_header_line(self):
        ir = _ir_with_implication()
        acs = _acs()
        solve_result = SolveResult(status="sat", unsat_core=[])
        report = render_report(
            _FEATURE, _DATE, solve_result, ir, acs, "CONSISTENT",
            spec_sha256=self._HASH,
        )
        self.assertIn("**Spec hash**: {0}".format(self._HASH), report)
        # Positioned in the header, after **Date** and before the scope
        # line.
        date_idx = report.index("**Date**:")
        hash_idx = report.index("**Spec hash**:")
        scope_idx = report.index("> **Scope:**")
        self.assertLess(date_idx, hash_idx)
        self.assertLess(hash_idx, scope_idx)


if __name__ == "__main__":
    unittest.main()
