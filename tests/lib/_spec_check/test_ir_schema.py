"""Tests for src/devforge/lib/_spec_check/ir_schema.py.

Coverage, per dataclass:
- Variable: happy path (each sort), name/gloss empty, bad sort, Enum without
  domain, non-Enum with domain, domain with dupes, domain with empty member,
  subject_resolution wrong type / happy attach.
- Atom: happy path (numeric/bool/enum-shaped), var empty, bad op, bad value
  type.
- Constraint: happy path (assertion/implication), ac_id empty, bad kind,
  empty consequent, non-Atom consequent element, assertion-with-antecedent,
  implication-without-antecedent, implication-with-empty-antecedent.
- Coverage: happy path (all four statuses), ac_id empty, bad status,
  skipped-without-reason, formalized-with-reason, formalized-reason-bad-type,
  unresolved_subject subject-required/must-be-None-otherwise.
- SubjectResolution: happy path (resolved/code, resolved/spec, unresolved),
  bad status, resolved-without-arm, resolved-without-citation,
  resolved-without-note, code-without-locator, spec-with-locator,
  resolved-with-searched, unresolved-with-any-of-arm/citation/locator/note,
  unresolved-without-searched.
- SpecCheckIR: happy path (incl. all-empty and all-skipped/zero-constraints),
  wrong-element-type per list.
- Module constants exported correctly.
"""

import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _spec_check.ir_schema import (  # noqa: E402
    COMPARISON_OPS,
    CONSTRAINT_KINDS,
    COVERAGE_STATUSES,
    SORTS,
    SUBJECT_RESOLUTION_ARMS,
    SUBJECT_RESOLUTION_STATUSES,
    Atom,
    Constraint,
    Coverage,
    SpecCheckIR,
    SubjectResolution,
    Variable,
)


# ---------------------------------------------------------------------------
# Module-level constants.
# ---------------------------------------------------------------------------

class TestModuleConstants(unittest.TestCase):

    def test_sorts_tuple(self):
        self.assertIsInstance(SORTS, tuple)
        self.assertEqual(SORTS, ("Int", "Real", "Bool", "Enum"))

    def test_comparison_ops_tuple(self):
        self.assertIsInstance(COMPARISON_OPS, tuple)
        self.assertEqual(COMPARISON_OPS, ("<", "<=", "=", "!=", ">", ">="))

    def test_constraint_kinds_tuple(self):
        self.assertIsInstance(CONSTRAINT_KINDS, tuple)
        self.assertEqual(CONSTRAINT_KINDS, ("assertion", "implication"))

    def test_coverage_statuses_tuple(self):
        self.assertIsInstance(COVERAGE_STATUSES, tuple)
        self.assertEqual(
            COVERAGE_STATUSES,
            (
                "formalized",
                "skipped_prose",
                "skipped_unsupported",
                "unresolved_subject",
            ),
        )

    def test_subject_resolution_statuses_tuple(self):
        self.assertIsInstance(SUBJECT_RESOLUTION_STATUSES, tuple)
        self.assertEqual(SUBJECT_RESOLUTION_STATUSES, ("resolved", "unresolved"))

    def test_subject_resolution_arms_tuple(self):
        self.assertIsInstance(SUBJECT_RESOLUTION_ARMS, tuple)
        self.assertEqual(SUBJECT_RESOLUTION_ARMS, ("code", "spec"))


# ---------------------------------------------------------------------------
# Builder helpers.
# ---------------------------------------------------------------------------

def _make_variable(**overrides):
    defaults = dict(
        name="response_ms",
        sort="Int",
        gloss="Response time in milliseconds.",
        domain=None,
    )
    defaults.update(overrides)
    return Variable(**defaults)


def _make_atom(**overrides):
    defaults = dict(var="response_ms", op="<", value=100)
    defaults.update(overrides)
    return Atom(**defaults)


def _make_constraint(**overrides):
    defaults = dict(
        ac_id="AC-1",
        kind="assertion",
        consequent=[_make_atom()],
        antecedent=None,
    )
    defaults.update(overrides)
    return Constraint(**defaults)


def _make_coverage(**overrides):
    defaults = dict(ac_id="AC-1", status="formalized", reason=None, subject=None)
    defaults.update(overrides)
    return Coverage(**defaults)


def _make_subject_resolution_code(**overrides):
    defaults = dict(
        status="resolved",
        arm="code",
        citation="src/widget.py",
        locator="def build_widget",
        note="Constructed at widget.py's build_widget factory.",
        searched=None,
    )
    defaults.update(overrides)
    return SubjectResolution(**defaults)


def _make_subject_resolution_spec(**overrides):
    defaults = dict(
        status="resolved",
        arm="spec",
        citation="AC-3",
        locator=None,
        note="AC-3 introduces the shipped state as new behavior.",
        searched=None,
    )
    defaults.update(overrides)
    return SubjectResolution(**defaults)


def _make_subject_resolution_unresolved(**overrides):
    defaults = dict(
        status="unresolved",
        arm=None,
        citation=None,
        locator=None,
        note=None,
        searched="grepped 'widget' and 'build_widget' across src/, 0 hits.",
    )
    defaults.update(overrides)
    return SubjectResolution(**defaults)


# ---------------------------------------------------------------------------
# Variable.
# ---------------------------------------------------------------------------

class TestVariableHappyPath(unittest.TestCase):

    def test_int_sort_no_domain(self):
        v = _make_variable(sort="Int", domain=None)
        self.assertEqual(v.sort, "Int")
        self.assertIsNone(v.domain)

    def test_real_sort_no_domain(self):
        v = _make_variable(name="latency", sort="Real", gloss="Latency in seconds.")
        self.assertEqual(v.sort, "Real")

    def test_bool_sort_no_domain(self):
        v = _make_variable(name="is_admin", sort="Bool", gloss="Whether the actor is an admin.")
        self.assertEqual(v.sort, "Bool")

    def test_enum_sort_with_domain(self):
        v = _make_variable(
            name="order_state",
            sort="Enum",
            gloss="Order lifecycle state.",
            domain=["pending", "paid", "shipped"],
        )
        self.assertEqual(v.sort, "Enum")
        self.assertEqual(v.domain, ["pending", "paid", "shipped"])

    def test_enum_domain_single_member(self):
        v = _make_variable(sort="Enum", domain=["only"])
        self.assertEqual(v.domain, ["only"])


class TestVariableValidation(unittest.TestCase):

    def test_name_empty_raises(self):
        with self.assertRaises(ValueError) as ctx:
            _make_variable(name="")
        self.assertIn("name", str(ctx.exception))

    def test_name_wrong_type_raises(self):
        with self.assertRaises(ValueError):
            _make_variable(name=None)  # type: ignore[arg-type]

    def test_bad_sort_raises(self):
        with self.assertRaises(ValueError) as ctx:
            _make_variable(sort="String")
        self.assertIn("sort", str(ctx.exception))

    def test_gloss_empty_raises(self):
        with self.assertRaises(ValueError) as ctx:
            _make_variable(gloss="")
        self.assertIn("gloss", str(ctx.exception))

    def test_gloss_whitespace_only_raises(self):
        with self.assertRaises(ValueError):
            _make_variable(gloss="   ")

    def test_enum_without_domain_raises(self):
        with self.assertRaises(ValueError) as ctx:
            _make_variable(sort="Enum", domain=None)
        self.assertIn("domain", str(ctx.exception))

    def test_enum_empty_domain_list_raises(self):
        with self.assertRaises(ValueError):
            _make_variable(sort="Enum", domain=[])

    def test_non_enum_with_domain_raises_int(self):
        with self.assertRaises(ValueError) as ctx:
            _make_variable(sort="Int", domain=["a", "b"])
        self.assertIn("domain", str(ctx.exception))

    def test_non_enum_with_domain_raises_bool(self):
        with self.assertRaises(ValueError):
            _make_variable(sort="Bool", domain=["a"])

    def test_non_enum_with_domain_raises_real(self):
        with self.assertRaises(ValueError):
            _make_variable(sort="Real", domain=["a"])

    def test_domain_with_dupes_raises(self):
        with self.assertRaises(ValueError) as ctx:
            _make_variable(sort="Enum", domain=["a", "b", "a"])
        self.assertIn("duplicate", str(ctx.exception))

    def test_domain_non_list_raises(self):
        with self.assertRaises(ValueError):
            _make_variable(sort="Enum", domain="a,b")  # type: ignore[arg-type]

    def test_domain_member_wrong_type_raises(self):
        with self.assertRaises(ValueError) as ctx:
            _make_variable(sort="Enum", domain=["a", 1])  # type: ignore[list-item]
        self.assertIn("domain[1]", str(ctx.exception))

    def test_domain_member_empty_string_raises(self):
        with self.assertRaises(ValueError) as ctx:
            _make_variable(sort="Enum", domain=["a", ""])
        self.assertIn("domain[1]", str(ctx.exception))

    def test_subject_resolution_defaults_to_none(self):
        v = _make_variable()
        self.assertIsNone(v.subject_resolution)

    def test_subject_resolution_code_attaches(self):
        sr = _make_subject_resolution_code()
        v = _make_variable(subject_resolution=sr)
        self.assertIs(v.subject_resolution, sr)

    def test_subject_resolution_spec_attaches(self):
        sr = _make_subject_resolution_spec()
        v = _make_variable(subject_resolution=sr)
        self.assertIs(v.subject_resolution, sr)

    def test_subject_resolution_unresolved_attaches(self):
        sr = _make_subject_resolution_unresolved()
        v = _make_variable(subject_resolution=sr)
        self.assertIs(v.subject_resolution, sr)

    def test_subject_resolution_wrong_type_raises(self):
        with self.assertRaises(ValueError) as ctx:
            _make_variable(subject_resolution={"status": "resolved"})  # type: ignore[arg-type]
        self.assertIn("subject_resolution", str(ctx.exception))


# ---------------------------------------------------------------------------
# SubjectResolution.
# ---------------------------------------------------------------------------

class TestSubjectResolutionHappyPath(unittest.TestCase):

    def test_resolved_code_arm(self):
        sr = _make_subject_resolution_code()
        self.assertEqual(sr.status, "resolved")
        self.assertEqual(sr.arm, "code")
        self.assertEqual(sr.citation, "src/widget.py")
        self.assertEqual(sr.locator, "def build_widget")
        self.assertIsNone(sr.searched)

    def test_resolved_spec_arm(self):
        sr = _make_subject_resolution_spec()
        self.assertEqual(sr.status, "resolved")
        self.assertEqual(sr.arm, "spec")
        self.assertEqual(sr.citation, "AC-3")
        self.assertIsNone(sr.locator)

    def test_unresolved(self):
        sr = _make_subject_resolution_unresolved()
        self.assertEqual(sr.status, "unresolved")
        self.assertIsNone(sr.arm)
        self.assertIsNone(sr.citation)
        self.assertIsNone(sr.locator)
        self.assertIsNone(sr.note)
        self.assertIn("grepped", sr.searched)


class TestSubjectResolutionValidation(unittest.TestCase):

    def test_bad_status_raises(self):
        with self.assertRaises(ValueError) as ctx:
            _make_subject_resolution_unresolved(status="bogus")
        self.assertIn("status", str(ctx.exception))

    def test_resolved_without_arm_raises(self):
        with self.assertRaises(ValueError) as ctx:
            _make_subject_resolution_code(arm=None)
        self.assertIn("arm", str(ctx.exception))

    def test_resolved_bad_arm_raises(self):
        with self.assertRaises(ValueError) as ctx:
            _make_subject_resolution_code(arm="bogus")
        self.assertIn("arm", str(ctx.exception))

    def test_resolved_without_citation_raises(self):
        with self.assertRaises(ValueError) as ctx:
            _make_subject_resolution_code(citation=None)
        self.assertIn("citation", str(ctx.exception))

    def test_resolved_without_note_raises(self):
        with self.assertRaises(ValueError) as ctx:
            _make_subject_resolution_code(note=None)
        self.assertIn("note", str(ctx.exception))

    def test_code_arm_without_locator_raises(self):
        with self.assertRaises(ValueError) as ctx:
            _make_subject_resolution_code(locator=None)
        self.assertIn("locator", str(ctx.exception))

    def test_spec_arm_with_locator_raises(self):
        with self.assertRaises(ValueError) as ctx:
            _make_subject_resolution_spec(locator="line 12")
        self.assertIn("locator", str(ctx.exception))

    def test_resolved_with_searched_raises(self):
        with self.assertRaises(ValueError) as ctx:
            _make_subject_resolution_code(searched="looked around")
        self.assertIn("searched", str(ctx.exception))

    def test_unresolved_with_arm_raises(self):
        with self.assertRaises(ValueError) as ctx:
            _make_subject_resolution_unresolved(arm="code")
        self.assertIn("arm", str(ctx.exception))

    def test_unresolved_with_citation_raises(self):
        with self.assertRaises(ValueError) as ctx:
            _make_subject_resolution_unresolved(citation="src/widget.py")
        self.assertIn("citation", str(ctx.exception))

    def test_unresolved_with_locator_raises(self):
        with self.assertRaises(ValueError) as ctx:
            _make_subject_resolution_unresolved(locator="line 12")
        self.assertIn("locator", str(ctx.exception))

    def test_unresolved_with_note_raises(self):
        with self.assertRaises(ValueError) as ctx:
            _make_subject_resolution_unresolved(note="found it")
        self.assertIn("note", str(ctx.exception))

    def test_unresolved_without_searched_raises(self):
        with self.assertRaises(ValueError) as ctx:
            _make_subject_resolution_unresolved(searched=None)
        self.assertIn("searched", str(ctx.exception))

    def test_unresolved_empty_searched_raises(self):
        with self.assertRaises(ValueError):
            _make_subject_resolution_unresolved(searched="")


# ---------------------------------------------------------------------------
# Atom.
# ---------------------------------------------------------------------------

class TestAtomHappyPath(unittest.TestCase):

    def test_numeric_int_comparison(self):
        a = _make_atom(var="response_ms", op="<", value=100)
        self.assertEqual(a.value, 100)

    def test_numeric_float_comparison(self):
        a = _make_atom(var="latency", op=">=", value=1.5)
        self.assertEqual(a.value, 1.5)

    def test_bool_true(self):
        a = _make_atom(var="is_admin", op="=", value=True)
        self.assertIs(a.value, True)

    def test_bool_false(self):
        a = _make_atom(var="is_admin", op="=", value=False)
        self.assertIs(a.value, False)

    def test_enum_equals(self):
        a = _make_atom(var="order_state", op="=", value="shipped")
        self.assertEqual(a.value, "shipped")

    def test_enum_not_equals(self):
        a = _make_atom(var="order_state", op="!=", value="pending")
        self.assertEqual(a.value, "pending")

    def test_all_comparison_ops_accepted(self):
        for op in COMPARISON_OPS:
            with self.subTest(op=op):
                a = _make_atom(op=op, value=5)
                self.assertEqual(a.op, op)


class TestAtomValidation(unittest.TestCase):

    def test_var_empty_raises(self):
        with self.assertRaises(ValueError) as ctx:
            _make_atom(var="")
        self.assertIn("var", str(ctx.exception))

    def test_var_wrong_type_raises(self):
        with self.assertRaises(ValueError):
            _make_atom(var=None)  # type: ignore[arg-type]

    def test_bad_op_raises(self):
        with self.assertRaises(ValueError) as ctx:
            _make_atom(op="==")
        self.assertIn("op", str(ctx.exception))

    def test_bad_value_type_none_raises(self):
        with self.assertRaises(ValueError) as ctx:
            _make_atom(value=None)  # type: ignore[arg-type]
        self.assertIn("value", str(ctx.exception))

    def test_bad_value_type_list_raises(self):
        with self.assertRaises(ValueError):
            _make_atom(value=[1, 2])  # type: ignore[arg-type]

    def test_bad_value_type_dict_raises(self):
        with self.assertRaises(ValueError):
            _make_atom(value={"a": 1})  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Constraint.
# ---------------------------------------------------------------------------

class TestConstraintHappyPath(unittest.TestCase):

    def test_assertion_no_antecedent(self):
        c = _make_constraint(kind="assertion", consequent=[_make_atom()], antecedent=None)
        self.assertEqual(c.kind, "assertion")
        self.assertIsNone(c.antecedent)

    def test_assertion_empty_antecedent_list_ok(self):
        c = _make_constraint(kind="assertion", consequent=[_make_atom()], antecedent=[])
        self.assertEqual(c.antecedent, [])

    def test_assertion_multi_atom_consequent(self):
        c = _make_constraint(
            kind="assertion",
            consequent=[_make_atom(var="a", value=1), _make_atom(var="b", value=2)],
        )
        self.assertEqual(len(c.consequent), 2)

    def test_implication_with_antecedent(self):
        c = _make_constraint(
            kind="implication",
            consequent=[_make_atom(var="is_admin", op="=", value=True)],
            antecedent=[_make_atom(var="can_delete", op="=", value=True)],
        )
        self.assertEqual(c.kind, "implication")
        self.assertEqual(len(c.antecedent), 1)


class TestConstraintValidation(unittest.TestCase):

    def test_ac_id_empty_raises(self):
        with self.assertRaises(ValueError) as ctx:
            _make_constraint(ac_id="")
        self.assertIn("ac_id", str(ctx.exception))

    def test_bad_kind_raises(self):
        with self.assertRaises(ValueError) as ctx:
            _make_constraint(kind="bogus")
        self.assertIn("kind", str(ctx.exception))

    def test_empty_consequent_raises(self):
        with self.assertRaises(ValueError) as ctx:
            _make_constraint(consequent=[])
        self.assertIn("consequent", str(ctx.exception))

    def test_consequent_non_atom_element_raises(self):
        with self.assertRaises(ValueError) as ctx:
            _make_constraint(consequent=[_make_atom(), "not an atom"])  # type: ignore[list-item]
        self.assertIn("consequent[1]", str(ctx.exception))

    def test_consequent_non_list_raises(self):
        with self.assertRaises(ValueError):
            _make_constraint(consequent=_make_atom())  # type: ignore[arg-type]

    def test_assertion_with_nonempty_antecedent_raises(self):
        with self.assertRaises(ValueError) as ctx:
            _make_constraint(kind="assertion", antecedent=[_make_atom()])
        self.assertIn("antecedent", str(ctx.exception))

    def test_implication_without_antecedent_raises(self):
        with self.assertRaises(ValueError) as ctx:
            _make_constraint(kind="implication", antecedent=None)
        self.assertIn("antecedent", str(ctx.exception))

    def test_implication_with_empty_antecedent_raises(self):
        with self.assertRaises(ValueError) as ctx:
            _make_constraint(kind="implication", antecedent=[])
        self.assertIn("antecedent", str(ctx.exception))

    def test_implication_antecedent_non_atom_element_raises(self):
        with self.assertRaises(ValueError) as ctx:
            _make_constraint(
                kind="implication",
                antecedent=["not an atom"],  # type: ignore[list-item]
            )
        self.assertIn("antecedent[0]", str(ctx.exception))


# ---------------------------------------------------------------------------
# Coverage.
# ---------------------------------------------------------------------------

class TestCoverageHappyPath(unittest.TestCase):

    def test_formalized_no_reason(self):
        c = _make_coverage(status="formalized", reason=None)
        self.assertEqual(c.status, "formalized")
        self.assertIsNone(c.reason)

    def test_formalized_with_reason(self):
        c = _make_coverage(status="formalized", reason="Directly modeled as an assertion.")
        self.assertEqual(c.reason, "Directly modeled as an assertion.")

    def test_skipped_prose_with_reason(self):
        c = _make_coverage(status="skipped_prose", reason="Purely descriptive, no testable condition.")
        self.assertEqual(c.status, "skipped_prose")

    def test_skipped_unsupported_with_reason(self):
        c = _make_coverage(
            status="skipped_unsupported",
            reason="References an external time-series constraint outside v1 sorts.",
        )
        self.assertEqual(c.status, "skipped_unsupported")

    def test_unresolved_subject_with_subject(self):
        c = _make_coverage(status="unresolved_subject", subject="shipped_state")
        self.assertEqual(c.status, "unresolved_subject")
        self.assertEqual(c.subject, "shipped_state")

    def test_unresolved_subject_with_subject_and_reason(self):
        c = _make_coverage(
            status="unresolved_subject",
            subject="shipped_state",
            reason="no construction site found",
        )
        self.assertEqual(c.reason, "no construction site found")


class TestCoverageValidation(unittest.TestCase):

    def test_ac_id_empty_raises(self):
        with self.assertRaises(ValueError) as ctx:
            _make_coverage(ac_id="")
        self.assertIn("ac_id", str(ctx.exception))

    def test_bad_status_raises(self):
        with self.assertRaises(ValueError) as ctx:
            _make_coverage(status="bogus")
        self.assertIn("status", str(ctx.exception))

    def test_skipped_prose_without_reason_raises(self):
        with self.assertRaises(ValueError) as ctx:
            _make_coverage(status="skipped_prose", reason=None)
        self.assertIn("reason", str(ctx.exception))

    def test_skipped_unsupported_without_reason_raises(self):
        with self.assertRaises(ValueError) as ctx:
            _make_coverage(status="skipped_unsupported", reason=None)
        self.assertIn("reason", str(ctx.exception))

    def test_skipped_prose_empty_reason_raises(self):
        with self.assertRaises(ValueError):
            _make_coverage(status="skipped_prose", reason="")

    def test_formalized_reason_bad_type_raises(self):
        with self.assertRaises(ValueError) as ctx:
            _make_coverage(status="formalized", reason=42)  # type: ignore[arg-type]
        self.assertIn("reason", str(ctx.exception))

    def test_unresolved_subject_without_subject_raises(self):
        with self.assertRaises(ValueError) as ctx:
            _make_coverage(status="unresolved_subject", subject=None)
        self.assertIn("subject", str(ctx.exception))

    def test_unresolved_subject_empty_subject_raises(self):
        with self.assertRaises(ValueError):
            _make_coverage(status="unresolved_subject", subject="")

    def test_formalized_with_subject_raises(self):
        with self.assertRaises(ValueError) as ctx:
            _make_coverage(status="formalized", subject="shipped_state")
        self.assertIn("subject", str(ctx.exception))

    def test_skipped_prose_with_subject_raises(self):
        with self.assertRaises(ValueError) as ctx:
            _make_coverage(
                status="skipped_prose", reason="n/a", subject="shipped_state"
            )
        self.assertIn("subject", str(ctx.exception))


# ---------------------------------------------------------------------------
# SpecCheckIR.
# ---------------------------------------------------------------------------

class TestSpecCheckIRHappyPath(unittest.TestCase):

    def test_full_ir(self):
        variables = [_make_variable()]
        constraints = [_make_constraint()]
        coverage = [_make_coverage()]
        ir = SpecCheckIR(variables=variables, constraints=constraints, coverage=coverage)
        self.assertEqual(len(ir.variables), 1)
        self.assertEqual(len(ir.constraints), 1)
        self.assertEqual(len(ir.coverage), 1)

    def test_all_empty_lists_ok(self):
        ir = SpecCheckIR(variables=[], constraints=[], coverage=[])
        self.assertEqual(ir.variables, [])
        self.assertEqual(ir.constraints, [])
        self.assertEqual(ir.coverage, [])

    def test_nothing_formalizable_case(self):
        # Vars declared, all-skipped coverage, zero constraints -- valid.
        variables = [_make_variable()]
        coverage = [
            _make_coverage(ac_id="AC-1", status="skipped_prose", reason="Descriptive only."),
            _make_coverage(ac_id="AC-2", status="skipped_unsupported", reason="Outside v1 sorts."),
        ]
        ir = SpecCheckIR(variables=variables, constraints=[], coverage=coverage)
        self.assertEqual(ir.constraints, [])
        self.assertEqual(len(ir.coverage), 2)


class TestSpecCheckIRValidation(unittest.TestCase):

    def test_variables_wrong_element_type_raises(self):
        with self.assertRaises(ValueError) as ctx:
            SpecCheckIR(variables=["not a Variable"], constraints=[], coverage=[])  # type: ignore[list-item]
        self.assertIn("variables[0]", str(ctx.exception))

    def test_variables_non_list_raises(self):
        with self.assertRaises(ValueError):
            SpecCheckIR(variables=_make_variable(), constraints=[], coverage=[])  # type: ignore[arg-type]

    def test_constraints_wrong_element_type_raises(self):
        with self.assertRaises(ValueError) as ctx:
            SpecCheckIR(variables=[], constraints=["not a Constraint"], coverage=[])  # type: ignore[list-item]
        self.assertIn("constraints[0]", str(ctx.exception))

    def test_coverage_wrong_element_type_raises(self):
        with self.assertRaises(ValueError) as ctx:
            SpecCheckIR(variables=[], constraints=[], coverage=["not a Coverage"])  # type: ignore[list-item]
        self.assertIn("coverage[0]", str(ctx.exception))

    def test_coverage_non_list_raises(self):
        with self.assertRaises(ValueError):
            SpecCheckIR(variables=[], constraints=[], coverage=_make_coverage())  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
