"""Tests for src/devforge/lib/_spec_check/_solve.py.

Coverage:
- Consistent numeric set -> sat, empty core.
- Numeric clash -> unsat with exact core.
- Role/permission clash via an implication + an asserting AC (D9
  reachability) -> unsat; a pure-implications control variant -> sat.
- Enum clash -> unsat with exact core.
- Build-time validation errors: undeclared var, wrong op for sort, Enum
  member not in domain, Int var given a float value.
- "Nothing formalizable" case (vars declared, no constraints) -> sat, empty
  core.
- Module-level helper unit tests: _build_var_table, _atom_to_formula,
  _constraint_to_formula, tracking-literal name round-trip.
- SolveResult validation.

The z3 unsat_core() literal-name round-trip was verified empirically before
writing this file:

    >>> import z3
    >>> s = z3.Solver()
    >>> x = z3.Int('response_ms')
    >>> p1 = z3.Bool('track!AC-3!0')
    >>> p2 = z3.Bool('track!AC-8!1')
    >>> s.assert_and_track(x < 100, p1)
    >>> s.assert_and_track(x > 200, p2)
    >>> s.check()
    unsat
    >>> [str(lit) for lit in s.unsat_core()]
    ['track!AC-3!0', 'track!AC-8!1']

str(lit) returns exactly the literal name passed to z3.Bool() -- no
quoting or reordering -- confirming the "track!{ac_id}!{i}" parse in
_ac_id_from_tracking_literal_name is correct for this z3 version (4.16.0).
"""

import sys
import unittest
from pathlib import Path

import z3

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _spec_check._solve import (  # noqa: E402
    SOLVE_STATUSES,
    SolveResult,
    _ac_id_from_tracking_literal_name,
    _atom_to_formula,
    _build_var_table,
    _constraint_to_formula,
    _tracking_literal_name,
    solve,
)
from _spec_check.ir_schema import (  # noqa: E402
    Atom,
    Constraint,
    Coverage,
    SpecCheckIR,
    Variable,
)


# ---------------------------------------------------------------------------
# Module constants + SolveResult.
# ---------------------------------------------------------------------------

class TestModuleConstants(unittest.TestCase):

    def test_solve_statuses_tuple(self):
        self.assertEqual(SOLVE_STATUSES, ("sat", "unsat", "unknown"))


class TestSolveResult(unittest.TestCase):

    def test_happy_path_sat(self):
        r = SolveResult(status="sat", unsat_core=[])
        self.assertEqual(r.status, "sat")
        self.assertEqual(r.unsat_core, [])

    def test_happy_path_unsat(self):
        r = SolveResult(status="unsat", unsat_core=["AC-1", "AC-2"])
        self.assertEqual(r.unsat_core, ["AC-1", "AC-2"])

    def test_happy_path_unknown(self):
        r = SolveResult(status="unknown", unsat_core=[])
        self.assertEqual(r.status, "unknown")
        self.assertEqual(r.unsat_core, [])

    def test_bad_status_raises(self):
        with self.assertRaises(ValueError) as ctx:
            SolveResult(status="bogus", unsat_core=[])
        self.assertIn("status", str(ctx.exception))

    def test_unsat_core_non_list_raises(self):
        with self.assertRaises(ValueError) as ctx:
            SolveResult(status="unsat", unsat_core="AC-1")  # type: ignore[arg-type]
        self.assertIn("unsat_core", str(ctx.exception))

    def test_unsat_core_non_str_element_raises(self):
        with self.assertRaises(ValueError) as ctx:
            SolveResult(status="unsat", unsat_core=["AC-1", 2])  # type: ignore[list-item]
        self.assertIn("unsat_core[1]", str(ctx.exception))

    def test_nonempty_core_on_sat_raises(self):
        with self.assertRaises(ValueError) as ctx:
            SolveResult(status="sat", unsat_core=["AC-1"])
        self.assertIn("unsat_core", str(ctx.exception))

    def test_nonempty_core_on_unknown_raises(self):
        with self.assertRaises(ValueError) as ctx:
            SolveResult(status="unknown", unsat_core=["AC-1"])
        self.assertIn("unsat_core", str(ctx.exception))

    def test_unsorted_core_raises(self):
        with self.assertRaises(ValueError) as ctx:
            SolveResult(status="unsat", unsat_core=["AC-2", "AC-1"])
        self.assertIn("sorted", str(ctx.exception))

    def test_duplicate_core_raises(self):
        with self.assertRaises(ValueError) as ctx:
            SolveResult(status="unsat", unsat_core=["AC-1", "AC-1"])
        self.assertIn("sorted", str(ctx.exception))

    def test_single_element_core_accepted(self):
        r = SolveResult(status="unsat", unsat_core=["AC-1"])
        self.assertEqual(r.unsat_core, ["AC-1"])


# ---------------------------------------------------------------------------
# Tracking-literal name helpers.
# ---------------------------------------------------------------------------

class TestTrackingLiteralNameRoundTrip(unittest.TestCase):

    def test_build_and_parse(self):
        name = _tracking_literal_name("AC-3", 0)
        self.assertEqual(name, "track!AC-3!0")
        self.assertEqual(_ac_id_from_tracking_literal_name(name), "AC-3")

    def test_build_and_parse_double_digit_index(self):
        name = _tracking_literal_name("AC-12", 7)
        self.assertEqual(_ac_id_from_tracking_literal_name(name), "AC-12")

    def test_shared_ac_id_distinct_literals(self):
        n1 = _tracking_literal_name("AC-1", 0)
        n2 = _tracking_literal_name("AC-1", 1)
        self.assertNotEqual(n1, n2)
        self.assertEqual(_ac_id_from_tracking_literal_name(n1), "AC-1")
        self.assertEqual(_ac_id_from_tracking_literal_name(n2), "AC-1")

    def test_empirical_z3_str_round_trip(self):
        """Confirms z3's str(lit) is exactly the literal name we assigned."""
        s = z3.Solver()
        x = z3.Int("response_ms")
        p1 = z3.Bool("track!AC-3!0")
        p2 = z3.Bool("track!AC-8!1")
        s.assert_and_track(x < 100, p1)
        s.assert_and_track(x > 200, p2)
        self.assertEqual(s.check(), z3.unsat)
        names = sorted(str(lit) for lit in s.unsat_core())
        self.assertEqual(names, ["track!AC-3!0", "track!AC-8!1"])
        self.assertEqual(
            sorted(_ac_id_from_tracking_literal_name(n) for n in names),
            ["AC-3", "AC-8"],
        )


# ---------------------------------------------------------------------------
# _build_var_table.
# ---------------------------------------------------------------------------

class TestBuildVarTable(unittest.TestCase):

    def test_int_var(self):
        table = _build_var_table([Variable(name="x", sort="Int", gloss="An int.")])
        sort, const, member_map = table["x"]
        self.assertEqual(sort, "Int")
        self.assertIsNone(member_map)

    def test_real_var(self):
        table = _build_var_table([Variable(name="x", sort="Real", gloss="A real.")])
        sort, const, member_map = table["x"]
        self.assertEqual(sort, "Real")

    def test_bool_var(self):
        table = _build_var_table([Variable(name="x", sort="Bool", gloss="A bool.")])
        sort, const, member_map = table["x"]
        self.assertEqual(sort, "Bool")

    def test_enum_var(self):
        table = _build_var_table(
            [Variable(name="s", sort="Enum", gloss="A state.", domain=["a", "b"])]
        )
        sort, const, member_map = table["s"]
        self.assertEqual(sort, "Enum")
        self.assertEqual(set(member_map.keys()), {"a", "b"})

    def test_two_enum_vars_get_distinct_sorts(self):
        table = _build_var_table(
            [
                Variable(name="s1", sort="Enum", gloss="State one.", domain=["a", "b"]),
                Variable(name="s2", sort="Enum", gloss="State two.", domain=["a", "b"]),
            ]
        )
        _, const1, map1 = table["s1"]
        _, const2, map2 = table["s2"]
        self.assertIsNot(map1["a"], map2["a"])

    def test_empty_variables_list(self):
        table = _build_var_table([])
        self.assertEqual(table, {})


# ---------------------------------------------------------------------------
# Consistent numeric set -> sat.
# ---------------------------------------------------------------------------

class TestSatCases(unittest.TestCase):

    def test_single_numeric_constraint_sat(self):
        ir = SpecCheckIR(
            variables=[Variable(name="response_ms", sort="Int", gloss="Response time.")],
            constraints=[
                Constraint(
                    ac_id="AC-3",
                    kind="assertion",
                    consequent=[Atom(var="response_ms", op="<", value=100)],
                )
            ],
            coverage=[Coverage(ac_id="AC-3", status="formalized")],
        )
        result = solve(ir)
        self.assertEqual(result.status, "sat")
        self.assertEqual(result.unsat_core, [])

    def test_compatible_numeric_constraints_sat(self):
        ir = SpecCheckIR(
            variables=[Variable(name="response_ms", sort="Int", gloss="Response time.")],
            constraints=[
                Constraint(
                    ac_id="AC-3",
                    kind="assertion",
                    consequent=[Atom(var="response_ms", op="<", value=100)],
                ),
                Constraint(
                    ac_id="AC-4",
                    kind="assertion",
                    consequent=[Atom(var="response_ms", op=">", value=50)],
                ),
            ],
            coverage=[],
        )
        result = solve(ir)
        self.assertEqual(result.status, "sat")
        self.assertEqual(result.unsat_core, [])

    def test_nothing_formalizable_sat(self):
        ir = SpecCheckIR(
            variables=[Variable(name="x", sort="Int", gloss="Unused var.")],
            constraints=[],
            coverage=[
                Coverage(ac_id="AC-1", status="skipped_prose", reason="Descriptive only."),
                Coverage(
                    ac_id="AC-2",
                    status="skipped_unsupported",
                    reason="Outside v1 sorts.",
                ),
            ],
        )
        result = solve(ir)
        self.assertEqual(result.status, "sat")
        self.assertEqual(result.unsat_core, [])

    def test_all_empty_ir_sat(self):
        ir = SpecCheckIR(variables=[], constraints=[], coverage=[])
        result = solve(ir)
        self.assertEqual(result.status, "sat")
        self.assertEqual(result.unsat_core, [])


# ---------------------------------------------------------------------------
# Numeric clash -> unsat.
# ---------------------------------------------------------------------------

class TestNumericClash(unittest.TestCase):

    def test_numeric_clash_exact_core(self):
        ir = SpecCheckIR(
            variables=[Variable(name="response_ms", sort="Int", gloss="Response time.")],
            constraints=[
                Constraint(
                    ac_id="AC-3",
                    kind="assertion",
                    consequent=[Atom(var="response_ms", op="<", value=100)],
                ),
                Constraint(
                    ac_id="AC-8",
                    kind="assertion",
                    consequent=[Atom(var="response_ms", op=">", value=200)],
                ),
            ],
            coverage=[],
        )
        result = solve(ir)
        self.assertEqual(result.status, "unsat")
        self.assertEqual(result.unsat_core, ["AC-3", "AC-8"])

    def test_ac_id_containing_delimiter_char_exact_core(self):
        # Regression: ir_schema.py places no character restriction on
        # ac_id, so "AC!3" is valid IR even though "!" is also the
        # tracking-literal delimiter. The parse must stay robust because
        # _ac_id_from_tracking_literal_name splits on the RIGHTMOST "!"
        # (str.rpartition), which always isolates the trailing numeric
        # index regardless of "!" characters inside the ac_id itself.
        ir = SpecCheckIR(
            variables=[Variable(name="response_ms", sort="Int", gloss="Response time.")],
            constraints=[
                Constraint(
                    ac_id="AC!3",
                    kind="assertion",
                    consequent=[Atom(var="response_ms", op="<", value=100)],
                ),
                Constraint(
                    ac_id="AC!8",
                    kind="assertion",
                    consequent=[Atom(var="response_ms", op=">", value=200)],
                ),
            ],
            coverage=[],
        )
        result = solve(ir)
        self.assertEqual(result.status, "unsat")
        self.assertEqual(result.unsat_core, ["AC!3", "AC!8"])


# ---------------------------------------------------------------------------
# All _NUMERIC_OPS entries exercised end-to-end through solve().
# ("<" and ">" are already covered above via TestSatCases /
#  TestNumericClash; this class covers the remaining four so every
#  _NUMERIC_OPS entry is hit through solve(), not just Atom.__post_init__.)
# ---------------------------------------------------------------------------

class TestNumericOpsThroughSolver(unittest.TestCase):

    def test_single_atom_sat_for_each_op(self):
        for op in ("<=", "=", "!=", ">="):
            with self.subTest(op=op):
                ir = SpecCheckIR(
                    variables=[Variable(name="x", sort="Int", gloss="A value.")],
                    constraints=[
                        Constraint(
                            ac_id="AC-1",
                            kind="assertion",
                            consequent=[Atom(var="x", op=op, value=5)],
                        )
                    ],
                    coverage=[],
                )
                result = solve(ir)
                self.assertEqual(result.status, "sat")
                self.assertEqual(result.unsat_core, [])

    def test_clashing_pair_unsat_for_each_op(self):
        # Each op paired with its logical negation asserted separately --
        # a true contradiction only solve() (not Atom.__post_init__) can
        # detect.
        clash_pairs = {
            "<=": Atom(var="x", op=">", value=5),
            "=": Atom(var="x", op="!=", value=5),
            "!=": Atom(var="x", op="=", value=5),
            ">=": Atom(var="x", op="<", value=5),
        }
        for op, contradicting_atom in clash_pairs.items():
            with self.subTest(op=op):
                ir = SpecCheckIR(
                    variables=[Variable(name="x", sort="Int", gloss="A value.")],
                    constraints=[
                        Constraint(
                            ac_id="AC-A",
                            kind="assertion",
                            consequent=[Atom(var="x", op=op, value=5)],
                        ),
                        Constraint(
                            ac_id="AC-B",
                            kind="assertion",
                            consequent=[contradicting_atom],
                        ),
                    ],
                    coverage=[],
                )
                result = solve(ir)
                self.assertEqual(result.status, "unsat")
                self.assertEqual(result.unsat_core, ["AC-A", "AC-B"])


# ---------------------------------------------------------------------------
# Real sort sat/unsat through solve() (mirrors the Int-sort cases above --
# the Real sort was never previously driven end-to-end through solve()).
# ---------------------------------------------------------------------------

class TestRealSort(unittest.TestCase):

    def test_real_sort_sat(self):
        ir = SpecCheckIR(
            variables=[Variable(name="latency", sort="Real", gloss="Latency in seconds.")],
            constraints=[
                Constraint(
                    ac_id="AC-9",
                    kind="assertion",
                    consequent=[Atom(var="latency", op="<", value=1.5)],
                ),
                Constraint(
                    ac_id="AC-10",
                    kind="assertion",
                    consequent=[Atom(var="latency", op=">", value=0.5)],
                ),
            ],
            coverage=[],
        )
        result = solve(ir)
        self.assertEqual(result.status, "sat")
        self.assertEqual(result.unsat_core, [])

    def test_real_sort_numeric_clash_exact_core(self):
        # ac_ids are "AC-A"/"AC-B", not "AC-9"/"AC-10" -- sorted() is a
        # lexicographic string sort, and "AC-10" < "AC-9" would make an
        # expected-order assertion misleading.
        ir = SpecCheckIR(
            variables=[Variable(name="latency", sort="Real", gloss="Latency in seconds.")],
            constraints=[
                Constraint(
                    ac_id="AC-A",
                    kind="assertion",
                    consequent=[Atom(var="latency", op="<", value=1.0)],
                ),
                Constraint(
                    ac_id="AC-B",
                    kind="assertion",
                    consequent=[Atom(var="latency", op=">", value=2.0)],
                ),
            ],
            coverage=[],
        )
        result = solve(ir)
        self.assertEqual(result.status, "unsat")
        self.assertEqual(result.unsat_core, ["AC-A", "AC-B"])


# ---------------------------------------------------------------------------
# Role/permission clash — D9 reachability semantics.
# ---------------------------------------------------------------------------

class TestReachabilitySemantics(unittest.TestCase):

    def _variables(self):
        return [
            Variable(name="can_delete", sort="Bool", gloss="Actor can delete."),
            Variable(name="is_admin", sort="Bool", gloss="Actor is an admin."),
        ]

    def test_implication_plus_asserting_ac_unsat(self):
        # AC-1: IF can_delete THEN is_admin.
        # AC-2 (assertion): a non-admin CAN delete -- asserts the reachable
        # conflicting scenario directly.
        ir = SpecCheckIR(
            variables=self._variables(),
            constraints=[
                Constraint(
                    ac_id="AC-1",
                    kind="implication",
                    antecedent=[Atom(var="can_delete", op="=", value=True)],
                    consequent=[Atom(var="is_admin", op="=", value=True)],
                ),
                Constraint(
                    ac_id="AC-2",
                    kind="assertion",
                    consequent=[
                        Atom(var="can_delete", op="=", value=True),
                        Atom(var="is_admin", op="=", value=False),
                    ],
                ),
            ],
            coverage=[],
        )
        result = solve(ir)
        self.assertEqual(result.status, "unsat")
        self.assertEqual(result.unsat_core, ["AC-1", "AC-2"])

    def test_two_implications_only_control_is_sat(self):
        # Control: both ACs are pure implications, neither asserts the
        # conflicting scenario as reachable -- D9 honesty boundary: this
        # must stay sat (no spurious unsat from mutually exclusive
        # triggers).
        ir = SpecCheckIR(
            variables=self._variables(),
            constraints=[
                Constraint(
                    ac_id="AC-1",
                    kind="implication",
                    antecedent=[Atom(var="can_delete", op="=", value=True)],
                    consequent=[Atom(var="is_admin", op="=", value=True)],
                ),
                Constraint(
                    ac_id="AC-2",
                    kind="implication",
                    antecedent=[Atom(var="can_delete", op="=", value=True)],
                    consequent=[Atom(var="is_admin", op="=", value=False)],
                ),
            ],
            coverage=[],
        )
        result = solve(ir)
        self.assertEqual(result.status, "sat")
        self.assertEqual(result.unsat_core, [])


# ---------------------------------------------------------------------------
# Enum clash -> unsat.
# ---------------------------------------------------------------------------

class TestEnumClash(unittest.TestCase):

    def test_enum_clash_exact_core(self):
        ir = SpecCheckIR(
            variables=[
                Variable(
                    name="order_state",
                    sort="Enum",
                    gloss="Order lifecycle state.",
                    domain=["pending", "paid", "shipped"],
                )
            ],
            constraints=[
                Constraint(
                    ac_id="AC-5",
                    kind="assertion",
                    consequent=[Atom(var="order_state", op="=", value="shipped")],
                ),
                Constraint(
                    ac_id="AC-6",
                    kind="assertion",
                    consequent=[Atom(var="order_state", op="=", value="pending")],
                ),
            ],
            coverage=[],
        )
        result = solve(ir)
        self.assertEqual(result.status, "unsat")
        self.assertEqual(result.unsat_core, ["AC-5", "AC-6"])

    def test_enum_not_equals_sat(self):
        ir = SpecCheckIR(
            variables=[
                Variable(
                    name="order_state",
                    sort="Enum",
                    gloss="Order lifecycle state.",
                    domain=["pending", "paid", "shipped"],
                )
            ],
            constraints=[
                Constraint(
                    ac_id="AC-5",
                    kind="assertion",
                    consequent=[Atom(var="order_state", op="!=", value="shipped")],
                ),
            ],
            coverage=[],
        )
        result = solve(ir)
        self.assertEqual(result.status, "sat")


# ---------------------------------------------------------------------------
# Build-time validation errors.
# ---------------------------------------------------------------------------

class TestBuildTimeValidation(unittest.TestCase):

    def test_atom_references_undeclared_var_raises(self):
        ir = SpecCheckIR(
            variables=[Variable(name="response_ms", sort="Int", gloss="Response time.")],
            constraints=[
                Constraint(
                    ac_id="AC-1",
                    kind="assertion",
                    consequent=[Atom(var="undeclared_var", op="<", value=1)],
                )
            ],
            coverage=[],
        )
        with self.assertRaises(ValueError) as ctx:
            solve(ir)
        self.assertIn("undeclared", str(ctx.exception))
        self.assertIn("AC-1", str(ctx.exception))

    def test_bool_var_with_comparison_op_raises(self):
        ir = SpecCheckIR(
            variables=[Variable(name="is_admin", sort="Bool", gloss="Is admin.")],
            constraints=[
                Constraint(
                    ac_id="AC-2",
                    kind="assertion",
                    consequent=[Atom(var="is_admin", op="<", value=True)],
                )
            ],
            coverage=[],
        )
        with self.assertRaises(ValueError) as ctx:
            solve(ir)
        self.assertIn("Bool", str(ctx.exception))
        self.assertIn("AC-2", str(ctx.exception))

    def test_enum_member_not_in_domain_raises(self):
        ir = SpecCheckIR(
            variables=[
                Variable(
                    name="order_state",
                    sort="Enum",
                    gloss="Order state.",
                    domain=["pending", "paid"],
                )
            ],
            constraints=[
                Constraint(
                    ac_id="AC-3",
                    kind="assertion",
                    consequent=[Atom(var="order_state", op="=", value="shipped")],
                )
            ],
            coverage=[],
        )
        with self.assertRaises(ValueError) as ctx:
            solve(ir)
        self.assertIn("domain", str(ctx.exception))
        self.assertIn("AC-3", str(ctx.exception))

    def test_int_var_given_float_value_raises(self):
        ir = SpecCheckIR(
            variables=[Variable(name="count", sort="Int", gloss="A count.")],
            constraints=[
                Constraint(
                    ac_id="AC-4",
                    kind="assertion",
                    consequent=[Atom(var="count", op="<", value=1.5)],
                )
            ],
            coverage=[],
        )
        with self.assertRaises(ValueError) as ctx:
            solve(ir)
        self.assertIn("Int", str(ctx.exception))
        self.assertIn("AC-4", str(ctx.exception))

    def test_enum_var_with_comparison_op_raises(self):
        ir = SpecCheckIR(
            variables=[
                Variable(
                    name="order_state",
                    sort="Enum",
                    gloss="Order state.",
                    domain=["pending", "paid"],
                )
            ],
            constraints=[
                Constraint(
                    ac_id="AC-5",
                    kind="assertion",
                    consequent=[Atom(var="order_state", op="<", value="pending")],
                )
            ],
            coverage=[],
        )
        with self.assertRaises(ValueError) as ctx:
            solve(ir)
        self.assertIn("Enum", str(ctx.exception))

    def test_real_var_given_bool_value_raises(self):
        ir = SpecCheckIR(
            variables=[Variable(name="latency", sort="Real", gloss="Latency.")],
            constraints=[
                Constraint(
                    ac_id="AC-6",
                    kind="assertion",
                    consequent=[Atom(var="latency", op="<", value=True)],
                )
            ],
            coverage=[],
        )
        with self.assertRaises(ValueError):
            solve(ir)


# ---------------------------------------------------------------------------
# _atom_to_formula direct unit tests.
# ---------------------------------------------------------------------------

class TestAtomToFormula(unittest.TestCase):

    def test_int_less_than(self):
        table = _build_var_table([Variable(name="x", sort="Int", gloss="An int.")])
        formula = _atom_to_formula(Atom(var="x", op="<", value=5), table, "AC-1")
        self.assertTrue(z3.is_expr(formula))

    def test_bool_true_formula_is_const(self):
        table = _build_var_table([Variable(name="b", sort="Bool", gloss="A bool.")])
        formula = _atom_to_formula(Atom(var="b", op="=", value=True), table, "AC-1")
        _, const, _ = table["b"]
        self.assertTrue(formula.eq(const))

    def test_bool_false_formula_is_not_const(self):
        table = _build_var_table([Variable(name="b", sort="Bool", gloss="A bool.")])
        formula = _atom_to_formula(Atom(var="b", op="=", value=False), table, "AC-1")
        self.assertEqual(formula.decl().name(), "not")

    def test_enum_equals_formula(self):
        table = _build_var_table(
            [Variable(name="s", sort="Enum", gloss="A state.", domain=["a", "b"])]
        )
        formula = _atom_to_formula(Atom(var="s", op="=", value="a"), table, "AC-1")
        self.assertTrue(z3.is_expr(formula))

    def test_enum_not_equals_formula(self):
        table = _build_var_table(
            [Variable(name="s", sort="Enum", gloss="A state.", domain=["a", "b"])]
        )
        formula = _atom_to_formula(Atom(var="s", op="!=", value="a"), table, "AC-1")
        self.assertTrue(z3.is_expr(formula))


# ---------------------------------------------------------------------------
# _constraint_to_formula direct unit tests.
# ---------------------------------------------------------------------------

class TestConstraintToFormula(unittest.TestCase):

    def test_assertion_single_atom(self):
        table = _build_var_table([Variable(name="x", sort="Int", gloss="An int.")])
        constraint = Constraint(
            ac_id="AC-1", kind="assertion", consequent=[Atom(var="x", op="<", value=5)]
        )
        formula = _constraint_to_formula(constraint, table)
        self.assertTrue(z3.is_expr(formula))

    def test_assertion_multi_atom_uses_and(self):
        table = _build_var_table([Variable(name="x", sort="Int", gloss="An int.")])
        constraint = Constraint(
            ac_id="AC-1",
            kind="assertion",
            consequent=[
                Atom(var="x", op="<", value=5),
                Atom(var="x", op=">", value=0),
            ],
        )
        formula = _constraint_to_formula(constraint, table)
        self.assertEqual(formula.decl().name(), "and")

    def test_implication_uses_implies(self):
        table = _build_var_table(
            [
                Variable(name="a", sort="Bool", gloss="A."),
                Variable(name="b", sort="Bool", gloss="B."),
            ]
        )
        constraint = Constraint(
            ac_id="AC-1",
            kind="implication",
            antecedent=[Atom(var="a", op="=", value=True)],
            consequent=[Atom(var="b", op="=", value=True)],
        )
        formula = _constraint_to_formula(constraint, table)
        self.assertEqual(formula.decl().name(), "=>")


if __name__ == "__main__":
    unittest.main()
