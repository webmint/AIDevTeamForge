"""Tests for src/devforge/lib/_design/_bag.py -- Bag + parse_bag/load_bag
(plan 53 Phase 4).

Real-fixture discipline note: the bag's real PRODUCER is a JS
`evaluate_script` collector (js/built_reader.js / js/intent_reader.js) that
only runs against a live Chrome MCP render (verified at Phase 9 e2e per
OQ-A -- jsdom has no layout engine or font loading, so a Python-side node/
jsdom round-trip would be theatre, not verification). So these tests build
synthetic JSON payloads that are BYTE-FOR-BYTE the documented contract (see
_bag.py's module docstring, which is kept in lockstep with both .js files'
header comments) -- that IS the round-trip discipline at this layer, mirrored
by _fidelity.py's tests using Bag objects built the same way.

Coverage:
  parse_bag / load_bag:
    - region_found:false with a minimal payload -> Bag(region_found=False),
      NOT an error (honesty invariant #4 -- valid data, not malformed)
    - region_found:true + a well-formed elements/overflow/clip/fonts payload
      -> Bag with every field populated correctly
    - a found=false element entry -> Bag.elements[key]['found'] is False,
      no style/geometry required
    - malformed JSON text -> BagParseError (load_bag)
    - missing top-level 'region_found' -> BagParseError naming the field
    - missing top-level 'elements' -> BagParseError naming the field
    - region_found wrong type (string, not bool) -> BagParseError
    - elements wrong type (list, not dict) -> BagParseError
    - an element found=true missing 'style' -> BagParseError
    - an element found=true missing a required style key -> BagParseError
    - an element found=true with a non-string style value -> BagParseError
    - an element found=true missing 'geometry' -> BagParseError
    - an element found=true missing a required geometry key -> BagParseError
    - an element found=true with a non-numeric geometry value -> BagParseError
    - an element found=true with a bool geometry value -> BagParseError
      (bool is an int subclass; must be explicitly rejected)
    - overflow_candidates / clip_candidates / fonts default to
      empty when absent (the intent-side shape)
    - overflow_candidates wrong type -> BagParseError
    - an overflow candidate missing a required key -> BagParseError
    - clip_candidates wrong type -> BagParseError
    - a clip candidate missing child_rect/parent_rect -> BagParseError
    - a clip candidate's child_rect missing a numeric key -> BagParseError
    - fonts wrong type -> BagParseError
    - a fonts value that is not a bool -> BagParseError
    - top-level payload not a dict -> BagParseError
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _design._bag import Bag, BagParseError, load_bag, parse_bag  # noqa: E402


def _style():
    return {
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


def _geometry(width=100.0, height=40.0, scroll_width=100.0, client_width=100.0):
    return {
        "x": 12.0,
        "y": 34.0,
        "width": width,
        "height": height,
        "scroll_width": scroll_width,
        "client_width": client_width,
    }


def _found_element(**overrides):
    el = {
        "found": True,
        "style": _style(),
        "geometry": _geometry(),
        "overflow_x": "visible",
        "position": "static",
    }
    el.update(overrides)
    return el


def _rect(x=0, y=0, width=50, height=50):
    return {"x": x, "y": y, "width": width, "height": height}


def _full_payload():
    return {
        "region_found": True,
        "elements": {"container": _found_element(), "missing-el": {"found": False}},
        "overflow_candidates": [
            {
                "label": "div.a",
                "scroll_width": 300.0,
                "client_width": 200.0,
                "overflow_x": "visible",
            }
        ],
        "clip_candidates": [
            {
                "label": "div.b",
                "child_rect": _rect(0, 0, 60, 60),
                "parent_rect": _rect(0, 0, 40, 40),
                "parent_overflow": "hidden",
                "child_position": "static",
            }
        ],
        "fonts": {'"Inter"': True, "sans-serif": True},
    }


class ParseBagRegionFoundTests(unittest.TestCase):
    def test_region_found_false_minimal_is_valid(self):
        bag = parse_bag({"region_found": False, "elements": {}})
        self.assertIsInstance(bag, Bag)
        self.assertFalse(bag.region_found)
        self.assertEqual(bag.elements, {})
        self.assertEqual(bag.overflow_candidates, [])
        self.assertEqual(bag.clip_candidates, [])
        self.assertEqual(bag.fonts, {})

    def test_region_found_true_full_payload(self):
        bag = parse_bag(_full_payload())
        self.assertTrue(bag.region_found)
        self.assertIn("container", bag.elements)
        self.assertTrue(bag.elements["container"]["found"])
        self.assertFalse(bag.elements["missing-el"]["found"])
        self.assertEqual(len(bag.overflow_candidates), 1)
        self.assertEqual(len(bag.clip_candidates), 1)
        self.assertEqual(bag.fonts['"Inter"'], True)

    def test_found_false_element_needs_no_style_or_geometry(self):
        bag = parse_bag({"region_found": True, "elements": {"x": {"found": False}}})
        self.assertFalse(bag.elements["x"]["found"])

    def test_optional_fields_default_empty(self):
        bag = parse_bag({"region_found": True, "elements": {}})
        self.assertEqual(bag.overflow_candidates, [])
        self.assertEqual(bag.clip_candidates, [])
        self.assertEqual(bag.fonts, {})


class LoadBagJsonTests(unittest.TestCase):
    def test_load_bag_round_trips_full_payload(self):
        text = json.dumps(_full_payload())
        bag = load_bag(text)
        self.assertTrue(bag.region_found)

    def test_load_bag_malformed_json_text(self):
        with self.assertRaises(BagParseError):
            load_bag("{not valid json")

    def test_load_bag_non_string_json_root_scalar(self):
        with self.assertRaises(BagParseError):
            load_bag("42")


class ParseBagMalformedTopLevelTests(unittest.TestCase):
    def test_top_level_not_a_dict(self):
        with self.assertRaises(BagParseError):
            parse_bag(["not", "a", "dict"])

    def test_missing_region_found(self):
        with self.assertRaises(BagParseError) as ctx:
            parse_bag({"elements": {}})
        self.assertIn("region_found", str(ctx.exception))

    def test_region_found_wrong_type(self):
        with self.assertRaises(BagParseError) as ctx:
            parse_bag({"region_found": "true", "elements": {}})
        self.assertIn("region_found", str(ctx.exception))

    def test_missing_elements(self):
        with self.assertRaises(BagParseError) as ctx:
            parse_bag({"region_found": True})
        self.assertIn("elements", str(ctx.exception))

    def test_elements_wrong_type(self):
        with self.assertRaises(BagParseError) as ctx:
            parse_bag({"region_found": True, "elements": []})
        self.assertIn("elements", str(ctx.exception))


class ParseBagMalformedElementTests(unittest.TestCase):
    def test_element_missing_found(self):
        with self.assertRaises(BagParseError) as ctx:
            parse_bag({"region_found": True, "elements": {"x": {}}})
        self.assertIn("found", str(ctx.exception))

    def test_element_found_wrong_type(self):
        with self.assertRaises(BagParseError):
            parse_bag({"region_found": True, "elements": {"x": {"found": "yes"}}})

    def test_found_true_missing_style(self):
        el = _found_element()
        del el["style"]
        with self.assertRaises(BagParseError) as ctx:
            parse_bag({"region_found": True, "elements": {"x": el}})
        self.assertIn("style", str(ctx.exception))

    def test_found_true_missing_required_style_key(self):
        el = _found_element()
        del el["style"]["color"]
        with self.assertRaises(BagParseError) as ctx:
            parse_bag({"region_found": True, "elements": {"x": el}})
        self.assertIn("color", str(ctx.exception))

    def test_found_true_style_value_not_string(self):
        el = _found_element()
        el["style"]["color"] = 123
        with self.assertRaises(BagParseError):
            parse_bag({"region_found": True, "elements": {"x": el}})

    def test_found_true_missing_geometry(self):
        el = _found_element()
        del el["geometry"]
        with self.assertRaises(BagParseError) as ctx:
            parse_bag({"region_found": True, "elements": {"x": el}})
        self.assertIn("geometry", str(ctx.exception))

    def test_found_true_missing_required_geometry_key(self):
        el = _found_element()
        del el["geometry"]["width"]
        with self.assertRaises(BagParseError) as ctx:
            parse_bag({"region_found": True, "elements": {"x": el}})
        self.assertIn("width", str(ctx.exception))

    def test_found_true_geometry_value_not_numeric(self):
        el = _found_element()
        el["geometry"]["width"] = "100px"
        with self.assertRaises(BagParseError):
            parse_bag({"region_found": True, "elements": {"x": el}})

    def test_found_true_geometry_value_bool_rejected(self):
        # bool is an int subclass in Python -- must be explicitly rejected,
        # not silently accepted as a "number".
        el = _found_element()
        el["geometry"]["width"] = True
        with self.assertRaises(BagParseError):
            parse_bag({"region_found": True, "elements": {"x": el}})

    def test_found_true_missing_overflow_x(self):
        el = _found_element()
        del el["overflow_x"]
        with self.assertRaises(BagParseError) as ctx:
            parse_bag({"region_found": True, "elements": {"x": el}})
        self.assertIn("overflow_x", str(ctx.exception))

    def test_found_true_missing_position(self):
        el = _found_element()
        del el["position"]
        with self.assertRaises(BagParseError) as ctx:
            parse_bag({"region_found": True, "elements": {"x": el}})
        self.assertIn("position", str(ctx.exception))


class ParseBagMalformedOverflowClipFontsTests(unittest.TestCase):
    def test_overflow_candidates_wrong_type(self):
        with self.assertRaises(BagParseError):
            parse_bag({"region_found": True, "elements": {}, "overflow_candidates": {}})

    def test_overflow_candidate_missing_key(self):
        cand = {"label": "x", "scroll_width": 1.0, "client_width": 1.0}
        with self.assertRaises(BagParseError) as ctx:
            parse_bag({"region_found": True, "elements": {}, "overflow_candidates": [cand]})
        self.assertIn("overflow_candidates[0]", str(ctx.exception))

    def test_clip_candidates_wrong_type(self):
        with self.assertRaises(BagParseError):
            parse_bag({"region_found": True, "elements": {}, "clip_candidates": "nope"})

    def test_clip_candidate_missing_child_rect(self):
        cand = {
            "label": "x",
            "parent_rect": _rect(),
            "parent_overflow": "hidden",
            "child_position": "static",
        }
        with self.assertRaises(BagParseError) as ctx:
            parse_bag({"region_found": True, "elements": {}, "clip_candidates": [cand]})
        self.assertIn("child_rect", str(ctx.exception))

    def test_clip_candidate_rect_missing_numeric_key(self):
        bad_rect = _rect()
        del bad_rect["width"]
        cand = {
            "label": "x",
            "child_rect": bad_rect,
            "parent_rect": _rect(),
            "parent_overflow": "hidden",
            "child_position": "static",
        }
        with self.assertRaises(BagParseError) as ctx:
            parse_bag({"region_found": True, "elements": {}, "clip_candidates": [cand]})
        self.assertIn("width", str(ctx.exception))

    def test_fonts_wrong_type(self):
        with self.assertRaises(BagParseError):
            parse_bag({"region_found": True, "elements": {}, "fonts": ["Inter"]})

    def test_fonts_value_not_bool(self):
        with self.assertRaises(BagParseError):
            parse_bag({"region_found": True, "elements": {}, "fonts": {"Inter": "yes"}})


if __name__ == "__main__":
    unittest.main()
