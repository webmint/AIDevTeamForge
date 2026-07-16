"""Tests for src/devforge/lib/_spec_check/_brief.py.

Covers:
  - render_formalize_brief: every AC id + text present, all three top-level
    contract keys, all 4 sorts, all 3 coverage statuses, both constraint
    kinds, no crash on an AC dict missing "checked"/"subsection", and the
    empty-acs-list case still renders the contract.
"""

import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _spec_check._brief import render_formalize_brief  # noqa: E402


class TestRenderFormalizeBrief(unittest.TestCase):
    def _acs(self):
        return [
            {
                "id": "AC-1",
                "text": "The system shall reject orders over $10,000.",
                "checked": False,
                "subsection": "5.1 Ordering",
            },
            {
                "id": "AC-2",
                "text": "WHEN a user is an admin THEN the system shall allow refunds.",
                "checked": True,
                "subsection": "5.2 Refunds",
            },
        ]

    def test_contains_every_ac_id_and_text(self):
        brief = render_formalize_brief(self._acs())
        self.assertIn("AC-1", brief)
        self.assertIn("The system shall reject orders over $10,000.", brief)
        self.assertIn("AC-2", brief)
        self.assertIn(
            "WHEN a user is an admin THEN the system shall allow refunds.",
            brief,
        )

    def test_contains_three_top_level_keys(self):
        brief = render_formalize_brief(self._acs())
        self.assertIn("`variables`", brief)
        self.assertIn("`constraints`", brief)
        self.assertIn("`coverage`", brief)

    def test_contains_all_four_sorts(self):
        brief = render_formalize_brief(self._acs())
        for sort in ("Int", "Real", "Bool", "Enum"):
            self.assertIn(sort, brief)

    def test_contains_all_three_coverage_statuses(self):
        brief = render_formalize_brief(self._acs())
        for status in ("formalized", "skipped_prose", "skipped_unsupported"):
            self.assertIn(status, brief)

    def test_contains_both_constraint_kinds(self):
        brief = render_formalize_brief(self._acs())
        self.assertIn("assertion", brief)
        self.assertIn("implication", brief)

    def test_no_crash_on_missing_checked_and_subsection(self):
        acs = [{"id": "AC-3", "text": "The system shall log all errors."}]
        brief = render_formalize_brief(acs)
        self.assertIn("AC-3", brief)
        self.assertIn("The system shall log all errors.", brief)

    def test_empty_acs_list_still_renders_contract(self):
        brief = render_formalize_brief([])
        self.assertIn("`variables`", brief)
        self.assertIn("`constraints`", brief)
        self.assertIn("`coverage`", brief)
        self.assertIn("(no acceptance criteria found)", brief)

    def test_returns_string_ending_in_newline(self):
        brief = render_formalize_brief(self._acs())
        self.assertTrue(brief.endswith("\n"))

    def test_one_json_object_instruction_present(self):
        brief = render_formalize_brief(self._acs())
        self.assertIn("ONE JSON object", brief)

    def test_gloss_and_domain_documented(self):
        brief = render_formalize_brief(self._acs())
        self.assertIn("gloss", brief)
        self.assertIn("domain", brief)

    def test_rules_reminder_present(self):
        brief = render_formalize_brief(self._acs())
        self.assertIn("flat", brief.lower())
        self.assertIn("one coverage entry per AC", brief)


if __name__ == "__main__":
    unittest.main()
