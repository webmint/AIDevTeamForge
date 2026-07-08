"""Tests for src/devforge/lib/_design/_comparator.py -- the intent-reader x
built-reader x comparator engine (plan 53 Phase 4/5).

Coverage (directly mirrors the plan's "Verify" bullets for Phases 4+5):
  - region_found:false -> status NOT_COVERED (not CLEAN, not DEFECT); zero
    findings; not_covered_reason set
  - region_found:true + zero differences (no intent bag / binding at all)
    -> status CLEAN; fidelity_covered False
  - region_found:true + intent bag + binding + zero differences -> status
    CLEAN; fidelity_covered True
  - a floor violation (built bag alone, no anchor) -> status DEFECT; proves
    D9's structural non-vacuousness (the floor runs and can flag WITHOUT any
    intent bag / binding)
  - a fidelity value mismatch -> status DEFECT; finding lands in
    fidelity_findings
  - a fidelity geometry mismatch -> status DEFECT
  - malformed probe output never reaches compare() -- BagParseError is
    raised by load_bag/parse_bag before compare() is called (covered in
    test_bag.py; asserted here too via the intended call order to document
    the contract at this module's boundary)
  - intent bag given but binding is None -> fidelity NOT covered, floor
    still runs (D9)
  - intent bag given but binding has zero pairs -> fidelity NOT covered
    (an empty binding behaves like no binding for fidelity purposes)
  - a pair whose built element is absent -> NOT-COVERED for that pair
    (fidelity_not_covered_pairs), status stays CLEAN when nothing else flags
  - to_dict() serializes every field, findings as their to_dict() output
  - ComparisonResult.findings combines floor + fidelity in that order
  - an invalid status string raises ValueError (defensive constructor guard)
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _design._bag import Bag, BagParseError, load_bag  # noqa: E402
from _design._comparator import (  # noqa: E402
    STATUS_CLEAN,
    STATUS_DEFECT,
    STATUS_NOT_COVERED,
    ComparisonResult,
    compare,
)
from _design._schema import Binding, BindingPair  # noqa: E402

_ROUTE = "/dashboard"


def _style(**overrides):
    style = {
        "color": "rgb(0, 0, 0)",
        "background": "rgba(0, 0, 0, 0)",
        "border": "1px solid rgb(0, 0, 0)",
        "border_radius": "4px",
        "padding": "8px",
        "margin": "0px",
        "gap": "8px",
        "font_family": '"Inter", sans-serif',
        "font_size": "14px",
        "line_height": "20px",
        "font_weight": "400",
    }
    style.update(overrides)
    return style


def _geometry(width=100.0, height=40.0):
    return {
        "x": 0.0,
        "y": 0.0,
        "width": width,
        "height": height,
        "scroll_width": width,
        "client_width": width,
    }


def _element(found=True, style=None, geometry=None, overflow_x="visible", position="static"):
    if not found:
        return {"found": False}
    return {
        "found": True,
        "style": style if style is not None else _style(),
        "geometry": geometry if geometry is not None else _geometry(),
        "overflow_x": overflow_x,
        "position": position,
    }


class ComparatorNotCoveredTests(unittest.TestCase):
    def test_region_not_found_is_not_covered(self):
        built_bag = Bag(region_found=False, elements={})
        result = compare(built_bag, None, None, _ROUTE)
        self.assertEqual(result.status, STATUS_NOT_COVERED)
        self.assertFalse(result.region_found)
        self.assertEqual(result.findings, [])
        self.assertIsNotNone(result.not_covered_reason)
        self.assertFalse(result.fidelity_covered)

    def test_region_not_found_ignores_intent_bag_and_binding(self):
        # A not-found built region short-circuits before fidelity is even
        # consulted -- pass a populated intent bag/binding to prove they
        # are never reached.
        built_bag = Bag(region_found=False, elements={})
        intent_bag = Bag(region_found=True, elements={".ref": _element()})
        binding = Binding(route=_ROUTE, pairs=[BindingPair(".ref", "built-el")])
        result = compare(built_bag, intent_bag, binding, _ROUTE)
        self.assertEqual(result.status, STATUS_NOT_COVERED)


class ComparatorCleanTests(unittest.TestCase):
    def test_clean_with_no_intent_bag_or_binding(self):
        built_bag = Bag(region_found=True, elements={})
        result = compare(built_bag, None, None, _ROUTE)
        self.assertEqual(result.status, STATUS_CLEAN)
        self.assertTrue(result.region_found)
        self.assertFalse(result.fidelity_covered)
        self.assertEqual(result.findings, [])

    def test_clean_with_intent_bag_and_binding_zero_differences(self):
        built_bag = Bag(region_found=True, elements={"built-el": _element()})
        intent_bag = Bag(region_found=True, elements={".ref": _element()})
        binding = Binding(route=_ROUTE, pairs=[BindingPair(".ref", "built-el")])
        result = compare(built_bag, intent_bag, binding, _ROUTE)
        self.assertEqual(result.status, STATUS_CLEAN)
        self.assertTrue(result.fidelity_covered)
        self.assertEqual(result.findings, [])
        self.assertEqual(result.fidelity_not_covered_pairs, [])


class ComparatorDefectTests(unittest.TestCase):
    def test_floor_violation_alone_no_anchor_needed(self):
        # D9 structural non-vacuousness: a feature with NO anchor still
        # gets a real DEFECT from the floor.
        built_bag = Bag(
            region_found=True,
            elements={},
            overflow_candidates=[
                {"label": "a", "scroll_width": 500, "client_width": 100, "overflow_x": "visible"}
            ],
        )
        result = compare(built_bag, None, None, _ROUTE)
        self.assertEqual(result.status, STATUS_DEFECT)
        self.assertFalse(result.fidelity_covered)
        self.assertEqual(len(result.floor_findings), 1)
        self.assertEqual(result.floor_findings[0].kind, "overflow")

    def test_fidelity_value_mismatch_is_defect(self):
        built_bag = Bag(
            region_found=True,
            elements={"built-el": _element(style=_style(color="rgb(255,0,0)"))},
        )
        intent_bag = Bag(region_found=True, elements={".ref": _element()})
        binding = Binding(route=_ROUTE, pairs=[BindingPair(".ref", "built-el")])
        result = compare(built_bag, intent_bag, binding, _ROUTE)
        self.assertEqual(result.status, STATUS_DEFECT)
        self.assertEqual(len(result.fidelity_findings), 1)
        self.assertEqual(result.fidelity_findings[0].kind, "value_mismatch")

    def test_fidelity_geometry_mismatch_is_defect(self):
        built_bag = Bag(
            region_found=True,
            elements={"built-el": _element(geometry=_geometry(200, 40))},
        )
        intent_bag = Bag(
            region_found=True, elements={".ref": _element(geometry=_geometry(100, 40))}
        )
        binding = Binding(route=_ROUTE, pairs=[BindingPair(".ref", "built-el")])
        result = compare(built_bag, intent_bag, binding, _ROUTE)
        self.assertEqual(result.status, STATUS_DEFECT)
        self.assertEqual(len(result.fidelity_findings), 1)
        self.assertEqual(result.fidelity_findings[0].kind, "geometry_mismatch")


class ComparatorBoundaryAndSerializationTests(unittest.TestCase):
    def test_malformed_probe_output_raised_before_compare_reached(self):
        with self.assertRaises(BagParseError):
            load_bag("{not valid json")

    def test_intent_bag_given_binding_none_fidelity_not_covered_floor_runs(self):
        built_bag = Bag(
            region_found=True,
            elements={},
            fonts={'"Inter"': False},
        )
        intent_bag = Bag(region_found=True, elements={".ref": _element()})
        result = compare(built_bag, intent_bag, None, _ROUTE)
        self.assertFalse(result.fidelity_covered)
        self.assertEqual(result.status, STATUS_DEFECT)
        self.assertEqual(result.floor_findings[0].kind, "font_not_loaded")

    def test_binding_with_zero_pairs_behaves_like_no_binding(self):
        built_bag = Bag(region_found=True, elements={})
        intent_bag = Bag(region_found=True, elements={})
        binding = Binding(route=_ROUTE, pairs=[])
        result = compare(built_bag, intent_bag, binding, _ROUTE)
        self.assertFalse(result.fidelity_covered)
        self.assertEqual(result.status, STATUS_CLEAN)

    def test_pair_with_absent_built_element_is_not_covered_stays_clean(self):
        built_bag = Bag(region_found=True, elements={})
        intent_bag = Bag(region_found=True, elements={".ref": _element()})
        binding = Binding(route=_ROUTE, pairs=[BindingPair(".ref", "missing-el")])
        result = compare(built_bag, intent_bag, binding, _ROUTE)
        self.assertEqual(result.status, STATUS_CLEAN)
        self.assertTrue(result.fidelity_covered)
        self.assertEqual(result.fidelity_not_covered_pairs, ["missing-el"])
        self.assertEqual(result.fidelity_findings, [])

    def test_to_dict_serializes_every_field(self):
        built_bag = Bag(
            region_found=True,
            elements={"built-el": _element(style=_style(color="rgb(1,2,3)"))},
        )
        intent_bag = Bag(region_found=True, elements={".ref": _element()})
        binding = Binding(route=_ROUTE, pairs=[BindingPair(".ref", "built-el")])
        result = compare(built_bag, intent_bag, binding, _ROUTE)
        d = result.to_dict()
        self.assertEqual(d["status"], STATUS_DEFECT)
        self.assertTrue(d["region_found"])
        self.assertIsNone(d["not_covered_reason"])
        self.assertEqual(len(d["floor_findings"]), 0)
        self.assertTrue(d["fidelity_covered"])
        self.assertEqual(len(d["fidelity_findings"]), 1)
        self.assertEqual(d["fidelity_findings"][0]["kind"], "value_mismatch")
        self.assertEqual(d["fidelity_not_covered_pairs"], [])

    def test_findings_property_combines_floor_then_fidelity(self):
        built_bag = Bag(
            region_found=True,
            elements={"built-el": _element(style=_style(color="rgb(1,2,3)"))},
            overflow_candidates=[
                {"label": "a", "scroll_width": 500, "client_width": 100, "overflow_x": "visible"}
            ],
        )
        intent_bag = Bag(region_found=True, elements={".ref": _element()})
        binding = Binding(route=_ROUTE, pairs=[BindingPair(".ref", "built-el")])
        result = compare(built_bag, intent_bag, binding, _ROUTE)
        kinds = [f.kind for f in result.findings]
        self.assertEqual(kinds, ["overflow", "value_mismatch"])

    def test_invalid_status_raises_value_error(self):
        with self.assertRaises(ValueError):
            ComparisonResult(
                status="BOGUS",
                region_found=True,
                floor_findings=[],
                fidelity_covered=False,
                fidelity_findings=[],
                fidelity_not_covered_pairs=[],
            )


if __name__ == "__main__":
    unittest.main()
