"""Tests for src/devforge/lib/_shared/spec_acs.py (parse_acs).

Real-producer round-trip discipline:
  parse_acs is tested against the REAL fixture
  tests/lib/fixtures/specify-sample-migration.md — the file produced by
  specify_helper and committed to the test fixture directory. No hand-authored
  AC strings are used as the primary test target.

Coverage:
  - Happy path against the real specify-sample-migration.md fixture.
    Asserts AC-1..AC-7 extracted with correct text and checked=False.
  - Checked [x] / [X] variants — inline text fixtures confirm checked=True.
  - Mixed checked/unchecked — combined inline fixture.
  - Subsection assignment — each AC's subsection matches the ### heading
    above it.
  - Empty string / no AC section → empty list (no crash).
  - Non-existent file path → treated as raw text (empty list, no crash).
  - Real file path (tempfile) → reads and parses.
  - AC section followed by ## 6 section — parser stops at the boundary.
  - Text before AC section is ignored.
  - N/A subsections with no ACs are skipped.
  - The "> Verification:" hint line is not captured in AC text.
"""

from __future__ import annotations

import os
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"
_FIXTURES_DIR = _REPO_ROOT / "tests" / "lib" / "fixtures"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _shared.spec_acs import parse_acs  # noqa: E402

# Path to the real specify-produced fixture.
_REAL_SPEC = str(_FIXTURES_DIR / "specify-sample-migration.md")


# ---------------------------------------------------------------------------
# Tests — parse_acs function (real fixture)
# ---------------------------------------------------------------------------


class TestParseAcsRealFixture(unittest.TestCase):
    """Round-trip against the real specify-sample-migration.md fixture."""

    @classmethod
    def setUpClass(cls):
        cls.acs = parse_acs(_REAL_SPEC)

    def test_fixture_exists(self):
        """Confirm the real fixture file is present — if this fails the repo is broken."""
        self.assertTrue(
            os.path.isfile(_REAL_SPEC),
            "Real fixture missing: {0}".format(_REAL_SPEC),
        )

    def test_returns_seven_acs(self):
        """specify-sample-migration.md has exactly AC-1 through AC-7."""
        self.assertEqual(len(self.acs), 7, "Expected 7 ACs, got {0}: {1}".format(
            len(self.acs), [a["id"] for a in self.acs]
        ))

    def test_ids_sequential(self):
        """AC ids are AC-1..AC-7 in order."""
        expected = ["AC-{0}".format(i) for i in range(1, 8)]
        actual = [a["id"] for a in self.acs]
        self.assertEqual(actual, expected)

    def test_all_unchecked(self):
        """All ACs in the fixture have - [ ] (unchecked)."""
        for ac in self.acs:
            self.assertFalse(ac["checked"], "Expected unchecked: {0}".format(ac))

    def test_ac1_text(self):
        """AC-1 text matches the EARS sentence in the fixture."""
        ac1 = self.acs[0]
        self.assertEqual(ac1["id"], "AC-1")
        self.assertIn("lerna", ac1["text"])

    def test_ac7_text(self):
        """AC-7 text mentions yarn lockfiles — the last AC in the fixture."""
        ac7 = self.acs[6]
        self.assertEqual(ac7["id"], "AC-7")
        self.assertIn("yarn", ac7["text"].lower())

    def test_ac3_ears_when(self):
        """AC-3 is a WHEN…THEN EARS sentence — text starts with 'WHEN'."""
        ac3 = self.acs[2]
        self.assertEqual(ac3["id"], "AC-3")
        self.assertTrue(
            ac3["text"].upper().startswith("WHEN"),
            "AC-3 text should start with WHEN: {0!r}".format(ac3["text"]),
        )

    def test_ac5_ears_if_then(self):
        """AC-5 is an IF…THEN EARS sentence — text starts with 'IF'."""
        ac5 = self.acs[4]
        self.assertEqual(ac5["id"], "AC-5")
        self.assertTrue(
            ac5["text"].upper().startswith("IF"),
            "AC-5 text should start with IF: {0!r}".format(ac5["text"]),
        )

    def test_subsection_populated(self):
        """Every AC carries a non-empty subsection string (### heading)."""
        for ac in self.acs:
            self.assertTrue(
                ac["subsection"],
                "AC {0} has empty subsection".format(ac["id"]),
            )

    def test_ac1_subsection(self):
        """AC-1 is under the '5.1 Tooling / artifact presence and absence' subsection."""
        ac1 = self.acs[0]
        self.assertIn("5.1", ac1["subsection"])

    def test_dict_shape(self):
        """Each AC dict has exactly the required keys."""
        required = {"id", "text", "checked", "subsection"}
        for ac in self.acs:
            self.assertEqual(set(ac.keys()), required)

    def test_text_is_stripped(self):
        """No AC text has leading or trailing whitespace."""
        for ac in self.acs:
            self.assertEqual(ac["text"], ac["text"].strip())


# ---------------------------------------------------------------------------
# Tests — checked variant and mixed state
# ---------------------------------------------------------------------------


class TestParseAcsChecked(unittest.TestCase):
    """parse_acs handles - [x] (checked) and - [X] (uppercase X) correctly."""

    def _spec(self, lines):
        """Wrap lines in a minimal spec with AC section."""
        header = (
            "# Spec\n\n"
            "## 5. Acceptance Criteria\n\n"
            "### 5.1 Functional\n\n"
        )
        return header + "\n".join(lines) + "\n\n## 6. Out of Scope\n\nN/A\n"

    def test_lowercase_x_checked(self):
        spec = self._spec(["- [x] **AC-1**: The system shall do it."])
        acs = parse_acs(spec)
        self.assertEqual(len(acs), 1)
        self.assertTrue(acs[0]["checked"])

    def test_uppercase_x_checked(self):
        spec = self._spec(["- [X] **AC-1**: The system shall do it."])
        acs = parse_acs(spec)
        self.assertEqual(len(acs), 1)
        self.assertTrue(acs[0]["checked"])

    def test_space_unchecked(self):
        spec = self._spec(["- [ ] **AC-1**: The system shall do it."])
        acs = parse_acs(spec)
        self.assertEqual(len(acs), 1)
        self.assertFalse(acs[0]["checked"])

    def test_mixed_checked_and_unchecked(self):
        spec = self._spec([
            "- [x] **AC-1**: Checked AC.",
            "- [ ] **AC-2**: Unchecked AC.",
            "- [x] **AC-3**: Also checked.",
        ])
        acs = parse_acs(spec)
        self.assertEqual(len(acs), 3)
        self.assertTrue(acs[0]["checked"])
        self.assertFalse(acs[1]["checked"])
        self.assertTrue(acs[2]["checked"])


# ---------------------------------------------------------------------------
# Tests — subsection tracking
# ---------------------------------------------------------------------------


class TestParseAcsSubsections(unittest.TestCase):
    """parse_acs tracks ### subsection headings correctly."""

    _SPEC = textwrap.dedent("""\
        # Spec

        ## 5. Acceptance Criteria

        ### 5.1 First subsection

        - [ ] **AC-1**: First AC.

        ### 5.2 Second subsection

        - [ ] **AC-2**: Second AC.
        - [ ] **AC-3**: Third AC.

        ## 6. Out of Scope

        N/A
    """)

    @classmethod
    def setUpClass(cls):
        cls.acs = parse_acs(cls._SPEC)

    def test_count(self):
        self.assertEqual(len(self.acs), 3)

    def test_ac1_subsection(self):
        self.assertIn("First subsection", self.acs[0]["subsection"])

    def test_ac2_subsection(self):
        self.assertIn("Second subsection", self.acs[1]["subsection"])

    def test_ac3_subsection_same_as_ac2(self):
        """AC-3 inherits the same subsection as AC-2 (no heading change)."""
        self.assertEqual(self.acs[1]["subsection"], self.acs[2]["subsection"])

    def test_ac_before_any_subsection_has_empty_subsection(self):
        """An AC that appears before any ### heading carries an empty subsection."""
        spec = (
            "## Acceptance Criteria\n\n"
            "- [ ] **AC-1**: No subsection above me.\n\n"
            "## 6. Out of Scope\n\n"
        )
        acs = parse_acs(spec)
        self.assertEqual(len(acs), 1)
        self.assertEqual(acs[0]["subsection"], "")


# ---------------------------------------------------------------------------
# Tests — boundary + error conditions
# ---------------------------------------------------------------------------


class TestParseAcsBoundary(unittest.TestCase):
    """parse_acs handles edge cases without crashing."""

    def test_empty_string(self):
        self.assertEqual(parse_acs(""), [])

    def test_no_ac_section(self):
        spec = "# Spec\n\n## 1. Overview\n\nSome text.\n"
        self.assertEqual(parse_acs(spec), [])

    def test_text_before_ac_section_ignored(self):
        """Narrative text before the AC section (including AC-like lines) is ignored."""
        spec = (
            "# Spec\n\n"
            "## 1. Overview\n\n"
            "- [ ] **AC-99**: Should not be parsed — before the AC section.\n\n"
            "## 5. Acceptance Criteria\n\n"
            "### 5.1 A\n\n"
            "- [ ] **AC-1**: Real AC.\n\n"
            "## 6. Out of Scope\n\n"
        )
        acs = parse_acs(spec)
        ids = [a["id"] for a in acs]
        self.assertEqual(ids, ["AC-1"])

    def test_nonexistent_file_path(self):
        """A path that doesn't exist as a file is treated as spec text (returns [])."""
        result = parse_acs("/nonexistent/path/does_not_exist.md")
        # os.path.exists returns False for this path, so parse_acs treats the
        # string as raw text. The string is not a spec, so result is [].
        self.assertEqual(result, [])

    def test_file_path_returns_acs(self):
        """When given a real file path, parse_acs reads it and returns ACs."""
        spec_text = (
            "# S\n\n"
            "## Acceptance Criteria\n\n"
            "### 5.1 A\n\n"
            "- [ ] **AC-1**: The system shall X.\n\n"
            "## 6. Out of Scope\n\n"
        )
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as fh:
            fh.write(spec_text)
            tmp_path = fh.name
        try:
            acs = parse_acs(tmp_path)
            self.assertEqual(len(acs), 1)
            self.assertEqual(acs[0]["id"], "AC-1")
        finally:
            os.unlink(tmp_path)

    def test_ac_section_stops_at_next_level2(self):
        """Parser stops when it sees ## 6. Out of Scope (not continuing into it)."""
        spec = (
            "# Spec\n\n"
            "## 5. Acceptance Criteria\n\n"
            "### 5.1 A\n\n"
            "- [ ] **AC-1**: Valid AC.\n\n"
            "## 6. Out of Scope\n\n"
            "- [ ] **AC-99**: Should NOT be parsed.\n"
        )
        acs = parse_acs(spec)
        ids = [a["id"] for a in acs]
        self.assertIn("AC-1", ids)
        self.assertNotIn("AC-99", ids)

    def test_na_subsections_skipped(self):
        """N/A lines in a subsection are skipped; AC lines are still parsed."""
        spec = (
            "## Acceptance Criteria\n\n"
            "### 5.1 A\n\n"
            "N/A — no applicable ACs in this category.\n\n"
            "### 5.2 B\n\n"
            "- [ ] **AC-1**: A real AC.\n\n"
            "## 6. Done\n"
        )
        acs = parse_acs(spec)
        self.assertEqual(len(acs), 1)
        self.assertEqual(acs[0]["id"], "AC-1")

    def test_verification_hint_line_not_captured_in_text(self):
        """The > Verification: hint line is not included in AC text."""
        spec = (
            "## Acceptance Criteria\n\n"
            "### 5.1 A\n\n"
            "- [ ] **AC-1**: The repository shall contain no occurrences of `lerna`.\n"
            "  > Verification: grep -rE 'lerna' . returns no matches\n\n"
            "## 6. Done\n"
        )
        acs = parse_acs(spec)
        self.assertEqual(len(acs), 1)
        # The text is only the AC line content, not the > hint.
        self.assertNotIn("Verification:", acs[0]["text"])

    def test_duplicate_ac_ids_accepted_in_order(self):
        """Duplicate AC ids are accepted and returned in encounter order."""
        spec = (
            "## Acceptance Criteria\n\n"
            "### 5.1 A\n\n"
            "- [ ] **AC-1**: First occurrence.\n"
            "- [ ] **AC-1**: Second occurrence (duplicate id).\n\n"
            "## 6. Done\n"
        )
        acs = parse_acs(spec)
        self.assertEqual(len(acs), 2)
        self.assertEqual(acs[0]["id"], "AC-1")
        self.assertEqual(acs[1]["id"], "AC-1")
        self.assertIn("First", acs[0]["text"])
        self.assertIn("Second", acs[1]["text"])


if __name__ == "__main__":
    unittest.main()
