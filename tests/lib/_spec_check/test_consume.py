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
  - Plan 82 Phase 1 (subject resolution): parse_ir happy/error paths for
    Variable.subject_resolution + Coverage.subject; back-compat parsing of
    historical IR dicts lacking both keys; validate_ir's third
    status/constraint agreement branch (unresolved_subject) and its
    subject-names-a-declared-variable cross-check; dataclasses.asdict
    round-trip for every new record shape; validate_citations (D3's one
    filesystem-touching check) against real tmp-dir workspace roots.
"""

from __future__ import annotations

import dataclasses
import json
import os
import sys
import tempfile
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
    validate_citations,
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
# parse_ir -- Variable.subject_resolution / Coverage.subject (Plan 82
# Phase 1).
# ---------------------------------------------------------------------------


def _raw_var_code_resolution(**sr_overrides):
    sr = {
        "status": "resolved",
        "arm": "code",
        "citation": "src/orders.py",
        "locator": "def mark_shipped",
        "note": "mark_shipped() sets the shipped flag.",
    }
    sr.update(sr_overrides)
    return {
        "variables": [
            {
                "name": "shipped_state",
                "sort": "Bool",
                "gloss": "order has shipped",
                "subject_resolution": sr,
            }
        ],
        "constraints": [],
        "coverage": [],
    }


def _raw_var_spec_resolution(**sr_overrides):
    sr = {
        "status": "resolved",
        "arm": "spec",
        "citation": "AC-3",
        "note": "AC-3 introduces the shipped state as new behavior.",
    }
    sr.update(sr_overrides)
    return {
        "variables": [
            {
                "name": "shipped_state",
                "sort": "Bool",
                "gloss": "order has shipped",
                "subject_resolution": sr,
            }
        ],
        "constraints": [],
        "coverage": [],
    }


def _raw_var_unresolved(**sr_overrides):
    sr = {
        "status": "unresolved",
        "searched": "grepped 'shipped' and 'mark_shipped' across src/, 0 hits.",
    }
    sr.update(sr_overrides)
    return {
        "variables": [
            {
                "name": "shipped_state",
                "sort": "Bool",
                "gloss": "order has shipped",
                "subject_resolution": sr,
            }
        ],
        "constraints": [],
        "coverage": [],
    }


class TestParseIrSubjectResolutionHappyPath(unittest.TestCase):
    def test_variable_arm_code_parses(self):
        ir = parse_ir(_raw_var_code_resolution())
        sr = ir.variables[0].subject_resolution
        self.assertEqual(sr.status, "resolved")
        self.assertEqual(sr.arm, "code")
        self.assertEqual(sr.citation, "src/orders.py")
        self.assertEqual(sr.locator, "def mark_shipped")

    def test_variable_arm_spec_parses(self):
        ir = parse_ir(_raw_var_spec_resolution())
        sr = ir.variables[0].subject_resolution
        self.assertEqual(sr.arm, "spec")
        self.assertEqual(sr.citation, "AC-3")
        self.assertIsNone(sr.locator)

    def test_variable_unresolved_parses(self):
        ir = parse_ir(_raw_var_unresolved())
        sr = ir.variables[0].subject_resolution
        self.assertEqual(sr.status, "unresolved")
        self.assertIn("grepped", sr.searched)

    def test_variable_without_subject_resolution_key_defaults_none(self):
        raw = {
            "variables": [{"name": "n", "sort": "Int", "gloss": "g"}],
            "constraints": [],
            "coverage": [],
        }
        ir = parse_ir(raw)
        self.assertIsNone(ir.variables[0].subject_resolution)

    def test_coverage_subject_parses(self):
        raw = {
            "variables": [{"name": "shipped_state", "sort": "Bool", "gloss": "g"}],
            "constraints": [],
            "coverage": [
                {
                    "ac_id": "AC-1",
                    "status": "unresolved_subject",
                    "subject": "shipped_state",
                }
            ],
        }
        ir = parse_ir(raw)
        self.assertEqual(ir.coverage[0].subject, "shipped_state")

    def test_coverage_without_subject_key_defaults_none(self):
        raw = {
            "variables": [],
            "constraints": [],
            "coverage": [{"ac_id": "AC-1", "status": "formalized"}],
        }
        ir = parse_ir(raw)
        self.assertIsNone(ir.coverage[0].subject)


class TestParseIrSubjectResolutionErrors(unittest.TestCase):
    def test_subject_resolution_not_an_object_raises(self):
        raw = {
            "variables": [
                {
                    "name": "n",
                    "sort": "Int",
                    "gloss": "g",
                    "subject_resolution": "nope",
                }
            ],
            "constraints": [],
            "coverage": [],
        }
        with self.assertRaises(IRParseError) as ctx:
            parse_ir(raw)
        msg = str(ctx.exception)
        self.assertIn("variables[0].subject_resolution", msg)
        self.assertIn("expected an object", msg)

    def test_subject_resolution_missing_status_raises(self):
        raw = {
            "variables": [
                {
                    "name": "n",
                    "sort": "Int",
                    "gloss": "g",
                    "subject_resolution": {"arm": "code"},
                }
            ],
            "constraints": [],
            "coverage": [],
        }
        with self.assertRaises(IRParseError) as ctx:
            parse_ir(raw)
        msg = str(ctx.exception)
        self.assertIn("variables[0].subject_resolution", msg)
        self.assertIn("status", msg)

    def test_subject_resolution_bad_arm_value_raises(self):
        """F2-style: well-typed str, not a valid SUBJECT_RESOLUTION_ARMS
        member -- the dataclass ValueError re-raise path."""
        raw = _raw_var_code_resolution(arm="bogus")
        with self.assertRaises(IRParseError) as ctx:
            parse_ir(raw)
        msg = str(ctx.exception)
        self.assertIn("variables[0].subject_resolution", msg)
        self.assertIn("arm", msg)

    def test_coverage_invalid_subject_combination_raises(self):
        """Coverage(status='formalized', subject=<non-None>) -- well-typed,
        rejected by the dataclass's status/subject agreement rule."""
        raw = {
            "variables": [],
            "constraints": [
                {
                    "ac_id": "AC-1",
                    "kind": "assertion",
                    "consequent": [{"var": "x", "op": "=", "value": 1}],
                }
            ],
            "coverage": [
                {"ac_id": "AC-1", "status": "formalized", "subject": "x"}
            ],
        }
        with self.assertRaises(IRParseError) as ctx:
            parse_ir(raw)
        self.assertIn("coverage[0]", str(ctx.exception))


class TestSubjectResolutionSerdeRoundTrip(unittest.TestCase):
    """parse_ir(dataclasses.asdict(ir)) == ir for every new record shape --
    the load-bearing round-trip invariant the whole scratch chain depends
    on (see _cli.py's _ir_to_dict / _ir_from_dict)."""

    def test_arm_code_round_trips(self):
        ir = parse_ir(_raw_var_code_resolution())
        self.assertEqual(parse_ir(dataclasses.asdict(ir)), ir)

    def test_arm_spec_round_trips(self):
        ir = parse_ir(_raw_var_spec_resolution())
        self.assertEqual(parse_ir(dataclasses.asdict(ir)), ir)

    def test_unresolved_round_trips(self):
        ir = parse_ir(_raw_var_unresolved())
        self.assertEqual(parse_ir(dataclasses.asdict(ir)), ir)

    def test_no_record_round_trips(self):
        raw = {
            "variables": [{"name": "n", "sort": "Int", "gloss": "g"}],
            "constraints": [],
            "coverage": [],
        }
        ir = parse_ir(raw)
        self.assertIsNone(ir.variables[0].subject_resolution)
        self.assertEqual(parse_ir(dataclasses.asdict(ir)), ir)

    def test_coverage_unresolved_subject_round_trips(self):
        raw = {
            "variables": [{"name": "shipped_state", "sort": "Bool", "gloss": "g"}],
            "constraints": [],
            "coverage": [
                {
                    "ac_id": "AC-1",
                    "status": "unresolved_subject",
                    "subject": "shipped_state",
                }
            ],
        }
        ir = parse_ir(raw)
        self.assertEqual(parse_ir(dataclasses.asdict(ir)), ir)

    def test_full_valid_ir_round_trips(self):
        """The pre-existing full-fixture IR (no new keys at all) still
        round-trips byte-for-byte -- back-compat confirmed at the
        dataclass-equality level, not just parse-without-raising."""
        ir = parse_ir(_full_valid_raw_ir())
        self.assertEqual(parse_ir(dataclasses.asdict(ir)), ir)


class TestSubjectResolutionBackwardCompatibility(unittest.TestCase):
    """Historical IR dicts (no subject_resolution / subject keys at all)
    still parse -- the pre-Phase-1 shape is a strict subset of the
    Phase-1 shape."""

    def test_historical_full_ir_parses_with_none_records(self):
        ir = parse_ir(_full_valid_raw_ir())
        for var in ir.variables:
            self.assertIsNone(var.subject_resolution)
        for cov in ir.coverage:
            self.assertIsNone(cov.subject)


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
# validate_ir -- unresolved_subject cases (Plan 82 Phase 1).
# ---------------------------------------------------------------------------


class TestValidateIrUnresolvedSubject(unittest.TestCase):
    def test_unresolved_subject_with_constraint_is_rejected(self):
        """The exact hole named in the brief: before this branch, a status
        that is neither 'formalized' nor a skip status was checked by
        nothing -- an unresolved_subject AC carrying a constraint (which
        Coverage's own __post_init__ cannot see, since it has no access to
        ir.constraints) passed validate_ir silently."""
        raw = {
            "variables": [{"name": "shipped_state", "sort": "Bool", "gloss": "g"}],
            "constraints": [
                {
                    "ac_id": "AC-1",
                    "kind": "assertion",
                    "consequent": [{"var": "shipped_state", "negated": False}],
                }
            ],
            "coverage": [
                {
                    "ac_id": "AC-1",
                    "status": "unresolved_subject",
                    "subject": "shipped_state",
                }
            ],
        }
        ir = parse_ir(raw)
        errors = validate_ir(ir, ["AC-1"])
        self.assertIn(
            "AC-1 marked unresolved_subject but has 1 constraint(s)", errors
        )

    def test_unresolved_subject_names_undeclared_variable(self):
        raw = {
            "variables": [],
            "constraints": [],
            "coverage": [
                {
                    "ac_id": "AC-1",
                    "status": "unresolved_subject",
                    "subject": "ghost_var",
                }
            ],
        }
        ir = parse_ir(raw)
        errors = validate_ir(ir, ["AC-1"])
        self.assertIn(
            "AC-1: unresolved_subject names undeclared variable 'ghost_var'",
            errors,
        )

    def test_unresolved_subject_naming_declared_variable_no_constraint_is_valid(
        self,
    ):
        """The named variable must carry a genuinely 'unresolved'
        subject_resolution record -- a no-record shape here was itself the
        evidence of the coherence gap this fixture now guards against (see
        TestValidateIrSubjectCoherence below)."""
        raw = {
            "variables": [
                {"name": "n_lerna_refs", "sort": "Int", "gloss": "g"},
                {
                    "name": "shipped_state",
                    "sort": "Bool",
                    "gloss": "g",
                    "subject_resolution": {
                        "status": "unresolved",
                        "searched": (
                            "grepped 'shipped' and 'mark_shipped' across "
                            "src/, 0 hits."
                        ),
                    },
                },
            ],
            "constraints": [
                {
                    "ac_id": "AC-1",
                    "kind": "assertion",
                    "consequent": [
                        {"var": "n_lerna_refs", "op": "=", "value": 0}
                    ],
                }
            ],
            "coverage": [
                {"ac_id": "AC-1", "status": "formalized"},
                {
                    "ac_id": "AC-2",
                    "status": "unresolved_subject",
                    "subject": "shipped_state",
                },
            ],
        }
        ir = parse_ir(raw)
        errors = validate_ir(ir, ["AC-1", "AC-2"])
        self.assertEqual(errors, [])


# ---------------------------------------------------------------------------
# validate_ir -- coverage-pointer coherence + constraint-exclusion
# (python-reviewer Finding 2, medium, ratified option (a)).
# ---------------------------------------------------------------------------


class TestValidateIrSubjectCoherence(unittest.TestCase):
    def test_target_variable_with_no_subject_resolution_record_is_rejected(
        self,
    ):
        """Dangling pointer: the named variable exists but carries no
        subject_resolution at all."""
        raw = {
            "variables": [{"name": "shipped_state", "sort": "Bool", "gloss": "g"}],
            "constraints": [],
            "coverage": [
                {
                    "ac_id": "AC-1",
                    "status": "unresolved_subject",
                    "subject": "shipped_state",
                }
            ],
        }
        ir = parse_ir(raw)
        errors = validate_ir(ir, ["AC-1"])
        self.assertIn(
            "AC-1: unresolved_subject variable 'shipped_state' has no "
            "subject_resolution record",
            errors,
        )

    def test_target_variable_with_resolved_record_is_rejected(self):
        """Contradicted pointer: the named variable's own record says
        'resolved', not 'unresolved'."""
        raw = {
            "variables": [
                {
                    "name": "shipped_state",
                    "sort": "Bool",
                    "gloss": "g",
                    "subject_resolution": {
                        "status": "resolved",
                        "arm": "code",
                        "citation": "src/orders.py",
                        "locator": "def mark_shipped",
                        "note": "found it",
                    },
                }
            ],
            "constraints": [],
            "coverage": [
                {
                    "ac_id": "AC-1",
                    "status": "unresolved_subject",
                    "subject": "shipped_state",
                }
            ],
        }
        ir = parse_ir(raw)
        errors = validate_ir(ir, ["AC-1"])
        self.assertIn(
            "AC-1: unresolved_subject variable 'shipped_state' has a "
            "resolved subject_resolution (expected unresolved)",
            errors,
        )

    def test_coherent_unresolved_target_is_valid(self):
        """The positive twin: a genuinely 'unresolved' record, named by
        exactly one coverage entry, with no constraint anywhere
        referencing it -- clean."""
        raw = {
            "variables": [
                {
                    "name": "shipped_state",
                    "sort": "Bool",
                    "gloss": "g",
                    "subject_resolution": {
                        "status": "unresolved",
                        "searched": "grepped 'shipped' across src/, 0 hits.",
                    },
                }
            ],
            "constraints": [],
            "coverage": [
                {
                    "ac_id": "AC-1",
                    "status": "unresolved_subject",
                    "subject": "shipped_state",
                }
            ],
        }
        ir = parse_ir(raw)
        errors = validate_ir(ir, ["AC-1"])
        self.assertEqual(errors, [])

    def test_constraint_under_a_different_ac_referencing_unresolved_variable_is_rejected(
        self,
    ):
        """The D1 twin, at full strength: AC-1's own coverage row is
        internally coherent (unresolved_subject, zero constraints, a
        genuinely unresolved target) -- the violation is a SEPARATE AC
        (AC-2, marked 'formalized', which the pre-existing agreement rule
        does not flag on its own) whose constraint illegally references
        the same unresolved variable. Proves the exclusion is IR-wide, not
        scoped to the unresolved variable's own AC's rows."""
        raw = {
            "variables": [
                {
                    "name": "shipped_state",
                    "sort": "Bool",
                    "gloss": "g",
                    "subject_resolution": {
                        "status": "unresolved",
                        "searched": "grepped 'shipped' across src/, 0 hits.",
                    },
                },
                {"name": "n_lerna_refs", "sort": "Int", "gloss": "g"},
            ],
            "constraints": [
                {
                    "ac_id": "AC-2",
                    "kind": "assertion",
                    "consequent": [{"var": "shipped_state", "negated": False}],
                }
            ],
            "coverage": [
                {
                    "ac_id": "AC-1",
                    "status": "unresolved_subject",
                    "subject": "shipped_state",
                },
                {"ac_id": "AC-2", "status": "formalized"},
            ],
        }
        ir = parse_ir(raw)
        errors = validate_ir(ir, ["AC-1", "AC-2"])
        self.assertIn(
            "AC-2: constraint references variable 'shipped_state' whose "
            "subject is unresolved",
            errors,
        )


# ---------------------------------------------------------------------------
# validate_citations -- D3's one filesystem-touching check.
# ---------------------------------------------------------------------------


class TestValidateCitations(unittest.TestCase):
    def setUp(self):
        # An OUTER tmp dir wrapping the actual workspace_root -- lets the
        # containment-escape tests place a real, readable file OUTSIDE
        # workspace_root (a sibling of it) to prove escape is rejected on
        # the path alone, not merely because the target happens to be
        # missing.
        self._outer_tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._outer_tmpdir.cleanup)
        self.workspace_root = os.path.join(self._outer_tmpdir.name, "workspace")
        os.makedirs(self.workspace_root)

    def _write(self, rel_path, content):
        abs_path = os.path.join(self.workspace_root, rel_path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "w", encoding="utf-8") as fh:
            fh.write(content)

    def test_nonexistent_cited_file_is_an_error(self):
        ir = parse_ir(_raw_var_code_resolution(citation="src/nope.py"))
        errors = validate_citations(ir, self.workspace_root)
        self.assertEqual(len(errors), 1)
        self.assertIn("does not exist", errors[0])
        self.assertIn("shipped_state", errors[0])

    def test_real_file_missing_cited_locator_is_an_error(self):
        self._write("src/orders.py", "def other_function():\n    pass\n")
        ir = parse_ir(_raw_var_code_resolution())
        errors = validate_citations(ir, self.workspace_root)
        self.assertEqual(len(errors), 1)
        self.assertIn("not found", errors[0])
        self.assertIn("shipped_state", errors[0])

    def test_real_file_with_cited_locator_is_clean(self):
        self._write("src/orders.py", "def mark_shipped():\n    pass\n")
        ir = parse_ir(_raw_var_code_resolution())
        errors = validate_citations(ir, self.workspace_root)
        self.assertEqual(errors, [])

    # -----------------------------------------------------------------
    # python-reviewer Finding 1 (high, confirmed empirically): a
    # citation must be rejected on containment ALONE, before any
    # filesystem touch -- never on file existence/content.
    # -----------------------------------------------------------------

    def test_absolute_citation_is_rejected_as_escape(self):
        """An absolute citation pointing at a REAL, matching file OUTSIDE
        workspace_root must still be rejected -- proves the rejection is
        on the path being absolute, not on the target missing or the
        locator not matching (both of which would pass here otherwise)."""
        outside_path = os.path.join(self._outer_tmpdir.name, "outside.py")
        with open(outside_path, "w", encoding="utf-8") as fh:
            fh.write("def mark_shipped():\n    pass\n")

        ir = parse_ir(_raw_var_code_resolution(citation=outside_path))
        errors = validate_citations(ir, self.workspace_root)
        self.assertEqual(len(errors), 1)
        self.assertIn("escapes workspace root", errors[0])
        self.assertIn("shipped_state", errors[0])

    def test_depth_correct_dot_dot_traversal_is_rejected_as_escape(self):
        """A single '..' from workspace_root lands exactly on a REAL,
        matching file placed as workspace_root's sibling -- rejected on
        containment, not on the (passing) existence/locator checks."""
        secret_path = os.path.join(self._outer_tmpdir.name, "secret.py")
        with open(secret_path, "w", encoding="utf-8") as fh:
            fh.write("def mark_shipped():\n    pass\n")

        ir = parse_ir(_raw_var_code_resolution(citation="../secret.py"))
        errors = validate_citations(ir, self.workspace_root)
        self.assertEqual(len(errors), 1)
        self.assertIn("escapes workspace root", errors[0])

    def test_legitimate_nested_relative_path_still_resolves(self):
        """Regression guard: a normal nested relative citation (no '..',
        not absolute) is unaffected by the containment guard."""
        self._write("src/pkg/mod.py", "def mark_shipped():\n    pass\n")
        ir = parse_ir(_raw_var_code_resolution(citation="src/pkg/mod.py"))
        errors = validate_citations(ir, self.workspace_root)
        self.assertEqual(errors, [])

    def test_spec_arm_does_not_trigger_the_file_check(self):
        """D3: a nonexistent path-like spec citation passes -- arm='spec'
        is never filesystem-checked."""
        ir = parse_ir(
            _raw_var_spec_resolution(citation="spec.md #this-path-does-not-exist")
        )
        errors = validate_citations(ir, self.workspace_root)
        self.assertEqual(errors, [])

    def test_unresolved_variable_is_not_filesystem_checked(self):
        ir = parse_ir(_raw_var_unresolved())
        errors = validate_citations(ir, self.workspace_root)
        self.assertEqual(errors, [])

    def test_variable_without_subject_resolution_is_skipped(self):
        raw = {
            "variables": [{"name": "n", "sort": "Int", "gloss": "g"}],
            "constraints": [],
            "coverage": [],
        }
        ir = parse_ir(raw)
        errors = validate_citations(ir, self.workspace_root)
        self.assertEqual(errors, [])

    def test_collects_multiple_errors_across_variables(self):
        raw = {
            "variables": [
                {
                    "name": "a",
                    "sort": "Bool",
                    "gloss": "g",
                    "subject_resolution": {
                        "status": "resolved",
                        "arm": "code",
                        "citation": "src/missing_a.py",
                        "locator": "x",
                        "note": "n",
                    },
                },
                {
                    "name": "b",
                    "sort": "Bool",
                    "gloss": "g",
                    "subject_resolution": {
                        "status": "resolved",
                        "arm": "code",
                        "citation": "src/missing_b.py",
                        "locator": "y",
                        "note": "n",
                    },
                },
            ],
            "constraints": [],
            "coverage": [],
        }
        ir = parse_ir(raw)
        errors = validate_citations(ir, self.workspace_root)
        self.assertEqual(len(errors), 2)


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
