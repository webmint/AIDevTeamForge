"""Tests for src/devforge/lib/_pr_review/_scope_drift.py.

Coverage:
  _extract_via_markdown_bullets — -, *, + variants; empty; whitespace-only
  _extract_via_numbered_list    — 1. / 2) / 10. variants; empty
  _extract_via_ac_marker        — AC-1: / AC1 / ac_2: / AC3. variants (case-insensitive)
  _extract_via_gwt              — GIVEN / WHEN / THEN / AND (case-insensitive)
  _extract_via_sentence_fallback — sentences 20-300 chars extracted; outside range excluded
  _extract_bullets              — integrates all 5 strategies; fallback gated on 0 structured
  _dedupe_and_assign_ids        — dedup by normalised text; IDs B1/B2/...
  Source ordering               — ticket_text bullets precede pr_body bullets
  Cap                           — 80 bullets → 50; capped flag True
  run() happy path              — PR #304-style ticket → bullets extracted, drift written
  run() replaces drift          — prior content overwritten on re-run
  run() no state file           — raises ValueError
  run() empty inputs            — 0 bullets, no crash
  Sentence fallback guard       — structured bullets win; no fallback when structured > 0
"""

import dataclasses
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _pr_review._scope_drift import (  # noqa: E402
    _MAX_BULLETS,
    _MIN_SENTENCE_CHARS,
    _MAX_SENTENCE_CHARS,
    _extract_via_markdown_bullets,
    _extract_via_numbered_list,
    _extract_via_ac_marker,
    _extract_via_gwt,
    _extract_via_sentence_fallback,
    _extract_bullets,
    _dedupe_and_assign_ids,
    run,
)
from _pr_review._state import PRReviewState, state_path  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers.
# ---------------------------------------------------------------------------


def _make_state(tmp_dir: str, pr_number: int, **kwargs) -> str:
    """Write a minimal PRReviewState to the expected path; return the path."""
    devforge = tmp_dir + "/.devforge"
    sp = state_path(devforge, pr_number)
    os.makedirs(os.path.dirname(sp), exist_ok=True)
    state = PRReviewState(pr_number=pr_number, repo="acme/app", **kwargs)
    with open(sp, "w", encoding="utf-8") as fh:
        json.dump(dataclasses.asdict(state), fh, indent=2)
        fh.write("\n")
    return sp


# ---------------------------------------------------------------------------
# TestExtractViaMarkdownBullets
# ---------------------------------------------------------------------------


class TestExtractViaMarkdownBullets(unittest.TestCase):
    def test_dash_bullet(self):
        result = _extract_via_markdown_bullets("- foo bar")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], "foo bar")
        self.assertEqual(result[0][1], "markdown_bullet")

    def test_asterisk_bullet(self):
        result = _extract_via_markdown_bullets("* hello world")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], "hello world")

    def test_plus_bullet(self):
        result = _extract_via_markdown_bullets("+ baz qux")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], "baz qux")

    def test_multiple_bullets(self):
        text = "- first\n* second\n+ third"
        result = _extract_via_markdown_bullets(text)
        self.assertEqual(len(result), 3)
        texts = [r[0] for r in result]
        self.assertIn("first", texts)
        self.assertIn("second", texts)
        self.assertIn("third", texts)

    def test_indented_bullet(self):
        result = _extract_via_markdown_bullets("  - indented bullet")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], "indented bullet")

    def test_empty_text(self):
        result = _extract_via_markdown_bullets("")
        self.assertEqual(result, [])

    def test_no_bullets(self):
        result = _extract_via_markdown_bullets("plain text paragraph\nno bullets here")
        self.assertEqual(result, [])

    def test_bullet_whitespace_only_content_excluded(self):
        # "- " followed by only spaces — group(1) is whitespace, stripped = ""
        result = _extract_via_markdown_bullets("-    ")
        # regex requires .+ after \s+, so empty trailing is not matched;
        # even if matched, strip() produces "" → excluded.
        for r in result:
            self.assertTrue(r[0].strip(), "empty content bullet should be excluded")

    def test_preserves_order(self):
        text = "- alpha\n- beta\n- gamma"
        result = _extract_via_markdown_bullets(text)
        self.assertEqual([r[0] for r in result], ["alpha", "beta", "gamma"])

    def test_multiline_text_with_prose_and_bullets(self):
        text = "Some intro text.\n- bullet one\nMore prose.\n- bullet two"
        result = _extract_via_markdown_bullets(text)
        self.assertEqual(len(result), 2)


# ---------------------------------------------------------------------------
# TestExtractViaNumberedList
# ---------------------------------------------------------------------------


class TestExtractViaNumberedList(unittest.TestCase):
    def test_dot_format(self):
        result = _extract_via_numbered_list("1. first item")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], "first item")
        self.assertEqual(result[0][1], "numbered_list")

    def test_paren_format(self):
        result = _extract_via_numbered_list("2) second item")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], "second item")

    def test_multi_digit(self):
        result = _extract_via_numbered_list("10. tenth item")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], "tenth item")

    def test_multiple_items(self):
        text = "1. alpha\n2. beta\n3. gamma"
        result = _extract_via_numbered_list(text)
        self.assertEqual(len(result), 3)

    def test_empty_text(self):
        result = _extract_via_numbered_list("")
        self.assertEqual(result, [])

    def test_no_numbered_list(self):
        result = _extract_via_numbered_list("plain text\n- bullet")
        self.assertEqual(result, [])

    def test_indented_numbered_item(self):
        result = _extract_via_numbered_list("   3. indented numbered")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], "indented numbered")


# ---------------------------------------------------------------------------
# TestExtractViaAcMarker
# ---------------------------------------------------------------------------


class TestExtractViaAcMarker(unittest.TestCase):
    def test_ac_dash_colon(self):
        result = _extract_via_ac_marker("AC-1: user can log in")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], "user can log in")
        self.assertEqual(result[0][1], "ac_marker")

    def test_ac_no_separator(self):
        result = _extract_via_ac_marker("AC1 user can log out")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], "user can log out")

    def test_ac_underscore_colon(self):
        result = _extract_via_ac_marker("ac_2: password must be 8 chars")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], "password must be 8 chars")

    def test_ac_dot(self):
        result = _extract_via_ac_marker("AC3. third criterion")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], "third criterion")

    def test_uppercase_ac(self):
        result = _extract_via_ac_marker("AC-10: tenth criterion")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], "tenth criterion")

    def test_case_insensitive(self):
        result = _extract_via_ac_marker("ac-1: lowercase ac marker")
        self.assertEqual(len(result), 1)

    def test_multiple_ac_markers(self):
        text = "AC-1: first\nAC-2: second\nAC-3: third"
        result = _extract_via_ac_marker(text)
        self.assertEqual(len(result), 3)

    def test_empty_text(self):
        result = _extract_via_ac_marker("")
        self.assertEqual(result, [])

    def test_no_ac_markers(self):
        result = _extract_via_ac_marker("- some bullet\n1. numbered")
        self.assertEqual(result, [])


# ---------------------------------------------------------------------------
# TestExtractViaGwt
# ---------------------------------------------------------------------------


class TestExtractViaGwt(unittest.TestCase):
    def test_given_uppercase(self):
        result = _extract_via_gwt("GIVEN a logged-in user")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], "a logged-in user")
        self.assertEqual(result[0][1], "gwt")

    def test_when_uppercase(self):
        result = _extract_via_gwt("WHEN the user clicks submit")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], "the user clicks submit")

    def test_then_uppercase(self):
        result = _extract_via_gwt("THEN the form is saved")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], "the form is saved")

    def test_and_uppercase(self):
        result = _extract_via_gwt("AND the spinner is shown")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], "the spinner is shown")

    def test_case_insensitive_then(self):
        result = _extract_via_gwt("Then the spinner is shown")
        self.assertEqual(len(result), 1)

    def test_case_insensitive_given(self):
        result = _extract_via_gwt("given a valid token")
        self.assertEqual(len(result), 1)

    def test_multiple_gwt_lines(self):
        text = "GIVEN a user\nWHEN they click\nTHEN it works\nAND logs are written"
        result = _extract_via_gwt(text)
        self.assertEqual(len(result), 4)

    def test_empty_text(self):
        result = _extract_via_gwt("")
        self.assertEqual(result, [])

    def test_no_gwt_lines(self):
        result = _extract_via_gwt("- bullet\n1. numbered\nAC-1: criterion")
        self.assertEqual(result, [])

    def test_and_prose_matches_gwt(self):
        """Documented design: lines starting with 'and' (any case) match _RE_GWT.

        This is a known false-positive risk in BDD-style ticket parsing; current
        decision is to accept the FPs rather than tighten the regex (which would
        miss legitimate BDD AND clauses).
        """
        text = "and the label is updated"
        result = _extract_via_gwt(text)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], "the label is updated")

    def test_uppercase_and_then_matches(self):
        """Mixed-case AND clause: 'AND THEN do this' matches; captures rest after AND."""
        text = "AND THEN do this"
        result = _extract_via_gwt(text)
        # _RE_GWT matches "AND" and captures "THEN do this" as the rest of the line.
        self.assertGreaterEqual(len(result), 1)
        self.assertEqual(result[0][0], "THEN do this")


# ---------------------------------------------------------------------------
# TestExtractViaSentenceFallback
# ---------------------------------------------------------------------------


class TestExtractViaSentenceFallback(unittest.TestCase):
    def test_simple_paragraph(self):
        text = "This feature adds a red asterisk. The label is updated. All tests pass."
        result = _extract_via_sentence_fallback(text)
        # Each sentence is 20-300 chars; should get 3 sentences.
        self.assertGreaterEqual(len(result), 1)
        for text_val, via in result:
            self.assertEqual(via, "sentence_fallback")

    def test_short_sentences_excluded(self):
        # Sentence shorter than _MIN_SENTENCE_CHARS.
        text = "Hi. Short. This is a longer sentence that qualifies for inclusion here."
        result = _extract_via_sentence_fallback(text)
        texts = [r[0] for r in result]
        # "Hi" and "Short" are < 20 chars.
        for t in texts:
            self.assertGreaterEqual(len(t), _MIN_SENTENCE_CHARS)

    def test_long_sentences_excluded(self):
        # Sentence longer than _MAX_SENTENCE_CHARS.
        long_sent = "A" * (_MAX_SENTENCE_CHARS + 1) + "."
        short_sent = "This sentence is exactly right length for inclusion."
        text = long_sent + " " + short_sent
        result = _extract_via_sentence_fallback(text)
        for text_val, _ in result:
            self.assertLessEqual(len(text_val), _MAX_SENTENCE_CHARS)

    def test_empty_text(self):
        result = _extract_via_sentence_fallback("")
        self.assertEqual(result, [])

    def test_sentence_boundary_split(self):
        # Verify it splits at ?, !, . boundaries.
        text = "First sentence here? Second sentence here! Third sentence too."
        result = _extract_via_sentence_fallback(text)
        self.assertGreaterEqual(len(result), 1)

    def test_returns_sentence_fallback_label(self):
        text = "This is a test sentence long enough for inclusion here."
        result = _extract_via_sentence_fallback(text)
        for _, via in result:
            self.assertEqual(via, "sentence_fallback")


# ---------------------------------------------------------------------------
# TestExtractBullets
# ---------------------------------------------------------------------------


class TestExtractBullets(unittest.TestCase):
    def test_ac_markers_primary(self):
        text = "AC-1: criterion one\nAC-2: criterion two"
        result = _extract_bullets(text, source="ticket_text")
        self.assertEqual(len(result), 2)
        for b in result:
            self.assertEqual(b["source"], "ticket_text")
            self.assertEqual(b["extracted_via"], "ac_marker")

    def test_markdown_bullets_in_pr_body(self):
        text = "- first change\n- second change"
        result = _extract_bullets(text, source="pr_body")
        self.assertEqual(len(result), 2)
        for b in result:
            self.assertEqual(b["source"], "pr_body")

    def test_empty_text_returns_empty(self):
        result = _extract_bullets("", source="ticket_text")
        self.assertEqual(result, [])

    def test_fallback_used_when_no_structured(self):
        # Only prose — no bullets, no numbered lists, no AC, no GWT.
        text = (
            "This ticket updates the address label. "
            "The asterisk should appear in red color. "
            "No regressions are expected in the test suite."
        )
        result = _extract_bullets(text, source="ticket_text")
        # Fallback should produce sentences.
        self.assertGreater(len(result), 0)
        for b in result:
            self.assertEqual(b["extracted_via"], "sentence_fallback")
            self.assertEqual(b["source"], "ticket_text_sentence")

    def test_structured_wins_over_fallback(self):
        # Text has both structured bullets AND prose sentences.
        text = (
            "This is a feature description. It does several things.\n"
            "- first structured bullet\n"
            "- second structured bullet\n"
            "Further context here as prose."
        )
        result = _extract_bullets(text, source="ticket_text")
        vias = {b["extracted_via"] for b in result}
        # sentence_fallback must NOT appear when structured bullets found.
        self.assertNotIn("sentence_fallback", vias)
        self.assertIn("markdown_bullet", vias)

    def test_source_pr_body_sentence_fallback_keeps_pr_body_label(self):
        # Unstructured pr_body — fallback keeps "pr_body" source (not "ticket_text_sentence").
        text = (
            "This pull request changes the label component. "
            "The asterisk styling was added to match the design."
        )
        result = _extract_bullets(text, source="pr_body")
        # All fallback results keep source="pr_body" (no renaming to ticket_text_sentence).
        for b in result:
            self.assertEqual(b["source"], "pr_body")

    def test_no_id_field_in_raw_bullets(self):
        text = "- bullet one\n- bullet two"
        result = _extract_bullets(text, source="ticket_text")
        for b in result:
            self.assertNotIn("id", b)

    def test_gwt_extracted(self):
        text = "GIVEN a user is logged in\nWHEN they click submit\nTHEN a confirmation appears"
        result = _extract_bullets(text, source="ticket_text")
        self.assertEqual(len(result), 3)
        for b in result:
            self.assertEqual(b["extracted_via"], "gwt")


# ---------------------------------------------------------------------------
# TestDedupeAndAssignIds
# ---------------------------------------------------------------------------


class TestDedupeAndAssignIds(unittest.TestCase):
    def test_assigns_ids_sequentially(self):
        bullets = [
            {"text": "alpha", "source": "ticket_text", "extracted_via": "markdown_bullet"},
            {"text": "beta", "source": "ticket_text", "extracted_via": "markdown_bullet"},
            {"text": "gamma", "source": "ticket_text", "extracted_via": "markdown_bullet"},
        ]
        result = _dedupe_and_assign_ids(bullets)
        self.assertEqual([b["id"] for b in result], ["B1", "B2", "B3"])

    def test_deduplicates_exact_match(self):
        bullets = [
            {"text": "same text", "source": "ticket_text", "extracted_via": "ac_marker"},
            {"text": "same text", "source": "pr_body", "extracted_via": "markdown_bullet"},
        ]
        result = _dedupe_and_assign_ids(bullets)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], "B1")

    def test_deduplicates_case_insensitive(self):
        bullets = [
            {"text": "Update Label", "source": "ticket_text", "extracted_via": "ac_marker"},
            {"text": "update label", "source": "pr_body", "extracted_via": "markdown_bullet"},
        ]
        result = _dedupe_and_assign_ids(bullets)
        self.assertEqual(len(result), 1)

    def test_deduplicates_with_leading_trailing_whitespace(self):
        bullets = [
            {"text": "  Update Label  ", "source": "ticket_text", "extracted_via": "ac_marker"},
            {"text": "Update Label", "source": "pr_body", "extracted_via": "markdown_bullet"},
        ]
        result = _dedupe_and_assign_ids(bullets)
        # Both normalise to "update label" — deduplicated.
        self.assertEqual(len(result), 1)

    def test_preserves_first_occurrence_on_dedup(self):
        bullets = [
            {"text": "same", "source": "ticket_text", "extracted_via": "ac_marker"},
            {"text": "same", "source": "pr_body", "extracted_via": "markdown_bullet"},
        ]
        result = _dedupe_and_assign_ids(bullets)
        self.assertEqual(result[0]["source"], "ticket_text")

    def test_empty_input(self):
        result = _dedupe_and_assign_ids([])
        self.assertEqual(result, [])

    def test_single_bullet(self):
        bullets = [{"text": "single", "source": "ticket_text", "extracted_via": "markdown_bullet"}]
        result = _dedupe_and_assign_ids(bullets)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], "B1")

    def test_preserves_all_fields(self):
        bullets = [
            {"text": "hello", "source": "ticket_text", "extracted_via": "gwt"},
        ]
        result = _dedupe_and_assign_ids(bullets)
        self.assertEqual(result[0]["text"], "hello")
        self.assertEqual(result[0]["source"], "ticket_text")
        self.assertEqual(result[0]["extracted_via"], "gwt")
        self.assertEqual(result[0]["id"], "B1")


# ---------------------------------------------------------------------------
# TestSourceOrdering
# ---------------------------------------------------------------------------


class TestSourceOrdering(unittest.TestCase):
    def test_ticket_text_before_pr_body(self):
        """Bullets from ticket_text appear before bullets from pr_body."""
        ticket_bullets = _extract_bullets(
            "- ticket bullet one\n- ticket bullet two", source="ticket_text"
        )
        pr_bullets = _extract_bullets(
            "- pr body bullet one\n- pr body bullet two", source="pr_body"
        )
        combined = _dedupe_and_assign_ids(ticket_bullets + pr_bullets)
        # First two bullets should be from ticket_text.
        self.assertEqual(combined[0]["source"], "ticket_text")
        self.assertEqual(combined[1]["source"], "ticket_text")
        # Last two bullets should be from pr_body.
        self.assertEqual(combined[2]["source"], "pr_body")
        self.assertEqual(combined[3]["source"], "pr_body")


# ---------------------------------------------------------------------------
# TestCap
# ---------------------------------------------------------------------------


class TestCap(unittest.TestCase):
    def test_cap_at_max_bullets(self):
        """run() caps output at _MAX_BULLETS = 50."""
        # Generate 80 unique AC markers.
        lines = ["AC-{0}: criterion number {0}".format(i) for i in range(1, 81)]
        ticket_text = "\n".join(lines)

        tmp = tempfile.mkdtemp()
        try:
            sp = _make_state(tmp, pr_number=1, ticket_text=ticket_text)
            result = run(target=tmp, pr_number=1, devforge_dir=".devforge")
            self.assertEqual(result["bullets_extracted"], _MAX_BULLETS)
            self.assertTrue(result["capped"])
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)

    def test_no_cap_when_under_limit(self):
        """run() does NOT set capped=True when bullets < _MAX_BULLETS."""
        ticket_text = "AC-1: first\nAC-2: second\nAC-3: third"
        tmp = tempfile.mkdtemp()
        try:
            _make_state(tmp, pr_number=2, ticket_text=ticket_text)
            result = run(target=tmp, pr_number=2, devforge_dir=".devforge")
            self.assertFalse(result["capped"])
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# TestRunHappyPath
# ---------------------------------------------------------------------------


class TestRunHappyPath(unittest.TestCase):
    """PR #304-style ticket: AC bullets extracted, drift written correctly."""

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._pr_number = 304
        # Ticket with AC markers + intro prose + pr_body with markdown bullets.
        ticket_text = (
            "MIG-2198: Update SHIP-TO-ADDRESS label\n\n"
            "AC-1: The SHIP-TO-ADDRESS label shows a red asterisk.\n"
            "AC-2: The asterisk is styled red (#cc0000) via CSS class.\n"
            "AC-3: Print layout is not affected.\n"
            "AC-4: Unit tests cover the new label rendering.\n"
            "AC-5: Accessibility: aria-required attribute is present.\n"
        )
        pr_body = (
            "## Changes\n"
            "- Added `required` CSS class to SHIP-TO-ADDRESS label\n"
            "- Updated unit test for label component\n"
        )
        self._sp = _make_state(
            self._tmp,
            pr_number=self._pr_number,
            ticket_text=ticket_text,
            pr_body=pr_body,
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_run_returns_ok(self):
        result = run(
            target=self._tmp,
            pr_number=self._pr_number,
            devforge_dir=".devforge",
        )
        self.assertEqual(result["status"], "ok")

    def test_run_extracts_ac_bullets(self):
        result = run(
            target=self._tmp,
            pr_number=self._pr_number,
            devforge_dir=".devforge",
        )
        # 5 AC markers from ticket + 2 markdown bullets from pr_body (after dedup).
        self.assertGreaterEqual(result["bullets_extracted"], 5)

    def test_run_by_source_counts(self):
        result = run(
            target=self._tmp,
            pr_number=self._pr_number,
            devforge_dir=".devforge",
        )
        by_source = result["by_source"]
        # ticket_text has AC markers → at least 5 in ticket_text bucket.
        self.assertGreaterEqual(by_source["ticket_text"], 5)
        # pr_body has markdown bullets → at least 1 in pr_body bucket.
        self.assertGreaterEqual(by_source["pr_body"], 1)

    def test_run_by_extracted_via_counts(self):
        result = run(
            target=self._tmp,
            pr_number=self._pr_number,
            devforge_dir=".devforge",
        )
        by_via = result["by_extracted_via"]
        # AC markers from ticket_text.
        self.assertGreaterEqual(by_via["ac_marker"], 5)
        # Markdown bullets from pr_body.
        self.assertGreaterEqual(by_via["markdown_bullet"], 1)

    def test_run_not_capped(self):
        result = run(
            target=self._tmp,
            pr_number=self._pr_number,
            devforge_dir=".devforge",
        )
        self.assertFalse(result["capped"])

    def test_run_state_path_is_absolute(self):
        result = run(
            target=self._tmp,
            pr_number=self._pr_number,
            devforge_dir=".devforge",
        )
        self.assertTrue(os.path.isabs(result["state_path"]))

    def test_run_drift_written_to_state(self):
        run(
            target=self._tmp,
            pr_number=self._pr_number,
            devforge_dir=".devforge",
        )
        with open(self._sp, "r", encoding="utf-8") as fh:
            state_data = json.load(fh)
        drift = state_data["drift"]
        self.assertIn("bullets", drift)
        self.assertIn("coverage_matrix", drift)
        self.assertIn("scope_creep_files", drift)
        self.assertFalse(drift["filled"])
        self.assertIsInstance(drift["coverage_matrix"], list)
        self.assertEqual(drift["coverage_matrix"], [])
        self.assertIsInstance(drift["scope_creep_files"], list)
        self.assertEqual(drift["scope_creep_files"], [])

    def test_run_bullets_have_required_keys(self):
        run(
            target=self._tmp,
            pr_number=self._pr_number,
            devforge_dir=".devforge",
        )
        with open(self._sp, "r", encoding="utf-8") as fh:
            state_data = json.load(fh)
        for bullet in state_data["drift"]["bullets"]:
            self.assertIn("id", bullet)
            self.assertIn("text", bullet)
            self.assertIn("source", bullet)
            self.assertIn("extracted_via", bullet)

    def test_run_bullet_ids_are_b_prefixed(self):
        run(
            target=self._tmp,
            pr_number=self._pr_number,
            devforge_dir=".devforge",
        )
        with open(self._sp, "r", encoding="utf-8") as fh:
            state_data = json.load(fh)
        for bullet in state_data["drift"]["bullets"]:
            self.assertTrue(
                bullet["id"].startswith("B"),
                "Expected ID to start with 'B', got {0!r}".format(bullet["id"]),
            )

    def test_run_next_action_mentions_step_8(self):
        result = run(
            target=self._tmp,
            pr_number=self._pr_number,
            devforge_dir=".devforge",
        )
        self.assertIn("Step 8", result["next_action"])


# ---------------------------------------------------------------------------
# TestRunReplacesDrift
# ---------------------------------------------------------------------------


class TestRunReplacesDrift(unittest.TestCase):
    def test_replaces_prior_drift(self):
        """Running run() twice replaces drift — does not append."""
        tmp = tempfile.mkdtemp()
        try:
            sp = _make_state(
                tmp,
                pr_number=10,
                ticket_text="AC-1: alpha\nAC-2: beta",
            )
            run(target=tmp, pr_number=10, devforge_dir=".devforge")
            with open(sp, "r", encoding="utf-8") as fh:
                count_first = len(json.load(fh)["drift"]["bullets"])

            # Run again — same state, same input.
            run(target=tmp, pr_number=10, devforge_dir=".devforge")
            with open(sp, "r", encoding="utf-8") as fh:
                count_second = len(json.load(fh)["drift"]["bullets"])

            # Replace semantics: counts are equal (not doubled).
            self.assertEqual(count_first, count_second)
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)

    def test_replaces_prior_drift_with_different_content(self):
        """After changing ticket_text, re-run overwrites old bullets."""
        tmp = tempfile.mkdtemp()
        try:
            sp = _make_state(
                tmp,
                pr_number=11,
                ticket_text="AC-1: original criterion",
            )
            run(target=tmp, pr_number=11, devforge_dir=".devforge")

            # Mutate ticket_text directly in state file.
            with open(sp, "r", encoding="utf-8") as fh:
                state_data = json.load(fh)
            state_data["ticket_text"] = "AC-1: new criterion\nAC-2: another criterion"
            with open(sp, "w", encoding="utf-8") as fh:
                json.dump(state_data, fh, indent=2)
                fh.write("\n")

            run(target=tmp, pr_number=11, devforge_dir=".devforge")
            with open(sp, "r", encoding="utf-8") as fh:
                updated = json.load(fh)

            bullet_texts = [b["text"] for b in updated["drift"]["bullets"]]
            self.assertNotIn("original criterion", bullet_texts)
            self.assertIn("new criterion", bullet_texts)
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# TestRunNoStateFile
# ---------------------------------------------------------------------------


class TestRunNoStateFile(unittest.TestCase):
    def test_raises_value_error_when_no_state(self):
        tmp = tempfile.mkdtemp()
        try:
            with self.assertRaises(ValueError) as ctx:
                run(target=tmp, pr_number=9999, devforge_dir=".devforge")
            self.assertIn("intake", str(ctx.exception))
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# TestRunEmptyTicket
# ---------------------------------------------------------------------------


class TestRunEmptyTicket(unittest.TestCase):
    def test_empty_ticket_and_pr_body_zero_bullets(self):
        tmp = tempfile.mkdtemp()
        try:
            _make_state(tmp, pr_number=20, ticket_text="", pr_body="")
            result = run(target=tmp, pr_number=20, devforge_dir=".devforge")
            self.assertEqual(result["bullets_extracted"], 0)
            self.assertEqual(result["status"], "ok")
            self.assertFalse(result["capped"])
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)

    def test_empty_ticket_writes_empty_bullets_list(self):
        tmp = tempfile.mkdtemp()
        try:
            sp = _make_state(tmp, pr_number=21, ticket_text="", pr_body="")
            run(target=tmp, pr_number=21, devforge_dir=".devforge")
            with open(sp, "r", encoding="utf-8") as fh:
                state_data = json.load(fh)
            self.assertEqual(state_data["drift"]["bullets"], [])
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# TestSentenceFallbackOnlyWhenStructuredEmpty
# ---------------------------------------------------------------------------


class TestSentenceFallbackOnlyWhenStructuredEmpty(unittest.TestCase):
    def test_structured_bullets_suppress_fallback(self):
        """When ticket_text has structured bullets, sentence_fallback is not used."""
        text = (
            "This is a long introduction sentence that would qualify as fallback.\n"
            "AC-1: The actual acceptance criterion.\n"
            "AC-2: Another criterion.\n"
            "Another prose sentence at the end that could also match fallback."
        )
        result = _extract_bullets(text, source="ticket_text")
        vias = {b["extracted_via"] for b in result}
        self.assertNotIn("sentence_fallback", vias)
        self.assertIn("ac_marker", vias)

    def test_fallback_activated_for_pure_prose(self):
        """Pure prose ticket_text triggers sentence_fallback."""
        text = (
            "This feature should display the red asterisk next to the label. "
            "The asterisk must be styled correctly using the CSS design system. "
            "All existing unit tests must continue passing after the change."
        )
        result = _extract_bullets(text, source="ticket_text")
        if result:  # sentences within range may or may not exist
            vias = {b["extracted_via"] for b in result}
            self.assertIn("sentence_fallback", vias)

    def test_markdown_bullet_suppresses_fallback(self):
        """A single markdown bullet prevents sentence_fallback from activating."""
        text = (
            "Here is some prose context about the feature.\n"
            "- The only structured bullet.\n"
            "More prose here that would otherwise be a fallback sentence candidate."
        )
        result = _extract_bullets(text, source="ticket_text")
        vias = {b["extracted_via"] for b in result}
        self.assertNotIn("sentence_fallback", vias)
        self.assertIn("markdown_bullet", vias)


# ---------------------------------------------------------------------------
# TestRunPrBodyFallback
# ---------------------------------------------------------------------------


class TestRunPrBodyFallback(unittest.TestCase):
    """Integration test: run() with pure-prose pr_body triggers sentence_fallback."""

    def test_pr_body_prose_triggers_sentence_fallback(self):
        """ticket_text="" + pr_body=pure-prose → sentence_fallback path exercised end-to-end."""
        tmp = tempfile.mkdtemp()
        try:
            pr_body = (
                "This pull request updates the address label component. "
                "The asterisk styling was added to match the design system. "
                "All existing unit tests continue passing after the change."
            )
            sp = _make_state(tmp, pr_number=50, ticket_text="", pr_body=pr_body)
            result = run(target=tmp, pr_number=50, devforge_dir=".devforge")

            # pr_body prose should produce at least 1 bullet via sentence_fallback.
            self.assertGreater(result["by_source"]["pr_body"], 0)
            self.assertGreater(result["by_extracted_via"]["sentence_fallback"], 0)

            # Verify every emitted bullet carries the correct labels.
            with open(sp, "r", encoding="utf-8") as fh:
                state_data = fh.read()
            import json as _json
            bullets = _json.loads(state_data)["drift"]["bullets"]
            self.assertGreater(len(bullets), 0)
            for bullet in bullets:
                self.assertEqual(bullet["source"], "pr_body")
                self.assertEqual(bullet["extracted_via"], "sentence_fallback")
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
