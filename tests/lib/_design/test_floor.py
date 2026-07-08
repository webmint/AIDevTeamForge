"""Tests for src/devforge/lib/_design/_floor.py -- the always-on, anchor-FREE
sanity floor (plan 53 D9/D10/Phase 5).

Fixtures are synthetic bag candidate dicts matching the exact contract
_bag.py validates (see that module + js/built_reader.js's header for the
authoritative shape) -- this IS the deterministic-guarantee discipline: the
predicates are exercised against every documented boundary case, not just a
happy path.

Coverage:
  check_overflow:
    - scrollWidth > clientWidth + overflow-x: visible -> flags
    - scrollWidth > clientWidth + overflow-x: hidden -> flags
    - scrollWidth > clientWidth + overflow-x: auto -> NO flag (exempt)
    - scrollWidth > clientWidth + overflow-x: scroll -> NO flag (exempt)
    - scrollWidth > clientWidth + an unlisted overflow-x value -> NO flag
      (conservative default -- only visible/hidden ever flag)
    - scrollWidth == clientWidth + overflow-x: visible -> NO flag
    - scrollWidth < clientWidth + overflow-x: visible -> NO flag
    - multiple candidates -> only the flagged ones produce findings, in order
  check_clip:
    - static child rect NOT contained in an overflow:hidden parent -> flags
    - static child rect NOT contained in an overflow:clip parent -> flags
    - static child rect NOT contained in an overflow:auto parent -> flags
    - relative child, same shape -> flags (relative is a flag position)
    - absolute-positioned escapee out of a clipping parent -> NO flag (exempt)
    - fixed-positioned escapee -> NO flag (exempt)
    - static child rect CONTAINED in an overflow:hidden parent -> NO flag
    - static child rect not contained, but parent overflow is 'visible'
      (not in the flag set) -> NO flag
    - a rect that overflows by less than the epsilon tolerance -> NO flag
      (subpixel rounding is not a real clip)
  check_fonts:
    - a declared-but-unloaded quoted custom family -> flags font_not_loaded
    - a loaded quoted custom family -> NO flag
    - a generic family (sans-serif) reported unloaded -> NO flag (skipped
      regardless of the measured bool -- plan 53 D10)
    - -apple-system reported unloaded -> NO flag (skipped, case-insensitive)
    - multiple families -> only the genuinely-unloaded custom one flags
    - FIX F3/F4 (decision-side, js/built_reader.js's collectFonts is the
      producer -- not unit-tested per OQ-A; these prove the Python DECISION
      given the fixed collector's fonts-dict shape):
        - F3: an opt-in pair element's first custom family, unloaded, while
          its style value-compare would still pass -> font_not_loaded
          flagged (the D10 vacuous-pass case reproduced at element level,
          not just :root/container)
        - F4: a stack whose first family is custom+loaded but a SECOND
          custom family is unloaded never even enters the fonts dict
          (collectFonts now emits only the first token per element) -- so
          check_fonts sees no key for the second family and cannot
          false-flag it
  run_floor:
    - combines overflow + clip + font findings from a full Bag
    - a bag with all-clean floor candidates -> zero findings
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
from _design._floor import check_clip, check_fonts, check_overflow, run_floor  # noqa: E402

_ROUTE = "/dashboard"


def _rect(x=0, y=0, width=50, height=50):
    return {"x": x, "y": y, "width": width, "height": height}


class CheckOverflowTests(unittest.TestCase):
    def _cand(self, scroll_width, client_width, overflow_x, label="div.a"):
        return {
            "label": label,
            "scroll_width": scroll_width,
            "client_width": client_width,
            "overflow_x": overflow_x,
        }

    def test_visible_overflow_flags(self):
        findings = check_overflow([self._cand(300, 200, "visible")], _ROUTE)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].kind, "overflow")
        self.assertEqual(findings[0].file, _ROUTE)
        self.assertEqual(findings[0].selector, "div.a")

    def test_hidden_overflow_flags(self):
        findings = check_overflow([self._cand(300, 200, "hidden")], _ROUTE)
        self.assertEqual(len(findings), 1)

    def test_auto_scroll_container_exempt(self):
        findings = check_overflow([self._cand(300, 200, "auto")], _ROUTE)
        self.assertEqual(findings, [])

    def test_scroll_container_exempt(self):
        findings = check_overflow([self._cand(300, 200, "scroll")], _ROUTE)
        self.assertEqual(findings, [])

    def test_unlisted_overflow_value_exempt(self):
        findings = check_overflow([self._cand(300, 200, "clip")], _ROUTE)
        self.assertEqual(findings, [])

    def test_equal_widths_no_flag(self):
        findings = check_overflow([self._cand(200, 200, "visible")], _ROUTE)
        self.assertEqual(findings, [])

    def test_scroll_narrower_than_client_no_flag(self):
        findings = check_overflow([self._cand(150, 200, "visible")], _ROUTE)
        self.assertEqual(findings, [])

    def test_multiple_candidates_only_flagged_ones_produce_findings(self):
        cands = [
            self._cand(300, 200, "visible", label="div.a"),
            self._cand(200, 200, "visible", label="div.b"),
            self._cand(400, 100, "hidden", label="div.c"),
        ]
        findings = check_overflow(cands, _ROUTE)
        labels = [f.selector for f in findings]
        self.assertEqual(labels, ["div.a", "div.c"])


class CheckClipTests(unittest.TestCase):
    def _cand(self, child_rect, parent_rect, parent_overflow, child_position, label="div.b"):
        return {
            "label": label,
            "child_rect": child_rect,
            "parent_rect": parent_rect,
            "parent_overflow": parent_overflow,
            "child_position": child_position,
        }

    def test_static_child_clipped_by_overflow_hidden(self):
        cand = self._cand(_rect(0, 0, 60, 60), _rect(0, 0, 40, 40), "hidden", "static")
        findings = check_clip([cand], _ROUTE)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].kind, "clip")

    def test_static_child_clipped_by_overflow_clip(self):
        cand = self._cand(_rect(0, 0, 60, 60), _rect(0, 0, 40, 40), "clip", "static")
        findings = check_clip([cand], _ROUTE)
        self.assertEqual(len(findings), 1)

    def test_static_child_clipped_by_overflow_auto(self):
        cand = self._cand(_rect(0, 0, 60, 60), _rect(0, 0, 40, 40), "auto", "static")
        findings = check_clip([cand], _ROUTE)
        self.assertEqual(len(findings), 1)

    def test_relative_child_clipped_flags(self):
        cand = self._cand(_rect(0, 0, 60, 60), _rect(0, 0, 40, 40), "hidden", "relative")
        findings = check_clip([cand], _ROUTE)
        self.assertEqual(len(findings), 1)

    def test_absolute_positioned_escapee_exempt(self):
        cand = self._cand(_rect(0, 0, 60, 60), _rect(0, 0, 40, 40), "hidden", "absolute")
        findings = check_clip([cand], _ROUTE)
        self.assertEqual(findings, [])

    def test_fixed_positioned_escapee_exempt(self):
        cand = self._cand(_rect(0, 0, 60, 60), _rect(0, 0, 40, 40), "hidden", "fixed")
        findings = check_clip([cand], _ROUTE)
        self.assertEqual(findings, [])

    def test_contained_child_no_flag(self):
        cand = self._cand(_rect(5, 5, 20, 20), _rect(0, 0, 40, 40), "hidden", "static")
        findings = check_clip([cand], _ROUTE)
        self.assertEqual(findings, [])

    def test_parent_overflow_visible_not_in_flag_set_no_flag(self):
        cand = self._cand(_rect(0, 0, 60, 60), _rect(0, 0, 40, 40), "visible", "static")
        findings = check_clip([cand], _ROUTE)
        self.assertEqual(findings, [])

    def test_subpixel_overflow_within_epsilon_no_flag(self):
        # child extends 0.2px beyond parent -- within the 0.5px epsilon.
        cand = self._cand(_rect(0, 0, 40.2, 40), _rect(0, 0, 40, 40), "hidden", "static")
        findings = check_clip([cand], _ROUTE)
        self.assertEqual(findings, [])


class CheckFontsTests(unittest.TestCase):
    def test_unloaded_custom_family_flags(self):
        findings = check_fonts({'"Inter"': False}, _ROUTE)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].kind, "font_not_loaded")
        self.assertEqual(findings[0].selector, '"Inter"')

    def test_loaded_custom_family_no_flag(self):
        findings = check_fonts({'"Inter"': True}, _ROUTE)
        self.assertEqual(findings, [])

    def test_generic_family_unloaded_is_skipped(self):
        findings = check_fonts({"sans-serif": False}, _ROUTE)
        self.assertEqual(findings, [])

    def test_apple_system_unloaded_is_skipped_case_insensitive(self):
        findings = check_fonts({"-Apple-System": False}, _ROUTE)
        self.assertEqual(findings, [])

    def test_mixed_families_only_custom_unloaded_flags(self):
        fonts = {'"Inter"': False, "sans-serif": False, '"Roboto"': True}
        findings = check_fonts(fonts, _ROUTE)
        self.assertEqual([f.selector for f in findings], ['"Inter"'])

    def test_font_not_loaded_does_not_block_value_compare_semantics(self):
        # D10's special case: the finding's title still names the RIGHT
        # family (the declaration matches) -- it is the LOAD state, not the
        # value, that is wrong. Assert the family name appears verbatim so a
        # reader sees the declared value matched but still isn't loaded.
        findings = check_fonts({'"Inter"': False}, _ROUTE)
        self.assertIn('"Inter"', findings[0].title)
        self.assertIn('"Inter"', findings[0].explanation)

    def test_f3_opt_in_pair_element_first_family_unloaded_flags(self):
        # FIX F3: the fixed collectFonts samples EACH measured built_testid
        # pair element, not just :root + container -- so a pair element
        # whose own first custom font-family is declared-but-unloaded must
        # be flagged even though a value-compare (see _fidelity.py) on that
        # same element would pass vacuously (the declared family name still
        # matches; the font simply never loaded and fell back). The bag's
        # "fonts" dict is keyed by family token regardless of WHICH element
        # contributed it -- this is the element-level reproduction of D10's
        # root/container-only special case.
        fonts = {"Custom Element Font": False}
        findings = check_fonts(fonts, _ROUTE)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].kind, "font_not_loaded")
        self.assertEqual(findings[0].selector, "Custom Element Font")

    def test_f4_second_family_in_stack_never_enters_dict_no_false_positive(self):
        # FIX F4: collectFonts now emits only the FIRST family token of each
        # computed font-family stack. For a stack like
        # `"Primary", "FallbackCustom", sans-serif` where Primary is loaded,
        # only "Primary" ever reaches the fonts dict -- "FallbackCustom" (a
        # legitimate secondary fallback) is never a key. Model that exact
        # post-fix shape: assert the dict has no entry for the second
        # family, and that check_fonts over the (correctly shaped) dict
        # produces zero findings -- the false positive cannot occur because
        # the offending key is structurally absent, not because a predicate
        # happened to exempt it.
        fonts = {"Primary": True}
        self.assertNotIn("FallbackCustom", fonts)
        findings = check_fonts(fonts, _ROUTE)
        self.assertEqual(findings, [])


class RunFloorTests(unittest.TestCase):
    def test_combines_all_three_checks(self):
        bag = Bag(
            region_found=True,
            elements={},
            overflow_candidates=[
                {"label": "a", "scroll_width": 300, "client_width": 200, "overflow_x": "visible"}
            ],
            clip_candidates=[
                {
                    "label": "b",
                    "child_rect": _rect(0, 0, 60, 60),
                    "parent_rect": _rect(0, 0, 40, 40),
                    "parent_overflow": "hidden",
                    "child_position": "static",
                }
            ],
            fonts={'"Inter"': False},
        )
        findings = run_floor(bag, _ROUTE)
        kinds = sorted(f.kind for f in findings)
        self.assertEqual(kinds, ["clip", "font_not_loaded", "overflow"])

    def test_all_clean_yields_zero_findings(self):
        bag = Bag(
            region_found=True,
            elements={},
            overflow_candidates=[
                {"label": "a", "scroll_width": 100, "client_width": 200, "overflow_x": "visible"}
            ],
            clip_candidates=[
                {
                    "label": "b",
                    "child_rect": _rect(5, 5, 10, 10),
                    "parent_rect": _rect(0, 0, 40, 40),
                    "parent_overflow": "hidden",
                    "child_position": "static",
                }
            ],
            fonts={'"Inter"': True},
        )
        findings = run_floor(bag, _ROUTE)
        self.assertEqual(findings, [])

    def test_no_anchor_needed_floor_runs_on_built_bag_alone(self):
        # Proves D9's structural non-vacuousness: a feature with NO design
        # anchor / intent bag / binding still gets a real floor result.
        bag = Bag(
            region_found=True,
            elements={},
            overflow_candidates=[
                {"label": "a", "scroll_width": 500, "client_width": 100, "overflow_x": "visible"}
            ],
        )
        findings = run_floor(bag, _ROUTE)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].kind, "overflow")


if __name__ == "__main__":
    unittest.main()
