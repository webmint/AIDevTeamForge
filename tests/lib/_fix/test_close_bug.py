"""Tests for the close-bug CLI verb on _fix/_cli.py (plan 88 D4).

Mirrors tests/lib/_fix/test_seed.py's structure: the write-seed CLI verb's
test file, which itself exercises its verb end-to-end via main(argv) with
captured stdout/stderr, rather than calling cmd_close_bug directly with a
hand-built _Args stand-in. The underlying function (close_bug) lives in
_shared/bug_file.py and has its own direct-call unit tests in
tests/lib/_shared/test_bug_file.py -- this file covers the CLI surface only:
registration, argparse wiring, argument-error exits, and the stdout JSON
ack shape.

Round-trip discipline: every test builds its bug file via the REAL producer
(_shared.bug_file.file_bugs -- the same writer /devforge:report-bug and
/devforge:verify use), never a hand-authored fixture.

Coverage:

CLI (close-bug verb, via main(argv)):
  - close-bug registered in _SUBCOMMAND_REGISTRY
  - top-level --help lists close-bug
  - close-bug --help exits 0
  - missing --bug-file / --date / --fix-notes (argparse-level, flag absent)
    -> exit 2
  - empty --bug-file / --date / --fix-notes (argparse-level present, value
    empty; the handler's own not-empty check) -> exit 2
  - happy path -> exit 0, {"closed": true, "bug_file": ...} JSON ack, the
    real bug file's three fields flipped
  - nonexistent --bug-file -> exit 2, stderr names the path
  - already-Fixed bug file -> exit 2 (second close-bug run), file unchanged
    from the first successful close
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

from _fix._cli import _SUBCOMMAND_REGISTRY, main  # noqa: E402
from _shared.bug_file import file_bugs  # noqa: E402


# ---------------------------------------------------------------------------
# Shared test helpers
# ---------------------------------------------------------------------------


def _capture(argv):
    # type: (list) -> tuple
    """Run main(argv) with captured stdout/stderr. Returns (stdout, stderr, rc).

    Catches SystemExit (raised by argparse on bad args / --help) and converts
    the exit code to an integer. Mirrors test_seed.py's _capture.
    """
    buf_out = io.StringIO()
    buf_err = io.StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    try:
        sys.stdout, sys.stderr = buf_out, buf_err
        try:
            rc = main(argv)
        except SystemExit as exc:
            rc = exc.code if isinstance(exc.code, int) else 2
    finally:
        sys.stdout, sys.stderr = old_out, old_err
    return buf_out.getvalue(), buf_err.getvalue(), rc


def _file_one_bug(bugs_dir):
    """Write one real Open bug file via file_bugs; return its path."""
    paths = file_bugs(
        bugs_dir=bugs_dir,
        issues=[{
            "title": "Null cart total",
            "severity": "Critical",
            "description": "The cart total is null when no items.",
            "expected": "Cart total should be 0 when empty.",
            "actual": "Cart total is null, causing downstream TypeError.",
            "files": [{"path": "src/cart.py", "detail": "total calculation"}],
            "evidence": "verify-report shows AC-3 FAIL",
            "ac_ref": "AC-3",
        }],
        feature_spec_path="specs/001-cart/spec.md",
        date="2026-06-16",
    )
    return paths[0]


def _valid_cli_argv(bug_file, **overrides):
    args = {
        "--bug-file": bug_file,
        "--date": "2026-08-26",
        "--fix-notes": "Root cause: null guard added; commit abc1234.",
    }
    args.update(overrides)
    argv = ["close-bug"]
    for flag, value in args.items():
        if value is None:
            continue
        argv.extend([flag, value])
    return argv


# ---------------------------------------------------------------------------
# CLI: close-bug verb (via main(argv))
# ---------------------------------------------------------------------------


class TestCloseBugCli(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.bugs_dir = os.path.join(self.tmp, "bugs")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_close_bug_registered_in_subcommand_registry(self):
        names = [verb for verb, _, _ in _SUBCOMMAND_REGISTRY]
        self.assertIn("close-bug", names)

    def test_top_level_help_lists_close_bug(self):
        out, err, rc = _capture(["--help"])
        self.assertEqual(rc, 0)
        self.assertIn("close-bug", out)

    def test_close_bug_help_exits_zero(self):
        out, err, rc = _capture(["close-bug", "--help"])
        self.assertEqual(rc, 0)

    def test_missing_bug_file_flag_exits_2(self):
        # argparse-level: --bug-file is required=True.
        argv = ["close-bug", "--date", "2026-08-26", "--fix-notes", "notes"]
        out, err, rc = _capture(argv)
        self.assertEqual(rc, 2)

    def test_missing_date_flag_exits_2(self):
        bug_path = _file_one_bug(self.bugs_dir)
        argv = ["close-bug", "--bug-file", bug_path, "--fix-notes", "notes"]
        out, err, rc = _capture(argv)
        self.assertEqual(rc, 2)

    def test_missing_fix_notes_flag_exits_2(self):
        bug_path = _file_one_bug(self.bugs_dir)
        argv = ["close-bug", "--bug-file", bug_path, "--date", "2026-08-26"]
        out, err, rc = _capture(argv)
        self.assertEqual(rc, 2)

    def test_empty_bug_file_value_exits_2(self):
        """--bug-file "" (flag present, value empty) is rejected by the
        handler's own not-empty check, not merely argparse presence."""
        argv = _valid_cli_argv("placeholder", **{"--bug-file": ""})
        out, err, rc = _capture(argv)
        self.assertEqual(rc, 2)
        self.assertIn("--bug-file", err)

    def test_empty_date_value_exits_2(self):
        bug_path = _file_one_bug(self.bugs_dir)
        argv = _valid_cli_argv(bug_path, **{"--date": ""})
        out, err, rc = _capture(argv)
        self.assertEqual(rc, 2)
        self.assertIn("--date", err)
        with open(bug_path, encoding="utf-8") as fh:
            self.assertIn("**Status**: Open", fh.read())

    def test_empty_fix_notes_value_exits_2(self):
        bug_path = _file_one_bug(self.bugs_dir)
        argv = _valid_cli_argv(bug_path, **{"--fix-notes": ""})
        out, err, rc = _capture(argv)
        self.assertEqual(rc, 2)
        self.assertIn("--fix-notes", err)
        with open(bug_path, encoding="utf-8") as fh:
            self.assertIn("**Status**: Open", fh.read())

    def test_happy_path_closes_real_bug_file(self):
        bug_path = _file_one_bug(self.bugs_dir)
        argv = _valid_cli_argv(bug_path)
        out, err, rc = _capture(argv)
        self.assertEqual(rc, 0, msg=err)

        ack = json.loads(out)
        self.assertEqual(ack, {"closed": True, "bug_file": bug_path})

        with open(bug_path, encoding="utf-8") as fh:
            content = fh.read()
        self.assertIn("**Status**: Fixed", content)
        self.assertIn("**Fixed**: 2026-08-26", content)
        self.assertIn("Root cause: null guard added; commit abc1234.", content)
        self.assertNotIn("_Filled in after resolution._", content)

    def test_nonexistent_bug_file_exits_2(self):
        missing = os.path.join(self.bugs_dir, "999-does-not-exist.md")
        argv = _valid_cli_argv(missing)
        out, err, rc = _capture(argv)
        self.assertEqual(rc, 2)
        self.assertIn(missing, err)

    def test_already_fixed_second_close_exits_2_and_writes_nothing(self):
        """MANDATORY case (Phase 1 verify): close-bug on a file already
        Fixed exits non-zero and writes nothing -- verified by reading the
        file back."""
        bug_path = _file_one_bug(self.bugs_dir)
        argv1 = _valid_cli_argv(bug_path)
        out1, err1, rc1 = _capture(argv1)
        self.assertEqual(rc1, 0, msg=err1)

        with open(bug_path, encoding="utf-8") as fh:
            after_first_close = fh.read()

        argv2 = _valid_cli_argv(
            bug_path, **{
                "--date": "2026-08-27",
                "--fix-notes": "Second closure attempt.",
            }
        )
        out2, err2, rc2 = _capture(argv2)
        self.assertNotEqual(rc2, 0)

        with open(bug_path, encoding="utf-8") as fh:
            after_second_attempt = fh.read()
        self.assertEqual(
            after_first_close, after_second_attempt,
            "A rejected close-bug run must write NOTHING",
        )


if __name__ == "__main__":
    unittest.main()
