"""Tests for src/devforge/lib/_spec_check/_brief.py.

Covers:
  - render_formalize_brief: every AC id + text present, all three top-level
    contract keys, all 4 sorts, all 4 coverage statuses, both constraint
    kinds, no crash on an AC dict missing "checked"/"subsection", and the
    empty-acs-list case still renders the contract.
  - subject_resolution: the key is named, both arms and both statuses are
    named (anchored so "resolved" can't false-pass off a substring of
    "unresolved"), the mechanical-check sentence, the unresolved
    "searched" field, and the coverage-side subject/omission rules.
  - subsection rendering: present subsections are rendered alongside the
    AC id/text; an AC without one still renders the pre-existing form;
    the role-key-first preservation trigger names the actual "5.2
    Behavior preservation" subsection text.
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
        # Absent subsection: renders exactly as it did before subsection
        # rendering existed -- no parenthesized annotation.
        self.assertIn(
            "**AC-3**: The system shall log all errors.", brief
        )

    def test_subsection_rendered_when_present(self):
        brief = render_formalize_brief(self._acs())
        self.assertIn(
            "**AC-1** (5.1 Ordering): The system shall reject orders "
            "over $10,000.",
            brief,
        )
        self.assertIn(
            "**AC-2** (5.2 Refunds): WHEN a user is an admin THEN the "
            "system shall allow refunds.",
            brief,
        )

    def test_empty_subsection_renders_as_before(self):
        acs = [
            {"id": "AC-4", "text": "The system shall archive logs.",
             "checked": False, "subsection": ""}
        ]
        brief = render_formalize_brief(acs)
        self.assertIn(
            "**AC-4**: The system shall archive logs.", brief
        )

    def test_empty_acs_list_still_renders_contract(self):
        brief = render_formalize_brief([])
        self.assertIn("`variables`", brief)
        self.assertIn("`constraints`", brief)
        self.assertIn("`coverage`", brief)
        self.assertIn("(no acceptance criteria found)", brief)

    def test_empty_acs_list_still_renders_subject_resolution(self):
        # Guards against a future `if acs:` gating of the subject-
        # resolution paragraphs -- the OUTPUT CONTRACT is static prose,
        # not conditional on the AC list content.
        brief = render_formalize_brief([])
        self.assertIn("`subject_resolution`", brief)
        self.assertIn("unresolved_subject", brief)

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

    def test_subject_resolution_key_named(self):
        brief = render_formalize_brief(self._acs())
        self.assertIn("`subject_resolution`", brief)
        self.assertIn("REQUIRED on every variable", brief)

    def test_subject_resolution_both_arms_named(self):
        from _spec_check.ir_schema import SUBJECT_RESOLUTION_ARMS

        brief = render_formalize_brief(self._acs())
        for arm in SUBJECT_RESOLUTION_ARMS:
            self.assertIn('"arm": "{0}"'.format(arm), brief)

    def test_subject_resolution_both_statuses_named(self):
        # Anchored like the sibling arm test: "resolved" is a substring of
        # "unresolved", so a bare assertIn(status, brief) can't fail for a
        # missing standalone "resolved" -- anchor on the quoted JSON pair.
        from _spec_check.ir_schema import SUBJECT_RESOLUTION_STATUSES

        brief = render_formalize_brief(self._acs())
        for status in SUBJECT_RESOLUTION_STATUSES:
            self.assertIn('"status": "{0}"'.format(status), brief)

    def test_mechanical_check_sentence_present(self):
        brief = render_formalize_brief(self._acs())
        self.assertIn("MECHANICALLY CHECKED", brief)
        self.assertIn("must exist under the workspace root", brief)
        # Hedged framing -- no wired-up auto-reclassification exists yet
        # (validate_citations has no caller until a later phase), so the
        # brief must not assert one.
        self.assertIn(
            "or the citation does not count as a resolution", brief
        )
        self.assertNotIn("the citation is treated as unresolved", brief)

    def test_unresolved_carries_searched(self):
        brief = render_formalize_brief(self._acs())
        self.assertIn('"searched"', brief)

    def test_preservation_subsection_is_primary_trigger(self):
        brief = render_formalize_brief(self._acs())
        # Role-key-first: the actual "5.2 Behavior preservation" subsection
        # text (the real ### heading /specify renders) is the FIRST-named
        # trigger, ahead of the wording-based secondary trigger.
        subsection_idx = brief.index("5.2 Behavior preservation")
        wording_idx = brief.index("presupposes presently-existing")
        self.assertLess(subsection_idx, wording_idx)
        self.assertIn("REGARDLESS of how the AC is worded", brief)
        self.assertIn("UNRESOLVED", brief)

    def test_preservation_wording_is_secondary_trigger(self):
        brief = render_formalize_brief(self._acs())
        self.assertIn(
            "an AC under any OTHER subsection whose statement "
            "presupposes presently-existing behavior must ALSO "
            "resolve via the code arm",
            brief,
        )

    def test_unresolved_variable_excluded_from_constraints(self):
        brief = render_formalize_brief(self._acs())
        self.assertIn("must not appear in ANY constraint", brief)

    def test_coverage_contains_all_four_statuses(self):
        from _spec_check.ir_schema import COVERAGE_STATUSES

        brief = render_formalize_brief(self._acs())
        for status in COVERAGE_STATUSES:
            self.assertIn(status, brief)
        self.assertIn("unresolved_subject", brief)

    def test_coverage_subject_field_requirement_documented(self):
        brief = render_formalize_brief(self._acs())
        self.assertIn("`subject`", brief)
        self.assertIn(
            "REQUIRED for `unresolved_subject` and names the "
            "unresolved variable",
            brief,
        )
        self.assertIn("omit it for every other status", brief)
        self.assertIn("reason` is optional for `unresolved_subject`", brief)

    def test_every_ac_id_exactly_once_statement_retained(self):
        brief = render_formalize_brief(self._acs())
        self.assertIn(
            "EVERY AC id above MUST appear exactly once in `coverage`",
            brief,
        )


if __name__ == "__main__":
    unittest.main()
