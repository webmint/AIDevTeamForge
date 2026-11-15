#!/usr/bin/env python3
"""Tests for scripts/forge/spec_lint.py (stdlib unittest; Python 3.9+).

Each test builds a throwaway project dir with an invented feature dir (specs/900-widget/spec.md, gates/spec-gate.md).
All data is invented.

Run: python3 -m unittest discover -s tests/scripts/forge -p 'test_spec_lint.py' -v
"""
from __future__ import annotations

import hashlib
import io
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(REPO, "scripts", "forge"))
import spec_lint  # noqa: E402

FEATURE = "specs/900-widget"

GOOD_SPEC = """# Spec: Widget spinner

**Date**: 2026-01-01
**Status**: Draft
**Type**: feature

## Request (verbatim)

> Add AC-99 and see §42 of the other thing.

## 1. Overview

The widget spins. See §3 for the rules.

## 2a. Prior art

| Candidate | Decision | Evidence read |
|-----------|----------|---------------|
| `Spinner.spin` | reuse | `src/spinner.py:10-20` |

## 3. Desired Behavior

### 3.4 Rates

The widget spins at 50 rpm.

## 5. Acceptance Criteria

**Spinning**
- [ ] **AC-1** (ticket AC 1): The widget spins, see AC-2 and §3.4.
- [x] **AC-2**: The widget stops.

**Other**
- [ ] **AC-3**: Same as spec 054's AC-7 and contract §13.
"""

GATE = """# Gate report: spec-gate — specs/900-widget

**Reviewer**: independent. **Date**: 2026-01-01.
**Result**: C0 W1 S0.

## Critical

## Warning

### W-1 something
"""


def codes(findings):
    return [(c, n) for c, n, _m in findings]


class Base(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.feature = os.path.join(self.root, FEATURE)
        os.makedirs(os.path.join(self.feature, "gates"))

    def tearDown(self):
        shutil.rmtree(self.root)

    def write(self, name, text):
        path = os.path.join(self.feature, name)
        with open(path, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
        return path

    def read(self, name):
        with open(os.path.join(self.feature, name), encoding="utf-8", newline="") as handle:
            return handle.read()

    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = spec_lint.main(list(argv) + ["--root", self.root])
        return code, out.getvalue(), err.getvalue()


class LintBlocking(Base):
    def lint(self, text):
        return spec_lint.lint(text)[0]

    def test_clean_spec_has_no_blocking(self):
        self.assertEqual(self.lint(GOOD_SPEC), [])

    def test_b1_duplicate_and_gap(self):
        text = GOOD_SPEC.replace("**AC-3**", "**AC-2**").replace("- [ ] **AC-1**", "- [ ] **AC-1**\n- [ ] **AC-5**: x")
        found = self.lint(text)
        messages = " | ".join(m for c, _n, m in found if c == "B1")
        self.assertIn("AC-2 is defined twice", messages)
        self.assertIn("missing AC-3, AC-4", messages)

    def test_b1_no_ac_at_all(self):
        found = self.lint("# Spec\n\n## 1. Overview\n\ntext\n")
        self.assertEqual([c for c, _n, _m in found], ["B1"])

    def test_b1_ac_with_text_between_id_and_colon_and_uppercase_x(self):
        text = "## 5. Acceptance Criteria\n- [X] **AC-1** (ticket AC 1): a\n- [ ] **AC-2** (x): b\n"
        self.assertEqual(self.lint(text), [])

    def test_b2_dangling_reference(self):
        found = self.lint(GOOD_SPEC.replace("see AC-2 and", "see AC-9 and"))
        self.assertEqual(codes(found), [("B2", 30)])

    def test_b2_skips_request_code_spans_and_qualified(self):
        text = GOOD_SPEC + "\nSee `AC-77`, ticket AC-8, brief AC-9, spec AC-10, 054 AC-11, 054's AC-12, contract AC-13.\n"
        self.assertEqual(self.lint(text), [])

    def test_b2_and_b3_a_ticket_key_qualifies(self):
        text = GOOD_SPEC + "\nAs in PROJ-1301 AC-4 and PROJ-1301's AC-5, see PROJ-1301 §3.\n"
        self.assertEqual(self.lint(text), [])

    def test_b2_and_b3_a_standard_name_is_not_a_ticket(self):
        found = self.lint(GOOD_SPEC + "\nEncoded as UTF-8 §99 and as UTF-16 AC-77.\n")
        self.assertEqual(sorted(c for c, _n, _m in found), ["B2", "B3"])

    def test_b2_an_ac_id_before_another_is_not_a_qualifier(self):
        found = self.lint(GOOD_SPEC + "\nBoth AC-1 AC-77 apply.\n")
        self.assertEqual([c for c, _n, _m in found], ["B2"])

    def test_b2_unqualified_after_other_word_is_found(self):
        found = self.lint(GOOD_SPEC + "\nAlso the AC-77 rule.\n")
        self.assertEqual([c for c, _n, _m in found], ["B2"])

    def test_b3_bare_section_reference(self):
        found = self.lint(GOOD_SPEC.replace("contract §13", "(approved, §13)"))
        self.assertEqual([c for c, _n, _m in found], ["B3"])
        self.assertIn("§13", found[0][2])

    def test_b3_headings_with_letters_and_dots_resolve(self):
        text = GOOD_SPEC + "\nSee §2a, §3.4, §5 and §1.\n"
        self.assertEqual(self.lint(text), [])
        self.assertEqual([c for c, _n, _m in self.lint(GOOD_SPEC + "\nSee §3.5.\n")], ["B3"])

    def test_b3_skips_other_document_code_span_quote_and_request(self):
        text = GOOD_SPEC + "\nThe constitution §5.2, `§9`, \"see §8 there\", “§7”.\n"
        self.assertEqual(self.lint(text), [])

    def test_b3_function_word_does_not_qualify(self):
        self.assertEqual([c for c, _n, _m in self.lint(GOOD_SPEC + "\nAs per §12 we act.\n")], ["B3"])

    def test_b3_reference_list_takes_first_members_qualification(self):
        text = GOOD_SPEC + "\ncontract §7.3–7.7, §8 and §9 hold. Also in §10 / §11.\n"
        self.assertEqual([m for _c, _n, m in self.lint(text)][0].split()[0], "§10")
        self.assertEqual(len(self.lint(text)), 2)  # §10 and §11 (list joined by "/")

    def test_b3_ignores_fenced_code(self):
        text = GOOD_SPEC + "\n```\nsee §99 and AC-99\n```\n"
        self.assertEqual(self.lint(text), [])


class LintReviewFixes(Base):
    def lint(self, text):
        return spec_lint.lint(text)[0]

    def b(self, text, code):
        return [f for f in self.lint(text) if f[0] == code]

    def test_b3_internal_forms_are_checked(self):
        for form in ("Size (§9)", "Source: §9", "See [§9]", "**Size (§9)**", "(§9)"):
            self.assertEqual(len(self.b(GOOD_SPEC + "\n" + form + " done.\n", "B3")), 1, form)

    def test_b3_document_qualifier_needs_whitespace_only(self):
        for form in ("(contract §13)", "**Constitution §5.2** rules", "the constitution §5.2", "054 §9.9", "054's §9.9"):
            self.assertEqual(self.b(GOOD_SPEC + "\n" + form + "\n", "B3"), [], form)
        self.assertEqual(len(self.b(GOOD_SPEC + "\ncontract: §13\n", "B3")), 1)

    def test_b3_and_b2_check_heading_lines(self):
        found = self.lint(GOOD_SPEC + "\n## 8. Notes (AC-9, §42)\n")
        self.assertEqual(sorted(c for c, _n, _m in found), ["B2", "B3"])

    def test_b3_numbered_heading_inside_a_fence_does_not_count(self):
        text = GOOD_SPEC + "\n```\n### 9.9 Fake\n```\n\nSee §9.9.\n"
        self.assertEqual(len(self.b(text, "B3")), 1)

    def test_b4_unclosed_fence(self):
        text = GOOD_SPEC + "\n```\nsee §99\n"
        found = self.b(text, "B4")
        self.assertEqual(len(found), 1)
        self.assertIn("opened on line {}".format(found[0][1]), found[0][2])
        self.assertIn("never closed", found[0][2])
        self.assertEqual(self.b(text, "B3"), [])

    def test_fence_inline_triple_backtick_is_not_a_fence(self):
        text = GOOD_SPEC + "\nUse ```x``` inline and §99.\n"
        self.assertEqual((len(self.b(text, "B4")), len(self.b(text, "B3"))), (0, 1))

    def test_fence_closes_on_a_longer_run_and_not_on_a_shorter_one(self):
        text = GOOD_SPEC + "\n```\nfoo\n`````\n\nSee §98 after.\n"
        self.assertEqual((len(self.b(text, "B4")), len(self.b(text, "B3"))), (0, 1))
        text = GOOD_SPEC + "\n````\n```\nsee §99\n````\n\nSee §98.\n"
        self.assertEqual((len(self.b(text, "B4")), len(self.b(text, "B3"))), (0, 1))

    def test_b1_malformed_definitions(self):
        for line in ("- [ ] **AC-4:** x", "- [ ] **AC-4a**: x", "- **AC-4**: x", "1. **AC-4**: x"):
            found = self.b(GOOD_SPEC + "\n" + line + "\n", "B1")
            self.assertEqual(len(found), 1, line)
            self.assertIn("not in the", found[0][2])

    def test_b2_suffix_refs_and_prefix_ids(self):
        self.assertEqual(len(self.b(GOOD_SPEC + "\nAlso AC-3a here.\n", "B2")), 1)
        text = "## 5. Acceptance Criteria\n- [ ] **AC-10**: x\n\nSee AC-1.\n"
        self.assertEqual([c for c, _n, _m in self.lint(text) if c == "B2"], ["B2"])

    def test_quote_with_an_inch_mark_does_not_hide_a_reference(self):
        text = GOOD_SPEC + '\nA 5" screen, see §42 and "x".\n'
        self.assertEqual(len(self.b(text, "B3")), 1)
        self.assertEqual(self.b(GOOD_SPEC + '\nA "see §42" quote.\n', "B3"), [])


class LintLowFixes(Base):
    def b(self, text, code):
        return [f for f in spec_lint.lint(text)[0] if f[0] == code]

    def test_l1_code_span_or_quote_before_a_reference_does_not_qualify(self):
        self.assertEqual(len(self.b(GOOD_SPEC + "\nThe handler `x()` §9 is wrong.\n", "B3")), 1)
        self.assertEqual(len(self.b(GOOD_SPEC + '\nThe term "foo" §9 is wrong.\n', "B3")), 1)

    def test_l3_emphasis_around_the_reference_still_qualifies(self):
        for form in ("Per constitution **§5.2**", "contract _§13_", "**Constitution** §5.2"):
            self.assertEqual(self.b(GOOD_SPEC + "\n" + form + "\n", "B3"), [], form)
        self.assertEqual(len(self.b(GOOD_SPEC + "\nSource: **§9**\n", "B3")), 1)

    def test_l2_bare_bold_ac_outside_the_ac_section_is_prose(self):
        text = GOOD_SPEC + "\n## 6. Out of Scope\n\n- **AC-5** (dropped): gone.\n\n## 9. Risks\n\n- **AC-2** depends on x.\n"
        self.assertEqual(self.b(text, "B1"), [])
        self.assertEqual([m for _c, _n, m in self.b(text, "B2")], ["AC-5 names no AC of this spec"])  # a ref, as before

    def test_l2_plain_id_after_a_checkbox_is_a_malformed_definition(self):
        found = self.b(GOOD_SPEC + "\n- [ ] AC-2: dup\n", "B1")
        self.assertEqual(len(found), 1)
        self.assertIn("not in the", found[0][2])
        self.assertEqual(len(self.b(GOOD_SPEC.replace("## 5. Acceptance Criteria", "## 5. Acceptance Criteria\n\n- **AC-9**: x"),
                                    "B1")), 1)

    def test_l4_fence_open_in_the_request_does_not_hide_the_rest(self):
        text = GOOD_SPEC.replace("> Add AC-99", "```\n> Add AC-99") + "\nSee §99.\n"
        self.assertEqual(self.b(text, "B4"), [])
        self.assertEqual(len(self.b(text, "B3")), 1)

    def test_l4_fence_open_in_the_request_at_eof_says_so(self):
        found = self.b("## Request (verbatim)\n\n```\nraw\n", "B4")
        self.assertEqual(len(found), 1)
        self.assertIn("in the Request section", found[0][2])


class LintAdvisory(Base):
    def advisory(self, text):
        return spec_lint.lint(text)[1]

    def test_clean_spec_has_no_advisory(self):
        self.assertEqual(self.advisory(GOOD_SPEC), [])

    def test_a1_same_noun_two_numbers(self):
        found = self.advisory(GOOD_SPEC + "\nThe batch holds 5 widgets.\nThe other holds 7 widgets.\n")
        self.assertEqual([c for c, _n, _m in found], ["A1"])
        self.assertIn("'widgets'", found[0][2])

    def test_a1_same_number_headings_code_and_thousands_are_quiet(self):
        text = GOOD_SPEC + "\nA batch of 5000 widgets, again 5,000 widgets, `9 widgets`.\n### 8 widgets\n"
        self.assertEqual([m for c, _n, m in self.advisory(text) if "widgets" in m], [])

    def test_a2_vague_phrase_without_number(self):
        text = GOOD_SPEC + "\n## 7. Technical Constraints\n\nThe widget must be fast. It spins in 20 ms and is robust.\n"
        found = [f for f in self.advisory(text) if f[0] == "A2"]
        self.assertEqual(len(found), 1)
        self.assertIn("'fast'", found[0][2])

    def test_a2_named_standard_and_other_sections_are_quiet(self):
        text = GOOD_SPEC + "\n## 7. Technical Constraints\n\nIt is secure under GDPR.\n\n## 9. Risks\n\nIt is fast.\n"
        self.assertEqual([f for f in self.advisory(text) if f[0] == "A2"], [])

    def test_a2_percent_and_dollar_count_as_numbers(self):
        text = GOOD_SPEC + "\n## 7. Technical Constraints\n\nIt stays fast at 99%. It stays reliable under 5$.\n"
        self.assertEqual([f for f in self.advisory(text) if f[0] == "A2"], [])

    def test_a3_pipe_inside_a_code_span_does_not_split_the_cell(self):
        text = GOOD_SPEC.replace("| `src/spinner.py:10-20` |", "| `a|b` `src/spinner.py:10-20` |")
        self.assertEqual([f for f in self.advisory(text) if f[0] == "A3"], [])

    def test_a2_banned_phrase(self):
        text = GOOD_SPEC.replace("The widget stops.", "The widget handles stops.")
        found = [f for f in self.advisory(text) if f[0] == "A2"]
        self.assertEqual(len(found), 1)
        self.assertIn("'handles'", found[0][2])

    def test_a3_bad_line_parts(self):
        for bad in ("src/a.py:0", "src/a.py:L12", "src/a.py#L12", "src/a.py:12-", "src/a.py:9-3"):
            found = [f for f in self.advisory(GOOD_SPEC + "\nSee `{}` there.\n".format(bad)) if f[0] == "A3"]
            self.assertEqual(len(found), 1, bad)

    def test_a3_good_citations_and_non_paths_are_quiet(self):
        text = GOOD_SPEC + "\nSee `src/a.py:12`, `src/a.py:12-14`, `localhost:0`, `127.0.0.1:0`, `a.py:3, 5-6`.\n"
        self.assertEqual([f for f in self.advisory(text) if f[0] == "A3"], [])

    def test_a3_prior_art_row_without_file_line(self):
        text = GOOD_SPEC.replace("| `src/spinner.py:10-20` |", "| the spinner file |")
        found = [f for f in self.advisory(text) if f[0] == "A3"]
        self.assertEqual(len(found), 1)
        self.assertIn("Spinner.spin", found[0][2])


FORMAT2_SPEC = GOOD_SPEC.replace("**Type**: feature\n", "**Type**: feature\n**Format**: 2\n") + """
## 7. Decisions

- **DEC-1** Spin order: clockwise. Why: the motor turns that way.

## 8. Open Questions

- **Q-2** Which colour?

### Q-3 Which size?

## 9. Risks

| Id | Risk |
|----|------|
| RISK-1 | the motor stalls |

The gate found CRIT-1, WARN-2 and NOTE-3; DEC-1 answers Q-2 and RISK-1 stays.
"""


class Labels(Base):
    def lint(self, text, key=None):
        blocking, advisory = spec_lint.lint(text, key)
        return [f for f in blocking + advisory if f[0] in ("B5", "A4")]

    def config(self, pattern):
        os.makedirs(os.path.join(self.root, ".claude"), exist_ok=True)
        with open(os.path.join(self.root, ".claude", "project-config.json"), "w", encoding="utf-8") as handle:
            handle.write('{"ISSUE_KEY_PATTERN": "%s"}' % pattern)

    def test_every_label_of_the_table_passes(self):
        self.assertTrue(spec_lint.is_format2(FORMAT2_SPEC))
        self.assertEqual(spec_lint.lint(FORMAT2_SPEC), ([], []))

    def test_invented_definitions_block(self):
        text = FORMAT2_SPEC + "\n- **KD-2** Use the cache.\n### D1 Second choice\n1. **OQ-4** a\n- [ ] **PD-1**: b\n"
        found = self.lint(text)
        self.assertEqual([(c, m.split("`")[1]) for c, _n, m in found],
                         [("B5", "KD-2"), ("B5", "D1"), ("B5", "OQ-4"), ("B5", "PD-1")])
        self.assertIn("a product or standard name: reword so the item does not open with it", found[0][2])

    def test_single_letter_definitions_block(self):
        text = FORMAT2_SPEC + "\n- **S9** a\n- **T2** b\n- **X-1** c\n### W1 d\n- **N1** e\n"
        found = self.lint(text)
        self.assertEqual([(c, m.split("`")[1]) for c, _n, m in found],
                         [("B5", "S9"), ("B5", "T2"), ("B5", "X-1"), ("B5", "W1"), ("B5", "N1")])

    def test_short_standard_names_pass_as_definitions(self):
        text = FORMAT2_SPEC + "\n- **S3** bucket\n- **EC2** hosts\n### P95 latency\n- **HTML5** forms\n"
        self.assertEqual(self.lint(text), [])

    def test_rows_of_a_label_table_block(self):
        decisions = FORMAT2_SPEC.replace("- **DEC-1** Spin order: clockwise. Why: the motor turns that way.\n",
                                         "| Decision | Why |\n|---|---|\n| DEC-1 | clockwise |\n| KD-1 | queue |\n")
        self.assertEqual([(c, m.split("`")[1]) for c, _n, m in self.lint(decisions)], [("B5", "KD-1")])
        self.assertIn("so the row does not open with it", self.lint(decisions)[0][2])
        by_header = FORMAT2_SPEC + "\n## 10. Parts\n\n| # | Part |\n|---|---|\n| P-1 | spinner |\n| T2 | stop |\n"
        self.assertEqual([(c, m.split("`")[1]) for c, _n, m in self.lint(by_header)], [("B5", "P-1"), ("B5", "T2")])

    def test_label_table_heading_words_match_whole_words(self):
        text = FORMAT2_SPEC + "\n## 10. Questionnaire fields\n\n| Field | What |\n|---|---|\n| V2 | form |\n"
        self.assertEqual([c for c, _n, _m in self.lint(text)], ["A4"])
        text = FORMAT2_SPEC + "\n## 10. Key Design Decisions\n\n| Field | What |\n|---|---|\n| V2 | form |\n"
        self.assertEqual([c for c, _n, _m in self.lint(text)], ["B5"])

    def test_table_rows_warn_only_for_an_unknown_label(self):
        text = FORMAT2_SPEC + ("\n## 10. Parts\n\n| Name | What |\n|----|------|\n| OQ-3 | a |\n| T1 | b |\n| UTF-8 | c |\n"
                               "| S3 | d |\n")
        found = self.lint(text)
        self.assertEqual([(c, m.split("`")[1]) for c, _n, m in found], [("A4", "OQ-3")])
        self.assertIn("table row", found[0][2])

    def test_invented_reference_warns(self):
        found = self.lint(FORMAT2_SPEC + "\nThis follows KD-9 and HG-1.\n")
        self.assertEqual([(c, m.split("`")[1]) for c, _n, m in found], [("A4", "KD-9"), ("A4", "HG-1")])

    def test_forge_machine_ids_and_standard_names_pass(self):
        text = FORMAT2_SPEC + ("\nSG-26, PG-A01, TR-27, B3-9, C1, E1, T1, F-3, W2, S-1, C0 W1 N2 S0, UTF-8, SHA-256, "
                               "EC2, S3, ISO-8601, E2E and K8s.\n")
        self.assertEqual(self.lint(text), [])

    def test_literal_ticket_key_passes(self):
        self.config("PROJ-[0-9]+")
        key = spec_lint.project_key(self.root)
        text = FORMAT2_SPEC + "\n- **PROJ-1301** the parent ticket\n\nSee PROJ-1302.\n"
        self.assertEqual(self.lint(text, key), [])
        self.assertEqual([c for c, _n, _m in self.lint(text)], ["B5", "A4"])  # without the project's pattern
        self.write("spec.md", text)
        self.assertEqual(self.run_cli("lint", FEATURE)[0], 0)

    def test_old_spec_lints_as_before_the_label_checks(self):
        text = GOOD_SPEC + "\nSee EN-12 AC-9, GB-4 §7 and EC-2 AC-8.\n"  # ticket keys qualify, as before
        self.assertEqual(spec_lint.lint(text)[0], [])

    def test_default_jira_pattern_is_ignored(self):
        self.config("[A-Z][A-Z0-9]+-[0-9]+")
        self.assertIsNone(spec_lint.project_key(self.root))
        self.write("spec.md", FORMAT2_SPEC + "\n- **KD-2** Use the cache.\n")
        code, out, _err = self.run_cli("lint", FEATURE)
        self.assertEqual(code, 1)
        self.assertIn("B5-", out)

    def test_qualified_old_label_passes(self):
        self.config("PROJ-[0-9]+")
        text = FORMAT2_SPEC + "\nAs spec 001 D-3, 001's KD-2, ticket OQ-1 and PROJ-1301 D-4 said.\n"
        self.assertEqual(self.lint(text, spec_lint.project_key(self.root)), [])

    def test_quotes_code_spans_and_fences_are_skipped(self):
        text = FORMAT2_SPEC + '\nThe user said "keep KD-2" and “drop D1”; see `KD-3`.\n\n```\n- **KD-4** x\n```\n'
        self.assertEqual(self.lint(text), [])

    def test_a_file_without_format_2_is_not_checked(self):
        text = GOOD_SPEC + "\n- **KD-2** Use the cache.\n\nThis follows KD-9.\n"
        self.assertEqual(self.lint(text), [])
        late = GOOD_SPEC + "\n**Format**: 2\n\n- **KD-2** Use the cache.\n"  # not a header line
        self.assertFalse(spec_lint.is_format2(late))
        self.assertEqual(self.lint(late), [])

    def test_labels_verb_on_a_plan(self):
        plan = ("# Plan: Widget\n\n**Spec**: spec.md\n**Format**: 2\n\n## Key Design Decisions\n\n"
                "| Id | Decision |\n|----|----------|\n| DEC-2 | cache |\n| KD-1 | queue |\n\n- **D1** retry\n\n"
                "## Layer Map\n\n| Layer | Files |\n|---|---|\n| OQ-9 | x |\n")
        self.write("plan.md", plan)
        before = sorted(os.listdir(os.path.join(self.feature, "gates")))
        code, out, _err = self.run_cli("labels", FEATURE + "/plan.md")
        self.assertEqual(code, 1)
        self.assertIn("BLOCKING\nB5-11 `KD-1`", out)
        self.assertIn("\nB5-13 `D1`", out)
        self.assertIn("ADVISORY\nA4-19 table row opens with `OQ-9`", out)
        self.assertTrue(out.rstrip().endswith("labels: B2 A1"))
        self.assertEqual(sorted(os.listdir(os.path.join(self.feature, "gates"))), before)  # writes nothing
        self.write("plan.md", plan.replace("**Format**: 2\n", ""))
        code, out, _err = self.run_cli("labels", FEATURE + "/plan.md")
        self.assertEqual(code, 0)
        self.assertIn("labels: not checked", out)
        self.assertEqual(self.run_cli("labels", FEATURE + "/missing.md")[0], 2)

    def test_labels_verb_reads_the_project_config_under_root(self):
        self.write("plan.md", "# Plan\n\n**Format**: 2\n\n## Decisions\n\n- **PROJ-1301** parent ticket\n")
        self.assertEqual(self.run_cli("labels", FEATURE + "/plan.md")[0], 1)
        self.config("PROJ-[0-9]+")
        code, out, _err = self.run_cli("labels", FEATURE + "/plan.md")
        self.assertEqual(code, 0)
        self.assertTrue(out.rstrip().endswith("labels: B0 A0"))


# The two spec shapes of `/specify` (`.claude/commands/specify.md` → "Spec Format"): the Format 2 template and the
# older template that an existing spec keeps.
NEW_SHAPE_SPEC = """# Spec: Widget spinner

**Date**: 2026-01-01
**Status**: Draft
**Author**: Claude + User
**Type**: feature
**Format**: 2

## 1. Summary

The widget spins when the user presses start and stops at a limit.
Its colours stay as they are.
The user decides whether the limit becomes a setting later.

## 2. Current State

The spinner turns once per call (`src/spinner.py:10-20`); the rest is in research-report.md.

## 2a. Prior art

| Candidate | What this spec needs from it | Decision | Evidence read |
|-----------|------------------------------|----------|---------------|
| `Spinner.spin` | one turn per call | reuse behaviour | `src/spinner.py:10-20` |

## 3. Behaviour and Acceptance Criteria

### 3.1 Start

The user presses start on the widget screen; the stop rule is in §3.2.

- [ ] **AC-1**: The widget turns at 50 rpm within 200 ms of the press.

### 3.2 Stop

- [ ] **AC-2**: The widget stops after 10 turns started as §3.1 says.

## 4. Affected Areas

| Area | Files | Impact |
|------|-------|--------|
| Spinner | `src/spinner.py` | add a stop limit |

## 5. Out of Scope

- The widget's colours (DEC-1).

## 6. Technical Constraints

The limit is read once, at start.

## 7. Decisions

- **DEC-1** Colours: unchanged. Why: the request names only motion.

## 8. Open Questions

- **Q-4** Should the limit become a setting later?

## 9. Risks

| Id | Risk | Likelihood | Impact | Mitigation |
|----|------|-----------|--------|------------|
| RISK-1 | the motor stalls at 50 rpm | Low | Med | AC-1 measures the rate |
"""

OLD_SHAPE_SPEC = """# Spec: Widget spinner

**Date**: 2026-01-01
**Status**: Draft
**Author**: Claude + User
**Type**: feature

## Request (verbatim)

> Make the widget spin fast, see §42 and AC-99.

Q (Phase 2, 2026-01-01): Which limit?
A: 10 turns, as KD-2 says.

## 1. Overview

The widget spins and stops at a limit.

## 2. Current State

The spinner turns once per call (`src/spinner.py:10-20`).

## 2a. Prior art

| Candidate | What this spec needs from it | Decision | Evidence read |
|-----------|------------------------------|----------|---------------|
| `Spinner.spin` | one turn per call | reuse behaviour | the spinner file |

## 3. Desired Behavior

### 3.2 Stop

The widget stops quickly and is fast.

## 4. Affected Areas

| Area | Files | Impact |
|------|-------|--------|
| Spinner | `src/spinner.py` | add a stop limit |

## 5. Acceptance Criteria

- [ ] **AC-1**: The widget stops after 10 turns (§3.2).
- [ ] **AC-2**: The widget stops after 12 turns at most, see AC-3.

## 6. Out of Scope

- NOT included: colours

## 7. Technical Constraints

- Must follow: a robust design.

## 8. Open Questions

- **OQ-1** Should the limit become a setting?

## 9. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| KD-1 the motor stalls | Low | Med | measure the rate |
"""

# `spec_lint.py lint` output for OLD_SHAPE_SPEC with the script of 1.40.0 Piece 1b-3a (dcadd0b), before the new
# template existed: the older shape lints the same after it
OLD_SHAPE_LINT = """BLOCKING
B2-44 AC-3 names no AC of this spec

ADVISORY
A3-27 prior-art row without a `file:line` in its evidence cell: `Spinner.spin`
A2-33 vague phrase 'fast' with no number or named standard: The widget stops quickly and is fast.
A1-43 'turns' appears with different numbers: 10 (line 43), 12 (line 44)
A2-52 vague phrase 'robust' with no number or named standard: - Must follow: a robust design.

spec-lint: B1 A4
"""


class TemplateShapes(Base):
    def test_new_shape_lints_clean(self):
        self.assertTrue(spec_lint.is_format2(NEW_SHAPE_SPEC))
        self.assertEqual(spec_lint.lint(NEW_SHAPE_SPEC), ([], []))
        self.write("spec.md", NEW_SHAPE_SPEC)
        code, out, _err = self.run_cli("lint", FEATURE)
        self.assertEqual(code, 0)
        self.assertTrue(out.rstrip().endswith("spec-lint: B0 A0"))

    def test_new_shape_label_lines_are_checked(self):
        for old, new, token in (("- **DEC-1** Colours", "- **D-1** Colours", "D-1"),
                                ("- **Q-4** Should", "- **OQ-4** Should", "OQ-4"),
                                ("| RISK-1 | the motor", "| R-1 | the motor", "R-1")):
            found = spec_lint.lint(NEW_SHAPE_SPEC.replace(old, new))[0]
            self.assertEqual([(c, m.split("`")[1]) for c, _n, m in found], [("B5", token)])

    def test_new_shape_keys_ac_and_vague_checks_on_section_3(self):
        text = NEW_SHAPE_SPEC.replace("- [ ] **AC-2**: The widget stops", "- **AC-2**: The widget stops")
        self.assertEqual([c for c, _n, _m in spec_lint.lint(text)[0]], ["B1"])  # an AC without its checkbox
        text = NEW_SHAPE_SPEC.replace("The user presses start", "The fast user presses start")
        self.assertEqual([c for c, _n, _m in spec_lint.lint(text)[1]], ["A2"])
        text = NEW_SHAPE_SPEC.replace("The limit is read once, at start.", "The limit is read in a robust way.")
        self.assertEqual([c for c, _n, _m in spec_lint.lint(text)[1]], ["A2"])
        text = NEW_SHAPE_SPEC.replace("| `src/spinner.py:10-20` |", "| the spinner file |")
        self.assertEqual([c for c, _n, _m in spec_lint.lint(text)[1]], ["A3"])

    def test_old_shape_lints_as_before(self):
        self.assertFalse(spec_lint.is_format2(OLD_SHAPE_SPEC))
        self.assertEqual(spec_lint.render_lint(*spec_lint.lint(OLD_SHAPE_SPEC)), OLD_SHAPE_LINT)

    def test_section_3_2_resolves_in_both_shapes(self):
        for text, heading in ((NEW_SHAPE_SPEC, "### 3.2 Stop"), (OLD_SHAPE_SPEC, "### 3.2 Stop")):
            self.assertEqual(self.b(text + "\nSee §3.2.\n"), [])
            self.assertEqual([c for c, _n, _m in self.b(text.replace(heading, "### Stop") + "\nSee §3.2.\n")],
                             ["B3"] * (text.count("§3.2") + 1))

    def b(self, text):
        return [f for f in spec_lint.lint(text)[0] if f[0] == "B3"]


class LintCli(Base):
    def test_output_file_ids_and_exit_codes(self):
        self.write("spec.md", GOOD_SPEC.replace("contract §13", "(approved, §13)"))
        code, out, _err = self.run_cli("lint", FEATURE)
        self.assertEqual(code, 1)
        self.assertEqual(out, self.read("gates/spec-lint.txt"))
        self.assertIn("BLOCKING\nB3-", out)
        self.assertTrue(out.rstrip().endswith("spec-lint: B1 A0"))
        self.assertIn("ADVISORY\n(none)", out)

    def test_clean_spec_exits_zero_even_with_advisory(self):
        self.write("spec.md", GOOD_SPEC + "\nSee `src/a.py:0`.\n")
        code, out, _err = self.run_cli("lint", FEATURE)
        self.assertEqual(code, 0)
        self.assertIn("A3-", out)
        self.assertTrue(out.rstrip().endswith("spec-lint: B0 A1"))

    def test_missing_spec_is_exit_two(self):
        code, _out, err = self.run_cli("lint", FEATURE)
        self.assertEqual(code, 2)
        self.assertIn("no spec.md", err)

    def test_lint_is_deterministic_on_a_second_run(self):
        self.write("spec.md", GOOD_SPEC)
        self.run_cli("lint", FEATURE)
        first = self.read("gates/spec-lint.txt")
        self.run_cli("lint", FEATURE)
        self.assertEqual(first, self.read("gates/spec-lint.txt"))


class LintFiles(Base):
    def test_existing_output_keeps_its_mode_and_new_follows_umask(self):
        self.write("spec.md", GOOD_SPEC)
        out = os.path.join(self.feature, "gates", "spec-lint.txt")
        self.run_cli("lint", FEATURE)
        umask = os.umask(0)
        os.umask(umask)
        self.assertEqual(os.stat(out).st_mode & 0o777, 0o666 & ~umask)
        os.chmod(out, 0o640)
        self.run_cli("lint", FEATURE)
        self.assertEqual(os.stat(out).st_mode & 0o777, 0o640)


class Hash(Base):
    def setUp(self):
        super().setUp()
        self.write("spec.md", GOOD_SPEC)
        self.write("gates/spec-gate.md", GATE)

    def expected(self, text):
        kept = "".join(l for l in text.splitlines(keepends=True) if not l.startswith("**Status**:"))
        return "sha256:" + hashlib.sha256(kept.encode("utf-8")).hexdigest()

    def test_plain_hash_ignores_status_line_only(self):
        code, out, _e = self.run_cli("hash", FEATURE)
        self.assertEqual((code, out.strip()), (0, self.expected(GOOD_SPEC)))
        self.write("spec.md", GOOD_SPEC.replace("Draft", "Approved"))
        self.assertEqual(self.run_cli("hash", FEATURE)[1].strip(), self.expected(GOOD_SPEC))
        self.write("spec.md", GOOD_SPEC.replace("The widget stops.", "The widget halts."))
        self.assertNotEqual(self.run_cli("hash", FEATURE)[1].strip(), self.expected(GOOD_SPEC))

    def test_status_line_in_the_body_counts_and_self_approval_line_does_not(self):
        base = self.run_cli("hash", FEATURE)[1]
        self.write("spec.md", GOOD_SPEC + "\n**Status**: Approved\n")
        self.assertNotEqual(self.run_cli("hash", FEATURE)[1], base)
        approved = GOOD_SPEC.replace("**Status**: Draft", "**Status**: Approved\nSelf-approved (autonomous mode, 2026-01-01): ok")
        self.write("spec.md", approved)
        self.assertEqual(self.run_cli("hash", FEATURE)[1], base)
        late = GOOD_SPEC + "\nSelf-approved (autonomous mode, 2026-01-01): ok\n"
        self.write("spec.md", late)
        self.assertNotEqual(self.run_cli("hash", FEATURE)[1], base)

    def test_l6_without_a_header_status_a_body_status_line_changes_the_hash(self):
        bare = GOOD_SPEC.replace("**Status**: Draft\n", "")
        self.write("spec.md", bare + "\n**Status**: Approved\n")
        first = self.run_cli("hash", FEATURE)[1]
        self.write("spec.md", bare + "\n**Status**: Draft\n")
        self.assertNotEqual(self.run_cli("hash", FEATURE)[1], first)

    def test_crlf_spec_hash_ignores_status(self):
        self.write("spec.md", GOOD_SPEC.replace("\n", "\r\n"))
        crlf = self.run_cli("hash", FEATURE)[1]
        self.write("spec.md", GOOD_SPEC.replace("\n", "\r\n").replace("Draft", "Approved"))
        self.assertEqual(self.run_cli("hash", FEATURE)[1], crlf)
        self.assertNotEqual(crlf.strip(), self.expected(GOOD_SPEC))  # CRLF bytes differ from LF bytes

    def test_unreviewed_before_record_is_replaced_by_the_hash(self):
        self.run_cli("hash", FEATURE, "--unreviewed", "W-1")
        self.assertIn("**Unreviewed changes**: W-1", self.read("gates/spec-gate.md"))
        self.run_cli("hash", FEATURE, "--record")
        text = self.read("gates/spec-gate.md")
        self.assertNotIn("Unreviewed", text)
        self.assertEqual(text.count("**Spec hash**:"), 1)

    def test_report_keeps_its_mode(self):
        path = os.path.join(self.feature, "gates", "spec-gate.md")
        os.chmod(path, 0o640)
        self.run_cli("hash", FEATURE, "--record")
        self.assertEqual(os.stat(path).st_mode & 0o777, 0o640)

    def test_flags_are_mutually_exclusive(self):
        err = io.StringIO()
        with redirect_stderr(err), self.assertRaises(SystemExit) as ctx:
            spec_lint.main(["hash", FEATURE, "--record", "--check", "--root", self.root])
        self.assertEqual(ctx.exception.code, 2)

    def test_record_inserts_after_header_lines_and_touches_nothing_else(self):
        code, _o, _e = self.run_cli("hash", FEATURE, "--record")
        self.assertEqual(code, 0)
        lines = self.read("gates/spec-gate.md").split("\n")
        self.assertEqual(lines[3], "**Result**: C0 W1 S0.")
        self.assertEqual(lines[4], "**Spec hash**: " + self.expected(GOOD_SPEC))
        del lines[4]
        self.assertEqual("\n".join(lines), GATE)

    def test_record_replaces_and_drops_unreviewed(self):
        self.run_cli("hash", FEATURE, "--record")
        self.run_cli("hash", FEATURE, "--unreviewed", "W-1 W-2")
        self.assertIn("**Unreviewed changes**: W-1 W-2\n", self.read("gates/spec-gate.md"))
        self.write("spec.md", GOOD_SPEC.replace("stops", "halts"))
        self.run_cli("hash", FEATURE, "--record")
        text = self.read("gates/spec-gate.md")
        self.assertEqual(text.count("**Spec hash**:"), 1)
        self.assertNotIn("Unreviewed", text)
        self.assertIn(self.expected(self.read("spec.md")), text)

    def test_unreviewed_goes_after_the_hash_line_and_is_replaced(self):
        self.run_cli("hash", FEATURE, "--record")
        self.run_cli("hash", FEATURE, "--unreviewed", "C-1")
        self.run_cli("hash", FEATURE, "--unreviewed", "C-2,  spec-lint")
        lines = self.read("gates/spec-gate.md").split("\n")
        self.assertTrue(lines[4].startswith("**Spec hash**:"))
        self.assertEqual(lines[5], "**Unreviewed changes**: C-2, spec-lint")
        self.assertEqual(sum(1 for l in lines if l.startswith("**Unreviewed")), 1)

    def test_crlf_report_keeps_its_line_endings(self):
        self.write("gates/spec-gate.md", GATE.replace("\n", "\r\n"))
        self.run_cli("hash", FEATURE, "--record")
        raw = self.read("gates/spec-gate.md")
        self.assertEqual(raw.count("\n"), raw.count("\r\n"))
        self.assertIn("**Spec hash**:", raw)

    def test_report_without_header_lines(self):
        self.write("gates/spec-gate.md", "# Gate report\n\n## Critical\n")
        self.run_cli("hash", FEATURE, "--record")
        lines = self.read("gates/spec-gate.md").split("\n")
        self.assertEqual(lines[0], "# Gate report")
        self.assertTrue(lines[2].startswith("**Spec hash**:"))
        self.assertIn("## Critical", lines)

    def test_no_temp_files_left_behind(self):
        self.run_cli("hash", FEATURE, "--record")
        snap = "spec.reviewed-%s.md" % self.expected(GOOD_SPEC)[len("sha256:"):][:12]
        self.assertEqual(sorted(os.listdir(os.path.join(self.feature, "gates"))), ["spec-gate.md", snap])

    def test_record_keeps_one_snapshot_per_reviewed_spec(self):
        code, out, _e = self.run_cli("hash", FEATURE, "--record")
        self.assertEqual(code, 0)
        snap = "spec.reviewed-%s.md" % self.expected(GOOD_SPEC)[len("sha256:"):][:12]
        self.assertEqual(self.read("gates/" + snap), GOOD_SPEC)
        self.assertIn(snap, out)
        self.run_cli("hash", FEATURE, "--record")  # same spec: no second file
        self.write("spec.md", GOOD_SPEC.replace("Draft", "Approved"))  # Status only: same hash
        self.run_cli("hash", FEATURE, "--record")
        snaps = [n for n in os.listdir(os.path.join(self.feature, "gates")) if n.startswith("spec.reviewed-")]
        self.assertEqual(snaps, [snap])
        self.assertEqual(self.read("gates/" + snap), GOOD_SPEC)  # the first copy of that version stays
        self.write("gates/" + snap, "damaged")
        self.run_cli("hash", FEATURE, "--record")
        self.assertEqual(self.read("gates/" + snap), GOOD_SPEC.replace("Draft", "Approved"))  # a damaged copy is rewritten
        self.write("spec.md", GOOD_SPEC.replace("The widget stops.", "The widget halts."))
        self.run_cli("hash", FEATURE, "--record")
        snaps = [n for n in os.listdir(os.path.join(self.feature, "gates")) if n.startswith("spec.reviewed-")]
        self.assertEqual(len(snaps), 2)

    def test_check_unchanged(self):
        self.run_cli("hash", FEATURE, "--record")
        self.write("spec.md", GOOD_SPEC.replace("Draft", "Approved"))
        code, out, _e = self.run_cli("hash", FEATURE, "--check")
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "spec unchanged since its last review ({})".format(self.expected(GOOD_SPEC)))
        self.assertEqual(self.read("gates/spec-hash.txt"), out)

    def test_check_unchanged_hash_with_unreviewed_line_is_exit_one(self):
        self.run_cli("hash", FEATURE, "--record")
        self.run_cli("hash", FEATURE, "--unreviewed", "W-3")
        code, out, _e = self.run_cli("hash", FEATURE, "--check")
        self.assertEqual(code, 1)
        self.assertEqual(out.strip(), "spec unchanged since its last review round; unreviewed changes: W-3")
        self.assertEqual(self.read("gates/spec-hash.txt"), out)

    def test_check_changed(self):
        self.run_cli("hash", FEATURE, "--record")
        self.write("spec.md", GOOD_SPEC.replace("stops", "halts"))
        code, out, _e = self.run_cli("hash", FEATURE, "--check")
        self.assertEqual((code, out.strip()),
                         (1, "spec changed after its last review; unreviewed changes: none recorded"))
        self.run_cli("hash", FEATURE, "--unreviewed", "W-1")
        code, out, _e = self.run_cli("hash", FEATURE, "--check")
        self.assertEqual((code, out.strip()), (1, "spec changed after its last review; unreviewed changes: W-1"))

    def test_check_without_report_or_hash_is_exit_two(self):
        code, _o, err = self.run_cli("hash", FEATURE, "--check")
        self.assertEqual(code, 2)
        self.assertIn("Spec hash", err)
        os.unlink(os.path.join(self.feature, "gates", "spec-gate.md"))
        code, _o, err = self.run_cli("hash", FEATURE, "--check")
        self.assertEqual(code, 2)
        self.assertIn("no spec-gate report", err)
        self.assertFalse(os.path.exists(os.path.join(self.feature, "gates", "spec-hash.txt")))

    def test_record_without_report_is_exit_two(self):
        os.unlink(os.path.join(self.feature, "gates", "spec-gate.md"))
        self.assertEqual(self.run_cli("hash", FEATURE, "--record")[0], 2)

    def test_empty_unreviewed_is_exit_two(self):
        self.assertEqual(self.run_cli("hash", FEATURE, "--unreviewed", "  ")[0], 2)


if __name__ == "__main__":
    unittest.main()
