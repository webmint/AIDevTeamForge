"""Tests for src/devforge/lib/_spec_check/_consume.py.

Covers:
  - extract_acs -- delegates to _shared.spec_acs.parse_acs (real-fixture
    round-trip).
  - parse_ir -- happy paths (dict input, JSON-string input, all atom
    shapes) and error paths (every IRParseError trigger named in the brief).
  - validate_ir -- a VALID full IR over the real fixture's 7 AC ids, and
    every INVALID case named in the brief, each asserting the PRECISE error
    string is present. Also confirms collect-all (multiple simultaneous
    errors all surface together).
  - validate_ir_or_raise -- raises IRValidationError on the invalid set,
    returns None on the valid set.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"
_FIXTURES_DIR = _REPO_ROOT / "tests" / "lib" / "fixtures"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _spec_check._consume import (  # noqa: E402
    IRParseError,
    IRValidationError,
    extract_acs,
    parse_ir,
    validate_ir,
    validate_ir_or_raise,
)
from _spec_check.ir_schema import Atom  # noqa: E402

_REAL_SPEC = str(_FIXTURES_DIR / "specify-sample-migration.md")


# ---------------------------------------------------------------------------
# extract_acs
# ---------------------------------------------------------------------------


class TestExtractAcs(unittest.TestCase):
    """extract_acs is a thin delegation to _shared.spec_acs.parse_acs."""

    def test_real_fixture_returns_seven_acs(self):
        acs = extract_acs(_REAL_SPEC)
        self.assertEqual(len(acs), 7)
        self.assertEqual([a["id"] for a in acs], ["AC-{0}".format(i) for i in range(1, 8)])

    def test_ac1_text_matches(self):
        acs = extract_acs(_REAL_SPEC)
        self.assertIn("lerna", acs[0]["text"])

    def test_empty_source_returns_empty_list(self):
        self.assertEqual(extract_acs(""), [])


# ---------------------------------------------------------------------------
# Shared fixture data for parse_ir / validate_ir tests.
# ---------------------------------------------------------------------------


def _real_ac_ids():
    return [a["id"] for a in extract_acs(_REAL_SPEC)]


def _full_valid_raw_ir():
    """A full, self-consistent raw IR dict over the real fixture's 7 ACs.

    - AC-1: numeric assertion (Int).
    - AC-3: Enum atom (assertion).
    - AC-5: implication with a Bool short-form antecedent (negated=False)
      and a Bool short-form consequent (negated=True) -- exercises both
      directions of the negated -> value mapping.
    - AC-2, AC-4, AC-6: skipped_prose with reasons.
    - AC-7: skipped_unsupported with a reason.
    """
    return {
        "variables": [
            {"name": "n_lerna_refs", "sort": "Int", "gloss": "count of lerna references"},
            {
                "name": "ci_state",
                "sort": "Enum",
                "gloss": "CI pipeline package-manager state",
                "domain": ["pnpm", "yarn", "unknown"],
            },
            {
                "name": "yarn_lock_committed",
                "sort": "Bool",
                "gloss": "a yarn lockfile is committed to the repo",
            },
            {
                "name": "hook_rejects_commit",
                "sort": "Bool",
                "gloss": "the pre-commit hook rejects the commit",
            },
        ],
        "constraints": [
            {
                "ac_id": "AC-1",
                "kind": "assertion",
                "consequent": [{"var": "n_lerna_refs", "op": "=", "value": 0}],
            },
            {
                "ac_id": "AC-3",
                "kind": "assertion",
                "consequent": [{"var": "ci_state", "op": "=", "value": "pnpm"}],
            },
            {
                "ac_id": "AC-5",
                "kind": "implication",
                "antecedent": [{"var": "yarn_lock_committed", "negated": False}],
                "consequent": [{"var": "hook_rejects_commit", "negated": True}],
            },
        ],
        "coverage": [
            {"ac_id": "AC-1", "status": "formalized"},
            {
                "ac_id": "AC-2",
                "status": "skipped_prose",
                "reason": "behavior preservation is qualitative, not formalizable",
            },
            {"ac_id": "AC-3", "status": "formalized"},
            {
                "ac_id": "AC-4",
                "status": "skipped_prose",
                "reason": "CI pipeline behavior, no numeric/boolean invariant captured",
            },
            {"ac_id": "AC-5", "status": "formalized"},
            {
                "ac_id": "AC-6",
                "status": "skipped_prose",
                "reason": "documentation content, not formalizable",
            },
            {
                "ac_id": "AC-7",
                "status": "skipped_unsupported",
                "reason": "requires filesystem enumeration, out of scope for the solver",
            },
        ],
    }


# ---------------------------------------------------------------------------
# parse_ir -- happy paths
# ---------------------------------------------------------------------------


class TestParseIrHappyPath(unittest.TestCase):
    def setUp(self):
        self.raw = _full_valid_raw_ir()

    def test_dict_input_builds_spec_check_ir(self):
        ir = parse_ir(self.raw)
        self.assertEqual(len(ir.variables), 4)
        self.assertEqual(len(ir.constraints), 3)
        self.assertEqual(len(ir.coverage), 7)

    def test_json_string_input_builds_same_shape(self):
        ir = parse_ir(json.dumps(self.raw))
        self.assertEqual(len(ir.variables), 4)
        self.assertEqual(len(ir.constraints), 3)
        self.assertEqual(len(ir.coverage), 7)

    def test_numeric_assertion_atom(self):
        ir = parse_ir(self.raw)
        ac1 = next(c for c in ir.constraints if c.ac_id == "AC-1")
        self.assertEqual(ac1.kind, "assertion")
        self.assertEqual(ac1.consequent, [Atom("n_lerna_refs", "=", 0)])
        self.assertIsNone(ac1.antecedent)

    def test_enum_atom(self):
        ir = parse_ir(self.raw)
        ac3 = next(c for c in ir.constraints if c.ac_id == "AC-3")
        self.assertEqual(ac3.consequent, [Atom("ci_state", "=", "pnpm")])

    def test_bool_short_form_negated_false_becomes_true(self):
        ir = parse_ir(self.raw)
        ac5 = next(c for c in ir.constraints if c.ac_id == "AC-5")
        self.assertEqual(ac5.antecedent, [Atom("yarn_lock_committed", "=", True)])

    def test_bool_short_form_negated_true_becomes_false(self):
        ir = parse_ir(self.raw)
        ac5 = next(c for c in ir.constraints if c.ac_id == "AC-5")
        self.assertEqual(ac5.consequent, [Atom("hook_rejects_commit", "=", False)])

    def test_implication_kind_and_antecedent_present(self):
        ir = parse_ir(self.raw)
        ac5 = next(c for c in ir.constraints if c.ac_id == "AC-5")
        self.assertEqual(ac5.kind, "implication")
        self.assertIsNotNone(ac5.antecedent)

    def test_variable_domain_preserved(self):
        ir = parse_ir(self.raw)
        ci_state = next(v for v in ir.variables if v.name == "ci_state")
        self.assertEqual(ci_state.domain, ["pnpm", "yarn", "unknown"])

    def test_coverage_entries_preserved(self):
        ir = parse_ir(self.raw)
        ac7 = next(c for c in ir.coverage if c.ac_id == "AC-7")
        self.assertEqual(ac7.status, "skipped_unsupported")
        self.assertIn("filesystem", ac7.reason)

    def test_empty_lists_valid_nothing_formalizable(self):
        """variables/constraints empty, coverage all-skipped -- the 'nothing
        formalizable' case is valid IR."""
        raw = {
            "variables": [],
            "constraints": [],
            "coverage": [
                {"ac_id": "AC-1", "status": "skipped_prose", "reason": "n/a"},
            ],
        }
        ir = parse_ir(raw)
        self.assertEqual(ir.variables, [])
        self.assertEqual(ir.constraints, [])
        self.assertEqual(len(ir.coverage), 1)


# ---------------------------------------------------------------------------
# parse_ir -- error paths
# ---------------------------------------------------------------------------


class TestParseIrErrors(unittest.TestCase):
    def test_bad_json_string(self):
        with self.assertRaises(IRParseError):
            parse_ir("{not valid json")

    def test_missing_top_level_constraints_key(self):
        raw = {"variables": [], "coverage": []}
        with self.assertRaises(IRParseError) as ctx:
            parse_ir(raw)
        self.assertIn("constraints", str(ctx.exception))

    def test_missing_top_level_variables_key(self):
        raw = {"constraints": [], "coverage": []}
        with self.assertRaises(IRParseError) as ctx:
            parse_ir(raw)
        self.assertIn("variables", str(ctx.exception))

    def test_missing_top_level_coverage_key(self):
        raw = {"variables": [], "constraints": []}
        with self.assertRaises(IRParseError) as ctx:
            parse_ir(raw)
        self.assertIn("coverage", str(ctx.exception))

    def test_variables_not_a_list(self):
        raw = {"variables": "nope", "constraints": [], "coverage": []}
        with self.assertRaises(IRParseError) as ctx:
            parse_ir(raw)
        self.assertIn("variables", str(ctx.exception))

    def test_raw_not_dict_or_str(self):
        with self.assertRaises(IRParseError):
            parse_ir(12345)

    def test_root_json_not_an_object(self):
        with self.assertRaises(IRParseError):
            parse_ir("[1, 2, 3]")

    def test_variable_missing_sort(self):
        raw = {
            "variables": [{"name": "x", "gloss": "some var"}],
            "constraints": [],
            "coverage": [],
        }
        with self.assertRaises(IRParseError) as ctx:
            parse_ir(raw)
        msg = str(ctx.exception)
        self.assertIn("variables[0]", msg)
        self.assertIn("sort", msg)

    def test_atom_with_both_negated_and_op(self):
        raw = {
            "variables": [{"name": "x", "sort": "Bool", "gloss": "g"}],
            "constraints": [
                {
                    "ac_id": "AC-1",
                    "kind": "assertion",
                    "consequent": [{"var": "x", "negated": True, "op": "="}],
                }
            ],
            "coverage": [],
        }
        with self.assertRaises(IRParseError) as ctx:
            parse_ir(raw)
        msg = str(ctx.exception)
        # F3: atom-list locators carry the AC label, same as the
        # constraint-wrapper locator -- "constraints[0] (AC-1).consequent[0]".
        self.assertIn("constraints[0] (AC-1).consequent[0]", msg)
        self.assertIn("ambiguous", msg)

    def test_negated_not_a_bool(self):
        raw = {
            "variables": [{"name": "x", "sort": "Bool", "gloss": "g"}],
            "constraints": [
                {
                    "ac_id": "AC-1",
                    "kind": "assertion",
                    "consequent": [{"var": "x", "negated": "yes"}],
                }
            ],
            "coverage": [],
        }
        with self.assertRaises(IRParseError):
            parse_ir(raw)

    def test_constraint_empty_consequent(self):
        raw = {
            "variables": [],
            "constraints": [
                {"ac_id": "AC-3", "kind": "assertion", "consequent": []}
            ],
            "coverage": [],
        }
        with self.assertRaises(IRParseError) as ctx:
            parse_ir(raw)
        msg = str(ctx.exception)
        self.assertIn("constraints[0] (AC-3)", msg)
        self.assertIn("non-empty", msg)

    def test_implication_missing_antecedent(self):
        raw = {
            "variables": [{"name": "x", "sort": "Bool", "gloss": "g"}],
            "constraints": [
                {
                    "ac_id": "AC-5",
                    "kind": "implication",
                    "consequent": [{"var": "x", "negated": False}],
                }
            ],
            "coverage": [],
        }
        with self.assertRaises(IRParseError) as ctx:
            parse_ir(raw)
        msg = str(ctx.exception)
        self.assertIn("constraints[0] (AC-5)", msg)
        self.assertIn("antecedent", msg)

    def test_coverage_missing_status(self):
        raw = {
            "variables": [],
            "constraints": [],
            "coverage": [{"ac_id": "AC-1"}],
        }
        with self.assertRaises(IRParseError) as ctx:
            parse_ir(raw)
        self.assertIn("coverage[0]", str(ctx.exception))

    # -----------------------------------------------------------------
    # F2: dataclass ValueError -> IRParseError re-raise path (one per
    # dataclass). Each case is well-TYPED (right Python type) but
    # semantically invalid (a bad enum member) -- the LLM's likeliest
    # failure mode, distinct from every pre-check above which trips on a
    # missing/wrong-typed key before the dataclass is ever constructed.
    # -----------------------------------------------------------------

    def test_variable_invalid_sort_value(self):
        """Variable(sort='Weird') -- well-typed str, not a valid SORTS member."""
        raw = {
            "variables": [{"name": "x", "sort": "Weird", "gloss": "g"}],
            "constraints": [],
            "coverage": [],
        }
        with self.assertRaises(IRParseError) as ctx:
            parse_ir(raw)
        self.assertIn("variables[0]", str(ctx.exception))

    def test_atom_invalid_op_value(self):
        """Atom(op='BADOP') -- well-typed str, not a valid COMPARISON_OPS member."""
        raw = {
            "variables": [{"name": "x", "sort": "Int", "gloss": "g"}],
            "constraints": [
                {
                    "ac_id": "AC-1",
                    "kind": "assertion",
                    "consequent": [{"var": "x", "op": "BADOP", "value": 1}],
                }
            ],
            "coverage": [],
        }
        with self.assertRaises(IRParseError) as ctx:
            parse_ir(raw)
        self.assertIn("constraints[0] (AC-1).consequent[0]", str(ctx.exception))

    def test_constraint_invalid_kind_value(self):
        """Constraint(kind='weird') -- well-typed str, not a valid
        CONSTRAINT_KINDS member."""
        raw = {
            "variables": [{"name": "x", "sort": "Int", "gloss": "g"}],
            "constraints": [
                {
                    "ac_id": "AC-1",
                    "kind": "weird",
                    "consequent": [{"var": "x", "op": "=", "value": 1}],
                }
            ],
            "coverage": [],
        }
        with self.assertRaises(IRParseError) as ctx:
            parse_ir(raw)
        self.assertIn("constraints[0] (AC-1)", str(ctx.exception))

    def test_coverage_invalid_status_value(self):
        """Coverage(status='weird') -- well-typed str, not a valid
        COVERAGE_STATUSES member."""
        raw = {
            "variables": [],
            "constraints": [],
            "coverage": [{"ac_id": "AC-1", "status": "weird"}],
        }
        with self.assertRaises(IRParseError) as ctx:
            parse_ir(raw)
        self.assertIn("coverage[0]", str(ctx.exception))


# ---------------------------------------------------------------------------
# validate_ir -- VALID case
# ---------------------------------------------------------------------------


class TestValidateIrValid(unittest.TestCase):
    def test_full_valid_ir_returns_no_errors(self):
        ac_ids = _real_ac_ids()
        ir = parse_ir(_full_valid_raw_ir())
        errors = validate_ir(ir, ac_ids)
        self.assertEqual(errors, [])

    def test_valid_ir_does_not_raise(self):
        ac_ids = _real_ac_ids()
        ir = parse_ir(_full_valid_raw_ir())
        result = validate_ir_or_raise(ir, ac_ids)
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# validate_ir -- INVALID cases
# ---------------------------------------------------------------------------


class TestValidateIrInvalid(unittest.TestCase):
    def test_undeclared_variable(self):
        raw = {
            "variables": [{"name": "n_lerna_refs", "sort": "Int", "gloss": "g"}],
            "constraints": [
                {
                    "ac_id": "AC-1",
                    "kind": "assertion",
                    "consequent": [{"var": "nonexistent_var", "op": "=", "value": 0}],
                }
            ],
            "coverage": [{"ac_id": "AC-1", "status": "formalized"}],
        }
        ir = parse_ir(raw)
        errors = validate_ir(ir, ["AC-1"])
        self.assertIn(
            "AC-1: atom references undeclared variable 'nonexistent_var'", errors
        )

    def test_missing_coverage_entry(self):
        """Drop AC-4's coverage entry from an otherwise-valid full IR."""
        raw = _full_valid_raw_ir()
        raw["coverage"] = [c for c in raw["coverage"] if c["ac_id"] != "AC-4"]
        ir = parse_ir(raw)
        errors = validate_ir(ir, _real_ac_ids())
        self.assertIn("AC coverage missing for AC-4", errors)

    def test_coverage_references_unknown_ac(self):
        raw = _full_valid_raw_ir()
        raw["coverage"].append(
            {"ac_id": "AC-99", "status": "skipped_prose", "reason": "n/a"}
        )
        ir = parse_ir(raw)
        errors = validate_ir(ir, _real_ac_ids())
        self.assertIn("coverage references unknown AC 'AC-99'", errors)

    def test_constraint_ac_marked_skipped_prose(self):
        """A constraint's ac_id (AC-2) is marked skipped_prose in coverage."""
        raw = _full_valid_raw_ir()
        raw["constraints"].append(
            {
                "ac_id": "AC-2",
                "kind": "assertion",
                "consequent": [{"var": "n_lerna_refs", "op": ">=", "value": 0}],
            }
        )
        ir = parse_ir(raw)
        errors = validate_ir(ir, _real_ac_ids())
        self.assertIn("AC-2 marked skipped_prose but has 1 constraint(s)", errors)

    def test_enum_atom_value_not_in_domain(self):
        raw = {
            "variables": [
                {
                    "name": "ci_state",
                    "sort": "Enum",
                    "gloss": "g",
                    "domain": ["pnpm", "yarn"],
                }
            ],
            "constraints": [
                {
                    "ac_id": "AC-3",
                    "kind": "assertion",
                    "consequent": [{"var": "ci_state", "op": "=", "value": "unknown"}],
                }
            ],
            "coverage": [{"ac_id": "AC-3", "status": "formalized"}],
        }
        ir = parse_ir(raw)
        errors = validate_ir(ir, ["AC-3"])
        self.assertIn(
            "AC-3: Enum variable 'ci_state' value 'unknown' not in domain "
            "['pnpm', 'yarn']",
            errors,
        )

    def test_int_var_given_float(self):
        raw = {
            "variables": [{"name": "n_lerna_refs", "sort": "Int", "gloss": "g"}],
            "constraints": [
                {
                    "ac_id": "AC-1",
                    "kind": "assertion",
                    "consequent": [{"var": "n_lerna_refs", "op": "=", "value": 1.5}],
                }
            ],
            "coverage": [{"ac_id": "AC-1", "status": "formalized"}],
        }
        ir = parse_ir(raw)
        errors = validate_ir(ir, ["AC-1"])
        self.assertIn(
            "AC-1: Int variable 'n_lerna_refs' given non-int value 1.5", errors
        )

    def test_duplicate_variable_name(self):
        raw = {
            "variables": [
                {"name": "dup", "sort": "Int", "gloss": "first"},
                {"name": "dup", "sort": "Int", "gloss": "second"},
            ],
            "constraints": [],
            "coverage": [],
        }
        ir = parse_ir(raw)
        errors = validate_ir(ir, [])
        self.assertIn("duplicate variable name 'dup'", errors)

    def test_real_var_given_bool_value(self):
        """F1: a Real var given a bool value is non-numeric per the Real check."""
        raw = {
            "variables": [{"name": "r", "sort": "Real", "gloss": "g"}],
            "constraints": [
                {
                    "ac_id": "AC-1",
                    "kind": "assertion",
                    "consequent": [{"var": "r", "op": "=", "value": True}],
                }
            ],
            "coverage": [{"ac_id": "AC-1", "status": "formalized"}],
        }
        ir = parse_ir(raw)
        errors = validate_ir(ir, ["AC-1"])
        self.assertIn(
            "AC-1: Real variable 'r' given non-numeric value True", errors
        )

    def test_bool_var_generic_shape_wrong_op(self):
        """F1: a Bool var via the generic atom shape (not the negated
        short-form) with a non-'=' op is invalid -- the negated short-form
        can never reach this branch since parse_ir always normalizes it to
        a valid op='=' Atom."""
        raw = {
            "variables": [{"name": "b", "sort": "Bool", "gloss": "g"}],
            "constraints": [
                {
                    "ac_id": "AC-1",
                    "kind": "assertion",
                    "consequent": [{"var": "b", "op": "!=", "value": True}],
                }
            ],
            "coverage": [{"ac_id": "AC-1", "status": "formalized"}],
        }
        ir = parse_ir(raw)
        errors = validate_ir(ir, ["AC-1"])
        self.assertIn(
            "AC-1: Bool variable 'b' given invalid op/value "
            "(op='!=', value=True)",
            errors,
        )

    def test_enum_var_invalid_op(self):
        """F1: an Enum atom using a comparison op valid at the Atom level
        (e.g. '<') but not valid for Enum ('=' or '!=' only)."""
        raw = {
            "variables": [
                {"name": "e", "sort": "Enum", "gloss": "g", "domain": ["a", "b"]}
            ],
            "constraints": [
                {
                    "ac_id": "AC-1",
                    "kind": "assertion",
                    "consequent": [{"var": "e", "op": "<", "value": "a"}],
                }
            ],
            "coverage": [{"ac_id": "AC-1", "status": "formalized"}],
        }
        ir = parse_ir(raw)
        errors = validate_ir(ir, ["AC-1"])
        self.assertIn("AC-1: Enum variable 'e' given invalid op '<'", errors)

    def test_duplicate_coverage_entry(self):
        """F1: two coverage entries for the same ac_id."""
        raw = {
            "variables": [],
            "constraints": [],
            "coverage": [
                {"ac_id": "AC-1", "status": "skipped_prose", "reason": "r1"},
                {"ac_id": "AC-1", "status": "skipped_prose", "reason": "r2"},
            ],
        }
        ir = parse_ir(raw)
        errors = validate_ir(ir, ["AC-1"])
        self.assertIn("duplicate coverage entry for AC 'AC-1'", errors)

    def test_duplicate_var_name_suppresses_sort_check(self):
        """F4: an atom on a duplicate-declared var name gets ONLY the
        duplicate-name error -- no sort-consistency noise resolved against
        the arbitrary first-seen declaration."""
        raw = {
            "variables": [
                {"name": "dup", "sort": "Int", "gloss": "first (arbitrary)"},
                {"name": "dup", "sort": "Bool", "gloss": "second (actually meant)"},
            ],
            "constraints": [
                {
                    "ac_id": "AC-1",
                    "kind": "assertion",
                    "consequent": [{"var": "dup", "negated": False}],
                }
            ],
            "coverage": [{"ac_id": "AC-1", "status": "formalized"}],
        }
        ir = parse_ir(raw)
        errors = validate_ir(ir, ["AC-1"])
        self.assertEqual(errors, ["duplicate variable name 'dup'"])

    def test_formalized_ac_with_no_constraint(self):
        raw = {
            "variables": [],
            "constraints": [],
            "coverage": [{"ac_id": "AC-1", "status": "formalized"}],
        }
        ir = parse_ir(raw)
        errors = validate_ir(ir, ["AC-1"])
        self.assertIn("AC-1 marked formalized but has no constraint", errors)

    def test_multiple_simultaneous_errors_all_returned(self):
        """Undeclared var AND missing coverage in the same IR -- both surface."""
        raw = {
            "variables": [{"name": "n_lerna_refs", "sort": "Int", "gloss": "g"}],
            "constraints": [
                {
                    "ac_id": "AC-1",
                    "kind": "assertion",
                    "consequent": [{"var": "ghost_var", "op": "=", "value": 0}],
                }
            ],
            "coverage": [],
        }
        ir = parse_ir(raw)
        errors = validate_ir(ir, ["AC-1", "AC-2"])
        self.assertIn(
            "AC-1: atom references undeclared variable 'ghost_var'", errors
        )
        self.assertIn("AC coverage missing for AC-1", errors)
        self.assertIn("AC coverage missing for AC-2", errors)
        self.assertGreaterEqual(len(errors), 3)


# ---------------------------------------------------------------------------
# validate_ir_or_raise
# ---------------------------------------------------------------------------


class TestValidateIrOrRaise(unittest.TestCase):
    def test_raises_ir_validation_error_on_invalid(self):
        raw = {
            "variables": [],
            "constraints": [],
            "coverage": [{"ac_id": "AC-1", "status": "formalized"}],
        }
        ir = parse_ir(raw)
        with self.assertRaises(IRValidationError) as ctx:
            validate_ir_or_raise(ir, ["AC-1"])
        self.assertIn("marked formalized but has no constraint", str(ctx.exception))

    def test_passes_silently_on_valid(self):
        ac_ids = _real_ac_ids()
        ir = parse_ir(_full_valid_raw_ir())
        try:
            validate_ir_or_raise(ir, ac_ids)
        except IRValidationError:
            self.fail("validate_ir_or_raise raised on a valid IR")


if __name__ == "__main__":
    unittest.main()
