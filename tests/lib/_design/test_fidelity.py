"""Tests for src/devforge/lib/_design/_fidelity.py -- anchor-gated value +
geometry fidelity checks (plan 53 D9, Phase 5).

Coverage:
  compare_pair_values:
    - identical style dicts -> no findings
    - a single property mismatch (color) -> one value_mismatch finding,
      severity Medium
    - a font_family mismatch -> severity High (the one elevated property)
    - whitespace-only differences ("8px" vs " 8px ") -> normalized, no
      finding (avoids a false positive from cosmetic formatting)
    - multiple mismatched properties -> one finding per property
  compare_pair_geometry:
    - identical width/height -> no findings
    - a width mismatch beyond tolerance -> one geometry_mismatch finding
    - a height mismatch beyond tolerance -> one geometry_mismatch finding
    - a mismatch WITHIN tolerance (subpixel/relative) -> no finding
    - a mismatch just beyond the relative tolerance on a large box -> flags
  run_fidelity:
    - built_testid absent from built bag's elements -> NOT-COVERED for that
      pair (no finding, testid appears in not_covered_pairs)
    - anchor_selector absent from intent bag's elements -> NOT-COVERED for
      that pair
    - built element found=false -> NOT-COVERED for that pair
    - intent element found=false -> NOT-COVERED for that pair
    - a pair with a genuine mismatch -> findings + NOT in not_covered_pairs
    - multiple pairs: one covered+clean, one covered+mismatched, one
      not-covered -> exactly the right partition
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _design._bag import Bag  # noqa: E402
from _design._fidelity import (  # noqa: E402
    compare_pair_geometry,
    compare_pair_values,
    run_fidelity,
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


def _element(found=True, style=None, geometry=None):
    if not found:
        return {"found": False}
    return {
        "found": True,
        "style": style if style is not None else _style(),
        "geometry": geometry if geometry is not None else _geometry(),
        "overflow_x": "visible",
        "position": "static",
    }


def _pair(anchor_selector=".ref", built_testid="built-el"):
    return BindingPair(anchor_selector=anchor_selector, built_testid=built_testid)


class ComparePairValuesTests(unittest.TestCase):
    def test_identical_styles_no_findings(self):
        built = _element()
        intent = _element()
        findings = compare_pair_values(_pair(), built, intent, _ROUTE)
        self.assertEqual(findings, [])

    def test_color_mismatch_flags_medium(self):
        built = _element(style=_style(color="rgb(255, 0, 0)"))
        intent = _element()
        findings = compare_pair_values(_pair(), built, intent, _ROUTE)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].property, "color")
        self.assertEqual(findings[0].severity, "Medium")
        self.assertEqual(findings[0].kind, "value_mismatch")

    def test_font_family_mismatch_flags_high(self):
        built = _element(style=_style(font_family='"Roboto"'))
        intent = _element()
        findings = compare_pair_values(_pair(), built, intent, _ROUTE)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].property, "font_family")
        self.assertEqual(findings[0].severity, "High")

    def test_whitespace_only_difference_normalized_no_finding(self):
        built = _element(style=_style(padding="8px"))
        intent = _element(style=_style(padding="  8px  "))
        findings = compare_pair_values(_pair(), built, intent, _ROUTE)
        self.assertEqual(findings, [])

    def test_multiple_mismatches_one_finding_each(self):
        built = _element(style=_style(color="rgb(255,0,0)", font_size="16px"))
        intent = _element()
        findings = compare_pair_values(_pair(), built, intent, _ROUTE)
        props = sorted(f.property for f in findings)
        self.assertEqual(props, ["color", "font_size"])

    def test_finding_carries_pair_selector_and_route(self):
        built = _element(style=_style(color="rgb(255,0,0)"))
        intent = _element()
        pair = _pair(anchor_selector=".hero", built_testid="hero-region")
        findings = compare_pair_values(pair, built, intent, _ROUTE)
        self.assertEqual(findings[0].selector, "hero-region")
        self.assertEqual(findings[0].file, _ROUTE)


class ComparePairGeometryTests(unittest.TestCase):
    def test_identical_geometry_no_findings(self):
        built = _element(geometry=_geometry(100, 40))
        intent = _element(geometry=_geometry(100, 40))
        findings = compare_pair_geometry(_pair(), built, intent, _ROUTE)
        self.assertEqual(findings, [])

    def test_width_mismatch_beyond_tolerance_flags(self):
        built = _element(geometry=_geometry(150, 40))
        intent = _element(geometry=_geometry(100, 40))
        findings = compare_pair_geometry(_pair(), built, intent, _ROUTE)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].property, "width")
        self.assertEqual(findings[0].kind, "geometry_mismatch")

    def test_height_mismatch_beyond_tolerance_flags(self):
        built = _element(geometry=_geometry(100, 80))
        intent = _element(geometry=_geometry(100, 40))
        findings = compare_pair_geometry(_pair(), built, intent, _ROUTE)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].property, "height")

    def test_mismatch_within_tolerance_no_finding(self):
        # tolerance = max(2.0, 100*0.02) = 2.0px; a 1.5px diff is within it.
        built = _element(geometry=_geometry(101.5, 40))
        intent = _element(geometry=_geometry(100, 40))
        findings = compare_pair_geometry(_pair(), built, intent, _ROUTE)
        self.assertEqual(findings, [])

    def test_large_box_relative_tolerance_flags_beyond_2_percent(self):
        # expected width 1000 -> tolerance = max(2.0, 20.0) = 20.0px;
        # a 25px diff exceeds it.
        built = _element(geometry=_geometry(1025, 40))
        intent = _element(geometry=_geometry(1000, 40))
        findings = compare_pair_geometry(_pair(), built, intent, _ROUTE)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].property, "width")


class RunFidelityTests(unittest.TestCase):
    def _bags(self, built_elements, intent_elements):
        built_bag = Bag(region_found=True, elements=built_elements)
        intent_bag = Bag(region_found=True, elements=intent_elements)
        return built_bag, intent_bag

    def test_built_testid_absent_is_not_covered(self):
        binding = Binding(route=_ROUTE, pairs=[_pair(".ref", "missing-testid")])
        built_bag, intent_bag = self._bags({}, {".ref": _element()})
        findings, not_covered = run_fidelity(built_bag, intent_bag, binding, _ROUTE)
        self.assertEqual(findings, [])
        self.assertEqual(not_covered, ["missing-testid"])

    def test_anchor_selector_absent_is_not_covered(self):
        binding = Binding(route=_ROUTE, pairs=[_pair(".missing-ref", "built-el")])
        built_bag, intent_bag = self._bags({"built-el": _element()}, {})
        findings, not_covered = run_fidelity(built_bag, intent_bag, binding, _ROUTE)
        self.assertEqual(findings, [])
        self.assertEqual(not_covered, ["built-el"])

    def test_built_found_false_is_not_covered(self):
        binding = Binding(route=_ROUTE, pairs=[_pair(".ref", "built-el")])
        built_bag, intent_bag = self._bags(
            {"built-el": _element(found=False)}, {".ref": _element()}
        )
        findings, not_covered = run_fidelity(built_bag, intent_bag, binding, _ROUTE)
        self.assertEqual(findings, [])
        self.assertEqual(not_covered, ["built-el"])

    def test_intent_found_false_is_not_covered(self):
        binding = Binding(route=_ROUTE, pairs=[_pair(".ref", "built-el")])
        built_bag, intent_bag = self._bags(
            {"built-el": _element()}, {".ref": _element(found=False)}
        )
        findings, not_covered = run_fidelity(built_bag, intent_bag, binding, _ROUTE)
        self.assertEqual(findings, [])
        self.assertEqual(not_covered, ["built-el"])

    def test_genuine_mismatch_produces_findings_not_not_covered(self):
        binding = Binding(route=_ROUTE, pairs=[_pair(".ref", "built-el")])
        built_bag, intent_bag = self._bags(
            {"built-el": _element(style=_style(color="rgb(255,0,0)"))},
            {".ref": _element()},
        )
        findings, not_covered = run_fidelity(built_bag, intent_bag, binding, _ROUTE)
        self.assertEqual(len(findings), 1)
        self.assertEqual(not_covered, [])

    def test_partition_across_multiple_pairs(self):
        pairs = [
            _pair(".ref-clean", "built-clean"),
            _pair(".ref-mismatch", "built-mismatch"),
            _pair(".ref-missing", "built-missing"),
        ]
        binding = Binding(route=_ROUTE, pairs=pairs)
        built_elements = {
            "built-clean": _element(),
            "built-mismatch": _element(style=_style(color="rgb(1,2,3)")),
            # "built-missing" intentionally absent
        }
        intent_elements = {
            ".ref-clean": _element(),
            ".ref-mismatch": _element(),
            ".ref-missing": _element(),
        }
        built_bag, intent_bag = self._bags(built_elements, intent_elements)
        findings, not_covered = run_fidelity(built_bag, intent_bag, binding, _ROUTE)
        self.assertEqual(not_covered, ["built-missing"])
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].selector, "built-mismatch")


if __name__ == "__main__":
    unittest.main()
