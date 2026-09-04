"""Tests for src/devforge/lib/_report_ticket/ — the report_ticket_helper subpackage.

Real-producer round-trip discipline (mandatory per repo rules):
  - write-ticket tests round-trip through the REAL shared writer
    file_ticket() (src/devforge/lib/_shared/ticket_file.py), asserting on
    actual on-disk output.
  - preflight tests use real filesystem layouts or stub project-config.json
    files (no monkey-patching of resolve_workspace internals).
  - No hand-authored markdown fixtures for format assertions — every format
    assertion reads files written by file_ticket() via the CLI path.
  - The backtick / $( round-trip tests are the build-time twin of plan 95's
    Phase 5 anchor 2 — OQ-6's whole point reduced to an assertion.

Coverage:
  cmd_preflight:
    - Standalone workspace (no project-config.json) → is_wrapper=False,
      tickets_dir ends with /tickets, root is an absolute path, exit 0.
    - Wrapper workspace (PROJECT_ROOT set in project-config.json) →
      is_wrapper=True, tickets_dir under install_root, exit 0.
    - JSON shape: exactly the keys tickets_dir, is_wrapper, root.
    - Default workspace_root "." resolves without error.

  cmd_write_ticket:
    - Happy path: file written to tickets/001-<slug>.md, exit 0.
    - Written file contains **Status**: Open, **Type**, **Source**.
    - --ticket provided (valid) → **Ticket**: <ID>.
    - --ticket omitted → **Ticket**: (none).
    - --title provided → H1 uses --title.
    - --title omitted → H1 falls back to first non-empty body line.
    - --body-file <path> → body byte-identical (incl. backtick/$( chars).
    - --body-file - (stdin) → body byte-identical (incl. backtick/$( chars).
    - Numbering starts at 001 in an empty tickets/ dir and continues from
      existing tickets; a populated bugs/ sibling never shifts it (OQ-3).

  Argument error paths (exit 2, nothing written):
    - Missing --tickets-dir / --date / --body-file / --type → exit 2.
    - Invalid --type / --source → exit 2.
    - Invalid --ticket → exit 2, tickets_dir left empty.
    - Empty --body-file content → exit 2.

  I/O error paths (exit 1):
    - --body-file pointing at a non-existent path → exit 1.

  CLI dispatch (via main()):
    - No subcommand → exit 2.
    - Unknown verb → exit 2.
    - preflight via main → exit 0, JSON on stdout.
    - write-ticket happy path via main → exit 0, JSON array on stdout.
"""

from __future__ import annotations

import io
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

# The modules under test.
from _report_ticket._cli import (  # noqa: E402
    main,
    cmd_preflight,
    cmd_write_ticket,
    _VALID_TYPES,
    _VALID_SOURCES,
)

# Real producer used for round-trip verification.
from _shared.ticket_file import file_ticket  # noqa: E402
from _shared.bug_file import file_bugs  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_main(argv, stdin_data=None):
    # type: (...) -> tuple
    """Run main(argv) capturing stdout/stderr.  Returns (exit_code, stdout, stderr)."""
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    old_stdin = sys.stdin

    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()

    if stdin_data is not None:
        sys.stdin = io.StringIO(stdin_data)

    sys.stdout = stdout_buf
    sys.stderr = stderr_buf

    try:
        exit_code = main(argv)
    except SystemExit as exc:
        exit_code = exc.code if isinstance(exc.code, int) else 2
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        sys.stdin = old_stdin

    return exit_code, stdout_buf.getvalue(), stderr_buf.getvalue()


def _make_tickets_dir(tmp):
    # type: (str) -> str
    tickets_dir = os.path.join(tmp, "tickets")
    os.makedirs(tickets_dir, exist_ok=True)
    return tickets_dir


def _write_body_file(tmp, content, name="body.txt"):
    # type: (str, str, str) -> str
    path = os.path.join(tmp, name)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    return path


def _minimal_write_ticket_argv(tickets_dir, body_file, type_="enhancement"):
    # type: (str, str, str) -> list
    return [
        "write-ticket",
        "--tickets-dir", tickets_dir,
        "--date", "2026-09-04",
        "--body-file", body_file,
        "--type", type_,
    ]


def _read_first_ticket(tickets_dir):
    # type: (str) -> str
    """Read the first ticket file's raw text.

    newline="" disables universal-newline translation on read, so a
    written \\r\\n survives the test's own verification step unmangled
    (see TestWriteTicketBodyRoundTrip's CRLF test) -- for every other
    (LF-only) fixture this is a no-op, identical to a plain open().
    """
    files = sorted(f for f in os.listdir(tickets_dir) if f.endswith(".md"))
    assert files, "no .md files in tickets_dir: {0}".format(tickets_dir)
    with open(os.path.join(tickets_dir, files[0]), "r", encoding="utf-8", newline="") as fh:
        return fh.read()


# ---------------------------------------------------------------------------
# Tests: preflight verb
# ---------------------------------------------------------------------------


class TestPreflight(unittest.TestCase):

    def test_standalone_workspace_is_wrapper_false(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, out, _ = _run_main(["preflight", "--workspace-root", tmp])
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertFalse(data["is_wrapper"])

    def test_standalone_tickets_dir_ends_with_tickets(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, out, _ = _run_main(["preflight", "--workspace-root", tmp])
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertTrue(data["tickets_dir"].endswith("tickets"))

    def test_standalone_root_is_absolute(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, out, _ = _run_main(["preflight", "--workspace-root", tmp])
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertTrue(os.path.isabs(data["root"]))

    def test_json_shape_has_exactly_required_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, out, _ = _run_main(["preflight", "--workspace-root", tmp])
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(sorted(data.keys()), ["is_wrapper", "root", "tickets_dir"])

    def test_exit_code_is_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, _, _ = _run_main(["preflight", "--workspace-root", tmp])
        self.assertEqual(code, 0)

    def test_wrapper_workspace_is_wrapper_true(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge_dir = os.path.join(tmp, ".devforge")
            os.makedirs(devforge_dir)
            config = {"PROJECT_ROOT": "src/product-app"}
            config_path = os.path.join(devforge_dir, "project-config.json")
            with open(config_path, "w", encoding="utf-8") as fh:
                json.dump(config, fh)
            code, out, _ = _run_main(["preflight", "--workspace-root", tmp])
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertTrue(data["is_wrapper"])

    def test_wrapper_tickets_dir_is_under_install_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge_dir = os.path.join(tmp, ".devforge")
            os.makedirs(devforge_dir)
            config = {"PROJECT_ROOT": "src/product-app"}
            with open(os.path.join(devforge_dir, "project-config.json"), "w", encoding="utf-8") as fh:
                json.dump(config, fh)
            code, out, _ = _run_main(["preflight", "--workspace-root", tmp])
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertTrue(data["tickets_dir"].startswith(str(Path(tmp).resolve())))
        self.assertNotIn("product-app", data["tickets_dir"])

    def test_default_workspace_root_resolves(self):
        code, out, _ = _run_main(["preflight"])
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertIn("tickets_dir", data)


# ---------------------------------------------------------------------------
# Tests: write-ticket — happy path
# ---------------------------------------------------------------------------


class TestWriteTicketHappyPath(unittest.TestCase):

    def test_exit_code_zero_on_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            tickets_dir = _make_tickets_dir(tmp)
            body_file = _write_body_file(tmp, "Add CSV export to the reports page.")
            code, _, _ = _run_main(_minimal_write_ticket_argv(tickets_dir, body_file))
        self.assertEqual(code, 0)

    def test_stdout_is_json_array_of_one_written_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            tickets_dir = _make_tickets_dir(tmp)
            body_file = _write_body_file(tmp, "Add CSV export.")
            code, out, _ = _run_main(_minimal_write_ticket_argv(tickets_dir, body_file))
            paths = json.loads(out)
            self.assertTrue(os.path.isfile(paths[0]))
        self.assertEqual(code, 0)
        self.assertIsInstance(paths, list)
        self.assertEqual(len(paths), 1)

    def test_file_name_starts_with_001(self):
        with tempfile.TemporaryDirectory() as tmp:
            tickets_dir = _make_tickets_dir(tmp)
            body_file = _write_body_file(tmp, "Add CSV export.")
            _, out, _ = _run_main(_minimal_write_ticket_argv(tickets_dir, body_file))
            paths = json.loads(out)
        self.assertTrue(os.path.basename(paths[0]).startswith("001-"))

    def test_status_field_is_open(self):
        with tempfile.TemporaryDirectory() as tmp:
            tickets_dir = _make_tickets_dir(tmp)
            body_file = _write_body_file(tmp, "Add CSV export.")
            _run_main(_minimal_write_ticket_argv(tickets_dir, body_file))
            content = _read_first_ticket(tickets_dir)
        self.assertIn("**Status**: Open", content)

    def test_type_field_persists(self):
        with tempfile.TemporaryDirectory() as tmp:
            tickets_dir = _make_tickets_dir(tmp)
            body_file = _write_body_file(tmp, "Add CSV export.")
            _run_main(_minimal_write_ticket_argv(tickets_dir, body_file, type_="task"))
            content = _read_first_ticket(tickets_dir)
        self.assertIn("**Type**: task", content)

    def test_default_source_is_manual(self):
        with tempfile.TemporaryDirectory() as tmp:
            tickets_dir = _make_tickets_dir(tmp)
            body_file = _write_body_file(tmp, "Add CSV export.")
            _run_main(_minimal_write_ticket_argv(tickets_dir, body_file))
            content = _read_first_ticket(tickets_dir)
        self.assertIn("**Source**: manual", content)

    def test_explicit_source_paste(self):
        with tempfile.TemporaryDirectory() as tmp:
            tickets_dir = _make_tickets_dir(tmp)
            body_file = _write_body_file(tmp, "Pasted tracker text.")
            argv = _minimal_write_ticket_argv(tickets_dir, body_file, type_="imported") + ["--source", "paste"]
            _run_main(argv)
            content = _read_first_ticket(tickets_dir)
        self.assertIn("**Source**: paste", content)

    def test_valid_ticket_id_persists(self):
        with tempfile.TemporaryDirectory() as tmp:
            tickets_dir = _make_tickets_dir(tmp)
            body_file = _write_body_file(tmp, "Pasted tracker text.")
            argv = _minimal_write_ticket_argv(tickets_dir, body_file) + ["--ticket", "PROJ-123"]
            _run_main(argv)
            content = _read_first_ticket(tickets_dir)
        self.assertIn("**Ticket**: PROJ-123", content)

    def test_omitted_ticket_renders_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            tickets_dir = _make_tickets_dir(tmp)
            body_file = _write_body_file(tmp, "An idea.")
            _run_main(_minimal_write_ticket_argv(tickets_dir, body_file))
            content = _read_first_ticket(tickets_dir)
        self.assertIn("**Ticket**: (none)", content)

    def test_title_provided_appears_in_heading(self):
        with tempfile.TemporaryDirectory() as tmp:
            tickets_dir = _make_tickets_dir(tmp)
            body_file = _write_body_file(tmp, "Some longer body text.")
            argv = _minimal_write_ticket_argv(tickets_dir, body_file) + ["--title", "Short Title"]
            _run_main(argv)
            content = _read_first_ticket(tickets_dir)
        self.assertIn("# Ticket 001: Short Title", content)

    def test_title_omitted_falls_back_to_first_body_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            tickets_dir = _make_tickets_dir(tmp)
            body_file = _write_body_file(tmp, "First line becomes the title.\nSecond line does not.")
            _run_main(_minimal_write_ticket_argv(tickets_dir, body_file))
            content = _read_first_ticket(tickets_dir)
        self.assertIn("# Ticket 001: First line becomes the title.", content)
        self.assertNotIn("# Ticket 001: Second line does not.", content)

    def test_reported_date_persists(self):
        with tempfile.TemporaryDirectory() as tmp:
            tickets_dir = _make_tickets_dir(tmp)
            body_file = _write_body_file(tmp, "An idea.")
            argv = ["write-ticket", "--tickets-dir", tickets_dir, "--date", "2026-01-15",
                    "--body-file", body_file, "--type", "enhancement"]
            _run_main(argv)
            content = _read_first_ticket(tickets_dir)
        self.assertIn("**Reported**: 2026-01-15", content)


# ---------------------------------------------------------------------------
# Tests: write-ticket — body-file / stdin round-trip (OQ-6)
# ---------------------------------------------------------------------------


class TestWriteTicketBodyRoundTrip(unittest.TestCase):

    _AWKWARD_BODY = (
        "Pasted ticket text with a `backtick` right here and a "
        "$(echo pwned) sequence, plus a $VAR reference and \"quotes\".\n\n"
        "Second paragraph, still awkward."
    )

    def test_body_file_round_trips_byte_identical(self):
        """A body containing a backtick and a $( sequence round-trips
        byte-identical through write-ticket --body-file <path>."""
        with tempfile.TemporaryDirectory() as tmp:
            tickets_dir = _make_tickets_dir(tmp)
            body_file = _write_body_file(tmp, self._AWKWARD_BODY)
            argv = _minimal_write_ticket_argv(tickets_dir, body_file, type_="imported") + [
                "--ticket", "PROJ-123",
            ]
            code, _, _ = _run_main(argv)
            content = _read_first_ticket(tickets_dir)
        self.assertEqual(code, 0)
        self.assertIn(self._AWKWARD_BODY, content)

    def test_stdin_round_trips_byte_identical(self):
        """The same awkward body, delivered via --body-file - (stdin),
        round-trips byte-identical."""
        with tempfile.TemporaryDirectory() as tmp:
            tickets_dir = _make_tickets_dir(tmp)
            argv = [
                "write-ticket",
                "--tickets-dir", tickets_dir,
                "--date", "2026-09-04",
                "--body-file", "-",
                "--type", "imported",
                "--ticket", "PROJ-123",
            ]
            code, _, _ = _run_main(argv, stdin_data=self._AWKWARD_BODY)
            content = _read_first_ticket(tickets_dir)
        self.assertEqual(code, 0)
        self.assertIn(self._AWKWARD_BODY, content)

    def test_body_file_and_stdin_produce_identical_bodies(self):
        """The two argument-surface routes render the exact same body
        into the file — proving neither path mangles the text
        differently from the other."""
        with tempfile.TemporaryDirectory() as tmp:
            tickets_dir_a = os.path.join(tmp, "tickets-a")
            tickets_dir_b = os.path.join(tmp, "tickets-b")
            body_file = _write_body_file(tmp, self._AWKWARD_BODY)

            argv_file = [
                "write-ticket", "--tickets-dir", tickets_dir_a, "--date", "2026-09-04",
                "--body-file", body_file, "--type", "imported",
            ]
            argv_stdin = [
                "write-ticket", "--tickets-dir", tickets_dir_b, "--date", "2026-09-04",
                "--body-file", "-", "--type", "imported",
            ]
            _run_main(argv_file)
            _run_main(argv_stdin, stdin_data=self._AWKWARD_BODY)

            content_a = _read_first_ticket(tickets_dir_a)
            content_b = _read_first_ticket(tickets_dir_b)

        # Both files carry the identical body text.
        self.assertIn(self._AWKWARD_BODY, content_a)
        self.assertIn(self._AWKWARD_BODY, content_b)

    def test_crlf_body_preserved_identically_via_file_and_stdin(self):
        """python-reviewer finding 1: open(--body-file) must NOT
        universal-newline-translate \\r\\n -> \\n while the stdin route
        (io.StringIO, which never translates) leaves it alone — that
        divergence would make the file route silently lossy relative to
        stdin.  Both routes must return the exact \\r\\n bytes, and the
        two routes must be identical to each other."""
        crlf_body = (
            "Line one.\r\nLine two with a `backtick`.\r\nLine three, "
            "no trailing newline so rstrip('\\n') is a no-op here."
        )

        with tempfile.TemporaryDirectory() as tmp:
            tickets_dir_a = os.path.join(tmp, "tickets-crlf-a")
            tickets_dir_b = os.path.join(tmp, "tickets-crlf-b")

            # Write the fixture with newline="" so the file on disk
            # carries the literal \r\n bytes, with no platform-dependent
            # translation on write either.
            body_file = os.path.join(tmp, "crlf_body.txt")
            with open(body_file, "w", encoding="utf-8", newline="") as fh:
                fh.write(crlf_body)

            argv_file = [
                "write-ticket", "--tickets-dir", tickets_dir_a, "--date", "2026-09-04",
                "--body-file", body_file, "--type", "imported",
            ]
            argv_stdin = [
                "write-ticket", "--tickets-dir", tickets_dir_b, "--date", "2026-09-04",
                "--body-file", "-", "--type", "imported",
            ]
            code_file, _, _ = _run_main(argv_file)
            code_stdin, _, _ = _run_main(argv_stdin, stdin_data=crlf_body)

            content_a = _read_first_ticket(tickets_dir_a)
            content_b = _read_first_ticket(tickets_dir_b)

        self.assertEqual(code_file, 0)
        self.assertEqual(code_stdin, 0)

        # Neither route collapsed \r\n to \n.
        self.assertIn(crlf_body, content_a)
        self.assertIn(crlf_body, content_b)

        # The two routes are byte-identical to each other (same body,
        # same title fallback, same type/source/ticket/date).
        self.assertEqual(content_a, content_b)


# ---------------------------------------------------------------------------
# Tests: write-ticket — numbering
# ---------------------------------------------------------------------------


class TestWriteTicketNumbering(unittest.TestCase):

    def test_numbering_continues_from_existing(self):
        with tempfile.TemporaryDirectory() as tmp:
            tickets_dir = _make_tickets_dir(tmp)
            with open(os.path.join(tickets_dir, "003-existing.md"), "w") as fh:
                fh.write("# Ticket 003: existing\n")
            body_file = _write_body_file(tmp, "Another idea.")
            _, out, _ = _run_main(_minimal_write_ticket_argv(tickets_dir, body_file))
            paths = json.loads(out)
        self.assertTrue(os.path.basename(paths[0]).startswith("004-"))

    def test_populated_bugs_sibling_does_not_shift_first_ticket_off_001(self):
        """OQ-3: bugs/ and tickets/ are independent sequences.  Populate
        a real bugs/ dir via the real producer file_bugs() and confirm
        the first ticket written afterward still lands at 001."""
        with tempfile.TemporaryDirectory() as tmp:
            bugs_dir = os.path.join(tmp, "bugs")
            file_bugs(
                bugs_dir=bugs_dir,
                issues=[{"title": "Bug one"}, {"title": "Bug two"}],
                feature_spec_path="N/A",
                date="2026-09-04",
            )
            tickets_dir = _make_tickets_dir(tmp)
            body_file = _write_body_file(tmp, "First captured idea.")
            _, out, _ = _run_main(_minimal_write_ticket_argv(tickets_dir, body_file))
            paths = json.loads(out)
        self.assertTrue(os.path.basename(paths[0]).startswith("001-"))


# ---------------------------------------------------------------------------
# Tests: argument error paths — exit 2, nothing written
# ---------------------------------------------------------------------------


class TestWriteTicketArgErrors(unittest.TestCase):

    def test_missing_tickets_dir_exits_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            body_file = _write_body_file(tmp, "An idea.")
            argv = ["write-ticket", "--date", "2026-09-04", "--body-file", body_file,
                    "--type", "enhancement"]
            code, _, _ = _run_main(argv)
        self.assertEqual(code, 2)

    def test_missing_date_exits_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            tickets_dir = _make_tickets_dir(tmp)
            body_file = _write_body_file(tmp, "An idea.")
            argv = ["write-ticket", "--tickets-dir", tickets_dir, "--body-file", body_file,
                    "--type", "enhancement"]
            code, _, _ = _run_main(argv)
        self.assertEqual(code, 2)

    def test_missing_body_file_exits_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            tickets_dir = _make_tickets_dir(tmp)
            argv = ["write-ticket", "--tickets-dir", tickets_dir, "--date", "2026-09-04",
                    "--type", "enhancement"]
            code, _, _ = _run_main(argv)
        self.assertEqual(code, 2)

    def test_missing_type_exits_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            tickets_dir = _make_tickets_dir(tmp)
            body_file = _write_body_file(tmp, "An idea.")
            argv = ["write-ticket", "--tickets-dir", tickets_dir, "--date", "2026-09-04",
                    "--body-file", body_file]
            code, _, _ = _run_main(argv)
        self.assertEqual(code, 2)

    def test_invalid_type_exits_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            tickets_dir = _make_tickets_dir(tmp)
            body_file = _write_body_file(tmp, "An idea.")
            argv = _minimal_write_ticket_argv(tickets_dir, body_file, type_="defect")
            code, _, _ = _run_main(argv)
        self.assertEqual(code, 2)

    def test_invalid_source_exits_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            tickets_dir = _make_tickets_dir(tmp)
            body_file = _write_body_file(tmp, "An idea.")
            argv = _minimal_write_ticket_argv(tickets_dir, body_file) + ["--source", "verify"]
            code, _, _ = _run_main(argv)
        self.assertEqual(code, 2)

    def test_invalid_ticket_exits_2_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            tickets_dir = _make_tickets_dir(tmp)
            body_file = _write_body_file(tmp, "An idea.")
            argv = _minimal_write_ticket_argv(tickets_dir, body_file) + ["--ticket", "proj-123"]
            code, _, err = _run_main(argv)
            remaining = [f for f in os.listdir(tickets_dir) if f.endswith(".md")]
        self.assertEqual(code, 2)
        self.assertEqual(remaining, [])
        self.assertIn("--ticket", err)

    def test_invalid_ticket_shape_bare_number_exits_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            tickets_dir = _make_tickets_dir(tmp)
            body_file = _write_body_file(tmp, "An idea.")
            argv = _minimal_write_ticket_argv(tickets_dir, body_file) + ["--ticket", "123"]
            code, _, _ = _run_main(argv)
        self.assertEqual(code, 2)

    def test_explicit_empty_ticket_string_exits_2_rather_than_none(self):
        """An explicit --ticket "" is a distinct case from OMITTING
        --ticket: omission renders (none), but an explicitly-passed
        empty/blank string is treated as invalid input and rejected
        rather than silently downgraded to (none) — a real value was
        expected and none arrived, which normalize_ticket's own
        no-ticket-supplied message names."""
        with tempfile.TemporaryDirectory() as tmp:
            tickets_dir = _make_tickets_dir(tmp)
            body_file = _write_body_file(tmp, "An idea.")
            argv = _minimal_write_ticket_argv(tickets_dir, body_file) + ["--ticket", ""]
            code, _, err = _run_main(argv)
            remaining = [f for f in os.listdir(tickets_dir) if f.endswith(".md")]
        self.assertEqual(code, 2)
        self.assertEqual(remaining, [])
        self.assertIn("--ticket", err)

    def test_empty_body_file_content_exits_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            tickets_dir = _make_tickets_dir(tmp)
            body_file = _write_body_file(tmp, "   \n\n  ")
            argv = _minimal_write_ticket_argv(tickets_dir, body_file)
            code, _, _ = _run_main(argv)
            remaining = [f for f in os.listdir(tickets_dir) if f.endswith(".md")]
        self.assertEqual(code, 2)
        self.assertEqual(remaining, [])


# ---------------------------------------------------------------------------
# Tests: I/O error path — exit 1
# ---------------------------------------------------------------------------


class TestWriteTicketIOErrors(unittest.TestCase):

    def test_nonexistent_body_file_exits_1(self):
        with tempfile.TemporaryDirectory() as tmp:
            tickets_dir = _make_tickets_dir(tmp)
            missing = os.path.join(tmp, "does-not-exist.txt")
            argv = _minimal_write_ticket_argv(tickets_dir, missing)
            code, _, err = _run_main(argv)
            remaining = [f for f in os.listdir(tickets_dir) if f.endswith(".md")]
        self.assertEqual(code, 1)
        self.assertEqual(remaining, [])
        self.assertIn("--body-file", err)


# ---------------------------------------------------------------------------
# Tests: CLI dispatch
# ---------------------------------------------------------------------------


class TestCLIDispatch(unittest.TestCase):

    def test_no_subcommand_exits_2(self):
        code, _, _ = _run_main([])
        self.assertEqual(code, 2)

    def test_unknown_verb_exits_2(self):
        code, _, _ = _run_main(["unknown-verb"])
        self.assertEqual(code, 2)

    def test_preflight_emits_valid_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, out, _ = _run_main(["preflight", "--workspace-root", tmp])
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertIsInstance(data, dict)

    def test_write_ticket_happy_path_via_main(self):
        with tempfile.TemporaryDirectory() as tmp:
            tickets_dir = _make_tickets_dir(tmp)
            body_file = _write_body_file(tmp, "An idea.")
            argv = _minimal_write_ticket_argv(tickets_dir, body_file)
            code, out, _ = _run_main(argv)
        self.assertEqual(code, 0)
        paths = json.loads(out)
        self.assertIsInstance(paths, list)
        self.assertEqual(len(paths), 1)


# ---------------------------------------------------------------------------
# Tests: direct-call second-layer defences (mirrors test_report_bug_helper.py)
# ---------------------------------------------------------------------------


class TestDirectCallGuards(unittest.TestCase):

    def test_direct_call_missing_tickets_dir_exits_2(self):
        import argparse as _ap
        ns = _ap.Namespace(tickets_dir=None, date="2026-09-04", body_file="-",
                            title=None, type="enhancement", source="manual", ticket=None)
        old_stdin, old_stderr = sys.stdin, sys.stderr
        sys.stdin = io.StringIO("x")
        sys.stderr = io.StringIO()
        try:
            code = cmd_write_ticket(ns)
            captured = sys.stderr.getvalue()
        finally:
            sys.stdin, sys.stderr = old_stdin, old_stderr
        self.assertEqual(code, 2)
        self.assertIn("--tickets-dir", captured)

    def test_direct_call_invalid_type_exits_2(self):
        import argparse as _ap
        with tempfile.TemporaryDirectory() as tmp:
            tickets_dir = _make_tickets_dir(tmp)
            ns = _ap.Namespace(tickets_dir=tickets_dir, date="2026-09-04", body_file="-",
                                title=None, type="defect", source="manual", ticket=None)
            old_stdin, old_stderr = sys.stdin, sys.stderr
            sys.stdin = io.StringIO("x")
            sys.stderr = io.StringIO()
            try:
                code = cmd_write_ticket(ns)
                captured = sys.stderr.getvalue()
            finally:
                sys.stdin, sys.stderr = old_stdin, old_stderr
        self.assertEqual(code, 2)
        self.assertTrue(any(v in captured for v in _VALID_TYPES))


# ---------------------------------------------------------------------------
# Tests: valid vocabulary constants
# ---------------------------------------------------------------------------


class TestValidVocab(unittest.TestCase):

    def test_valid_types_are_exactly_enhancement_task_imported(self):
        self.assertEqual(set(_VALID_TYPES), {"enhancement", "task", "imported"})

    def test_valid_sources_are_exactly_manual_paste(self):
        self.assertEqual(set(_VALID_SOURCES), {"manual", "paste"})


if __name__ == "__main__":
    unittest.main()
