"""Tests for src/devforge/lib/_shared/ticket_file.py

Coverage:
  file_ticket / _format_ticket:
    Format verification:
      - Written file starts with "# Ticket NNN: <title>"
      - **Status**: Open
      - **Type**: as given
      - **Source**: as given
      - **Ticket**: as given, or "(none)" when absent/empty
      - **Reported**: as given (date)
      - Body appears verbatim after the metadata block

    Title resolution (_resolve_title):
      - Explicit title wins
      - No title, multi-line body -> first non-empty line
      - No title, blank body -> "Untitled ticket"
      - Title used for the H1 is the SAME title used for the slug

    Numbering:
      - Empty tickets/ dir -> starts at 001
      - Existing tickets (e.g. 003-*.md) -> starts at 004
      - Directory is its own sequence: a populated bugs/ sibling never
        shifts the first ticket off 001 (OQ-3)

    Slug sanitisation (reused from bug_file.slugify — promoted, OQ-1):
      - Spaces -> hyphens, capped at 30 chars

    Atomic write:
      - No .tmp-ticket- files left after success
      - tickets_dir created if absent

    Verbatim body / trailing-newline normalization:
      - Body containing a backtick and a $( sequence round-trips
        byte-identical (modulo the documented trailing-newline
        normalization)
      - Internal blank lines / multi-paragraph bodies preserved exactly
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _shared.ticket_file import (  # noqa: E402
    file_ticket,
    _format_ticket,
    _resolve_title,
)
from _shared.bug_file import file_bugs  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _item(
    title=None,
    body="An idea worth capturing.",
    type_="enhancement",
    ticket=None,
):
    d = {"body": body, "type": type_}
    if title is not None:
        d["title"] = title
    if ticket is not None:
        d["ticket"] = ticket
    return d


# ---------------------------------------------------------------------------
# Format tests
# ---------------------------------------------------------------------------


class TestFileTicketFormat(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.tickets_dir = os.path.join(self.tmp, "tickets")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write_one(self, **kwargs):
        source = kwargs.pop("source", "manual")
        date = kwargs.pop("date", "2026-09-04")
        path = file_ticket(
            tickets_dir=self.tickets_dir,
            item=_item(**kwargs),
            date=date,
            source=source,
        )
        with open(path, encoding="utf-8") as fh:
            return fh.read()

    def test_heading_uses_title(self):
        content = self._write_one(title="Add CSV export")
        self.assertIn("# Ticket 001: Add CSV export", content)

    def test_status_open(self):
        content = self._write_one()
        self.assertIn("**Status**: Open", content)

    def test_type_field(self):
        content = self._write_one(type_="task")
        self.assertIn("**Type**: task", content)

    def test_source_manual(self):
        content = self._write_one(source="manual")
        self.assertIn("**Source**: manual", content)

    def test_source_paste(self):
        content = self._write_one(source="paste")
        self.assertIn("**Source**: paste", content)

    def test_ticket_field_present(self):
        content = self._write_one(ticket="PROJ-123")
        self.assertIn("**Ticket**: PROJ-123", content)

    def test_ticket_field_absent_renders_none(self):
        content = self._write_one()
        self.assertIn("**Ticket**: (none)", content)

    def test_ticket_field_empty_string_renders_none(self):
        content = self._write_one(ticket="")
        self.assertIn("**Ticket**: (none)", content)

    def test_reported_date(self):
        content = self._write_one(date="2026-01-15")
        self.assertIn("**Reported**: 2026-01-15", content)

    def test_body_appears_verbatim(self):
        body = "Something noticed while reading src/cart.py."
        content = self._write_one(body=body)
        self.assertIn(body, content)

    def test_no_bug_only_sections(self):
        """A ticket file has none of bug_file's sections (no Fix Notes,
        no Related Issues, no File(s) table -- D3's field set is
        deliberately smaller)."""
        content = self._write_one()
        for absent in ("## Fix Notes", "## Related Issues", "## File(s)", "**Severity**"):
            self.assertNotIn(absent, content)


# ---------------------------------------------------------------------------
# Title resolution
# ---------------------------------------------------------------------------


class TestResolveTitle(unittest.TestCase):

    def test_explicit_title_wins(self):
        item = _item(title="Explicit title", body="line1\nline2")
        self.assertEqual(_resolve_title(item), "Explicit title")

    def test_falls_back_to_first_nonempty_body_line(self):
        item = _item(title=None, body="\n\n  First real line.  \nSecond line.")
        self.assertEqual(_resolve_title(item), "First real line.")

    def test_falls_back_to_untitled_ticket_when_body_blank(self):
        item = _item(body="   \n\n   ")
        self.assertEqual(_resolve_title(item), "Untitled ticket")

    def test_falls_back_to_untitled_ticket_when_body_missing(self):
        item = {"type": "task"}
        self.assertEqual(_resolve_title(item), "Untitled ticket")

    def test_title_whitespace_only_treated_as_absent(self):
        item = _item(title="   ", body="Real content here.")
        self.assertEqual(_resolve_title(item), "Real content here.")

    def test_h1_and_slug_use_the_same_resolved_title(self):
        """file_ticket must derive the filename slug from the SAME title
        _format_ticket renders in the H1 (unlike bug_file's file_bugs/
        _format_bug pair, which use two independent fallback literals)."""
        tmp = tempfile.mkdtemp()
        try:
            tickets_dir = os.path.join(tmp, "tickets")
            item = {"body": "First captured line stands in for the title.", "type": "task"}
            path = file_ticket(tickets_dir=tickets_dir, item=item, date="2026-09-04", source="manual")
            with open(path, encoding="utf-8") as fh:
                content = fh.read()
            self.assertIn("# Ticket 001: First captured line stands in for the title.", content)
            self.assertIn("first-captured-line-stands-in", os.path.basename(path))
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# Numbering
# ---------------------------------------------------------------------------


class TestFileTicketNumbering(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.tickets_dir = os.path.join(self.tmp, "tickets")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_empty_dir_starts_at_001(self):
        path = file_ticket(
            tickets_dir=self.tickets_dir,
            item=_item(),
            date="2026-09-04",
            source="manual",
        )
        self.assertTrue(os.path.basename(path).startswith("001-"))

    def test_existing_tickets_continue_numbering(self):
        os.makedirs(self.tickets_dir, exist_ok=True)
        for i in range(1, 4):
            p = os.path.join(self.tickets_dir, "{0:03d}-existing.md".format(i))
            with open(p, "w", encoding="utf-8") as fh:
                fh.write("# Ticket {0}\n".format(i))
        path = file_ticket(
            tickets_dir=self.tickets_dir,
            item=_item(),
            date="2026-09-04",
            source="manual",
        )
        self.assertTrue(os.path.basename(path).startswith("004-"))

    def test_populated_bugs_sibling_does_not_shift_ticket_numbering(self):
        """OQ-3: tickets/ and bugs/ are independent sequences. Populate a
        real bugs/ dir via the real producer (file_bugs) with THREE
        bugs, then confirm the first ticket still lands at 001."""
        bugs_dir = os.path.join(self.tmp, "bugs")
        issues = [
            {"title": "Bug one"},
            {"title": "Bug two"},
            {"title": "Bug three"},
        ]
        bug_paths = file_bugs(
            bugs_dir=bugs_dir,
            issues=issues,
            feature_spec_path="N/A",
            date="2026-09-04",
        )
        self.assertEqual(len(bug_paths), 3)

        ticket_path = file_ticket(
            tickets_dir=self.tickets_dir,
            item=_item(),
            date="2026-09-04",
            source="manual",
        )
        self.assertTrue(os.path.basename(ticket_path).startswith("001-"))

    def test_tickets_dir_created_if_absent(self):
        self.assertFalse(os.path.isdir(self.tickets_dir))
        file_ticket(
            tickets_dir=self.tickets_dir,
            item=_item(),
            date="2026-09-04",
            source="manual",
        )
        self.assertTrue(os.path.isdir(self.tickets_dir))


# ---------------------------------------------------------------------------
# Slug sanitisation (reused slugify — light smoke coverage; full coverage
# of slugify itself lives in tests/lib/_shared/test_bug_file.py)
# ---------------------------------------------------------------------------


class TestFileTicketSlug(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.tickets_dir = os.path.join(self.tmp, "tickets")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_slug_derived_from_title_is_capped_and_lowercase(self):
        long_title = "This Is A Very Long Ticket Title That Definitely Exceeds Thirty Characters"
        path = file_ticket(
            tickets_dir=self.tickets_dir,
            item=_item(title=long_title),
            date="2026-09-04",
            source="manual",
        )
        name = os.path.basename(path)
        slug_part = name[len("001-"):-len(".md")]
        self.assertLessEqual(len(slug_part), 30)
        self.assertEqual(slug_part, slug_part.lower())


# ---------------------------------------------------------------------------
# Atomic write + verbatim body preservation
# ---------------------------------------------------------------------------


class TestFileTicketAtomicAndVerbatim(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.tickets_dir = os.path.join(self.tmp, "tickets")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_no_tmp_files_left(self):
        file_ticket(
            tickets_dir=self.tickets_dir,
            item=_item(),
            date="2026-09-04",
            source="manual",
        )
        entries = os.listdir(self.tickets_dir)
        tmp_files = [e for e in entries if e.startswith(".tmp-ticket-")]
        self.assertEqual(tmp_files, [])

    def test_body_with_backtick_and_dollar_paren_round_trips(self):
        body = "Contains a `backtick` and a $(echo pwned) sequence.\n\nSecond paragraph."
        path = file_ticket(
            tickets_dir=self.tickets_dir,
            item=_item(body=body),
            date="2026-09-04",
            source="manual",
        )
        with open(path, encoding="utf-8") as fh:
            content = fh.read()
        # The body appears exactly, with no mangling of the special chars.
        self.assertIn(body, content)

    def test_body_internal_blank_lines_preserved(self):
        body = "Paragraph one.\n\n\nParagraph two after two blank lines."
        path = file_ticket(
            tickets_dir=self.tickets_dir,
            item=_item(body=body),
            date="2026-09-04",
            source="manual",
        )
        with open(path, encoding="utf-8") as fh:
            content = fh.read()
        self.assertIn(body, content)

    def test_trailing_newlines_normalized_not_duplicated(self):
        """Per the module docstring: body is trimmed only by a trailing-
        newline normalization (rstrip('\\n')) -- excess trailing blank
        lines in the input do not appear duplicated in the output, and
        the file ends with exactly one trailing newline."""
        body = "Some content.\n\n\n\n"
        path = file_ticket(
            tickets_dir=self.tickets_dir,
            item=_item(body=body),
            date="2026-09-04",
            source="manual",
        )
        with open(path, encoding="utf-8") as fh:
            content = fh.read()
        self.assertTrue(content.endswith("Some content.\n"))
        self.assertFalse(content.endswith("Some content.\n\n\n"))


if __name__ == "__main__":
    unittest.main()
