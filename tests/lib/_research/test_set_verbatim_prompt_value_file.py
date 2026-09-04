"""Tests for _research/_cmds_basic.py's set-verbatim-prompt --value-file option.

95-TICKET-CAPTURE-LANE-PLAN.md Phase 3a -- /devforge:research's Phase 3
consumer arm must seed memo.verbatim_prompt from a ticket file's body, but
set-verbatim-prompt previously took ONLY inline --value, which would force a
pasted tracker-ticket body through a shell argument -- exactly the OQ-6/
Trap-7 failure the capture side (_report_ticket/_cli.py --body-file) already
refused. This file covers the additive --value-file <path> route (mutually
exclusive with --value, exactly one required) added to close that gap.

This is a NEW test file under tests/lib/_research/ rather than an addition
to the pre-existing legacy monolith tests/lib/test_research_helper.py --
mirrors test_cmds_feature_alloc.py's precedent (a new option on an existing
verb gets its own focused file; the monolith is not grown further). The
monolith's existing --value call sites (asserted unaffected here via the
"inline --value path unchanged" tests) are not duplicated.

Every set-verbatim-prompt call here is a real subprocess invocation of
research_helper.py, and every assertion reads memo.verbatim_prompt back via
a real read-memo subprocess call (parsing its stdout JSON) -- never a
hand-authored fixture and never a private-attribute peek at in-process
state.

Coverage:
  --value-file <path>:
    - Body containing a backtick + $( sequence + embedded CRLF round-trips
      into state with the CRLF preserved (no universal-newline collapse to
      LF) -- the build-time twin of the capture side's own CRLF test.
    - Same awkward body via --value-file - (stdin) -- byte-identical to the
      --value-file <path> result.
    - Leading/trailing whitespace (including a trailing CRLF) is stripped,
      matching _validate_scalar's contract on the --value route.
  --value (inline, pre-existing route):
    - Unchanged: still works, still stripped, byte-identical to prior
      behaviour.
  Argument-shape errors (exit 2, memo.verbatim_prompt untouched):
    - Both --value and --value-file supplied -> exit 2 (argparse mutual
      exclusion).
    - Neither supplied -> exit 2 (argparse required-group).
    - --value-file pointing at an empty (or whitespace-only) file -> exit 2,
      consistent with --value's own empty guard.
  I/O error (exit 1):
    - --value-file pointing at a non-existent path -> exit 1, memo untouched.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"
_RESEARCH_HELPER_PY = _LIB_DIR / "research_helper.py"


def _run_research(devforge_dir, *args, input_text=None):
    """Invoke research_helper.py <args> as a subprocess.

    input_text, when given, is piped to stdin (for the --value-file -
    route) -- never a shell argument.
    """
    return subprocess.run(
        [sys.executable, str(_RESEARCH_HELPER_PY), "--devforge-dir", str(devforge_dir)]
        + list(args),
        input=input_text,
        capture_output=True,
        text=True,
    )


def _read_verbatim_prompt(devforge_dir):
    """Real-producer round trip: read-memo subprocess, parse stdout JSON,
    return memo['verbatim_prompt']."""
    r = _run_research(devforge_dir, "read-memo")
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)["verbatim_prompt"]


def _write_body_file(tmp, content, name="body.txt"):
    """Write content to a file with newline="" -- no platform-dependent
    translation on write either, so the fixture on disk carries the exact
    bytes the test intends (mirrors _report_ticket's own CRLF test)."""
    path = Path(tmp) / name
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(content)
    return str(path)


_AWKWARD_BODY = (
    "Pasted ticket text with a `backtick` right here and a $(echo pwned) "
    "sequence, plus a $VAR reference.\r\nSecond line after a CRLF.\r\n"
    "Third line, still awkward."
)


class TestValueFilePath(unittest.TestCase):

    def test_backtick_dollar_paren_crlf_round_trips_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            devforge.mkdir()
            body_file = _write_body_file(tmp, _AWKWARD_BODY)

            r = _run_research(
                devforge, "set-verbatim-prompt", "--value-file", body_file,
            )
            self.assertEqual(r.returncode, 0, r.stderr)

            stored = _read_verbatim_prompt(devforge)
            # _validate_scalar strips only the OUTER ends; the body has no
            # leading/trailing whitespace here, so this is byte-identical
            # to the source, backticks/$(/CRLF all intact.
            self.assertEqual(stored, _AWKWARD_BODY)
            self.assertIn("\r\n", stored)
            self.assertIn("`backtick`", stored)
            self.assertIn("$(echo pwned)", stored)

    def test_leading_trailing_whitespace_including_crlf_is_stripped(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            devforge.mkdir()
            padded = "  \r\n" + _AWKWARD_BODY + "\r\n\r\n  "
            body_file = _write_body_file(tmp, padded)

            r = _run_research(
                devforge, "set-verbatim-prompt", "--value-file", body_file,
            )
            self.assertEqual(r.returncode, 0, r.stderr)

            stored = _read_verbatim_prompt(devforge)
            self.assertEqual(stored, _AWKWARD_BODY)


class TestValueFileStdin(unittest.TestCase):

    def test_stdin_dash_round_trips_byte_identical_to_file_route(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge_file = Path(tmp) / ".devforge-file"
            devforge_file.mkdir()
            devforge_stdin = Path(tmp) / ".devforge-stdin"
            devforge_stdin.mkdir()
            body_file = _write_body_file(tmp, _AWKWARD_BODY)

            r_file = _run_research(
                devforge_file, "set-verbatim-prompt", "--value-file", body_file,
            )
            self.assertEqual(r_file.returncode, 0, r_file.stderr)

            r_stdin = _run_research(
                devforge_stdin, "set-verbatim-prompt", "--value-file", "-",
                input_text=_AWKWARD_BODY,
            )
            self.assertEqual(r_stdin.returncode, 0, r_stdin.stderr)

            stored_file = _read_verbatim_prompt(devforge_file)
            stored_stdin = _read_verbatim_prompt(devforge_stdin)

            self.assertEqual(stored_file, _AWKWARD_BODY)
            self.assertEqual(stored_stdin, _AWKWARD_BODY)
            self.assertEqual(stored_file, stored_stdin)
            self.assertIn("\r\n", stored_stdin)


class TestValueInlineUnchanged(unittest.TestCase):
    """The pre-existing --value route: unaffected by the new option."""

    def test_inline_value_still_works_and_is_stripped(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            devforge.mkdir()
            r = _run_research(
                devforge, "set-verbatim-prompt",
                "--value", "  Order BLoC fetch returns stale rows. Suspected cause: race.  ",
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            stored = _read_verbatim_prompt(devforge)
            self.assertEqual(
                stored,
                "Order BLoC fetch returns stale rows. Suspected cause: race.",
            )

    def test_inline_value_with_internal_whitespace_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            devforge.mkdir()
            value = "Line one.\nLine two.\nLine three."
            r = _run_research(
                devforge, "set-verbatim-prompt", "--value", value,
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(_read_verbatim_prompt(devforge), value)


class TestArgumentShapeErrors(unittest.TestCase):

    def test_both_value_and_value_file_exits_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            devforge.mkdir()
            body_file = _write_body_file(tmp, "some text")
            r = _run_research(
                devforge, "set-verbatim-prompt",
                "--value", "x", "--value-file", body_file,
            )
            self.assertEqual(r.returncode, 2)
            self.assertIn("not allowed with argument --value", r.stderr)
            # Nothing written -- memo stays at its untouched default.
            self.assertIsNone(_read_verbatim_prompt(devforge))

    def test_neither_value_nor_value_file_exits_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            devforge.mkdir()
            r = _run_research(devforge, "set-verbatim-prompt")
            self.assertEqual(r.returncode, 2)
            self.assertIn("required", r.stderr)

    def test_empty_value_file_content_exits_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            devforge.mkdir()
            empty_file = _write_body_file(tmp, "", name="empty.txt")
            r = _run_research(
                devforge, "set-verbatim-prompt", "--value-file", empty_file,
            )
            self.assertEqual(r.returncode, 2)
            self.assertIn("cannot be empty", r.stderr)
            self.assertIsNone(_read_verbatim_prompt(devforge))

    def test_explicit_empty_value_file_string_exits_2(self):
        """--value-file "" (a literal empty string ARGUMENT) is a distinct
        code path from test_empty_value_file_content_exits_2 above (a real
        FILE whose CONTENT is empty). The former is caught by
        cmd_set_verbatim_prompt's own `if not value_file:` guard before any
        file I/O is attempted; the latter reaches _validate_scalar only
        after a real (empty) file is successfully read. Both exit 2 and
        both stderr messages happen to contain the substring "cannot be
        empty", so this test pins the FULL, unambiguous message
        "--value-file cannot be empty" -- not the shared substring -- to
        prove the guard branch fired rather than _validate_scalar's."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            devforge.mkdir()
            r = _run_research(
                devforge, "set-verbatim-prompt", "--value-file", "",
            )
            self.assertEqual(r.returncode, 2)
            self.assertIn("--value-file cannot be empty", r.stderr)
            self.assertIsNone(_read_verbatim_prompt(devforge))

    def test_whitespace_only_value_file_content_exits_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            devforge.mkdir()
            ws_file = _write_body_file(tmp, "   \r\n\r\n   ", name="ws.txt")
            r = _run_research(
                devforge, "set-verbatim-prompt", "--value-file", ws_file,
            )
            self.assertEqual(r.returncode, 2)
            self.assertIsNone(_read_verbatim_prompt(devforge))


class TestValueFileIOError(unittest.TestCase):

    def test_nonexistent_value_file_exits_1(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            devforge.mkdir()
            missing = str(Path(tmp) / "does-not-exist.txt")
            r = _run_research(
                devforge, "set-verbatim-prompt", "--value-file", missing,
            )
            self.assertEqual(r.returncode, 1)
            self.assertIn("--value-file", r.stderr)
            self.assertIsNone(_read_verbatim_prompt(devforge))


if __name__ == "__main__":
    unittest.main()
