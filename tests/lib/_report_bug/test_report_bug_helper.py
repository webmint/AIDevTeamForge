"""Tests for src/devforge/lib/_report_bug/ — the report_bug_helper subpackage.

Real-producer round-trip discipline (mandatory per repo rules):
  - write-bug tests round-trip through the REAL shared writer file_bugs()
    (src/devforge/lib/_shared/bug_file.py), asserting on actual on-disk output.
  - preflight tests use real filesystem layouts or stub project-config.json
    files (no monkey-patching of resolve_workspace internals).
  - No hand-authored markdown fixtures for format assertions — every format
    assertion reads files written by file_bugs() via the CLI path.

Coverage:
  cmd_preflight:
    - Standalone workspace (no project-config.json) → is_wrapper=False,
      bugs_dir ends with /bugs, root is an absolute path, exit 0.
    - Wrapper workspace (PROJECT_ROOT set in project-config.json) →
      is_wrapper=True, bugs_dir under install_root, exit 0.
    - Default workspace_root "." resolves without error.
    - JSON shape: exactly the keys bugs_dir, is_wrapper, root.

  cmd_write_bug:
    - Happy path: file written to bugs/001-<slug>.md, exit 0.
    - Written file contains **Source**: manual.
    - Written file contains **Status**: Open.
    - Written file contains **Feature**: N/A.
    - Default severity is Warning (omitting --severity).
    - Explicit --severity Critical persists to file.
    - Explicit --severity Info persists to file.
    - --title provided → file title uses --title, not description.
    - --title omitted → file title defaults to --description value.
    - --file provided (path exists) → file table row appears in output.
    - --file provided (path absent) → warning on stderr, bug still written.
    - --file omitted → file table shows (unknown) placeholder row.
    - Stdout is a JSON array of the written path(s).
    - Written path name starts with 001- when bugs_dir is empty.
    - Numbering continues from existing bugs (e.g. 003-* exists → new is 004-*).

  Argument error paths (exit 2):
    - Missing --date → exit 2, message on stderr.
    - Missing --bugs-dir → exit 2, message on stderr.
    - Missing --description → exit 2, message on stderr.
    - Invalid --severity (e.g. "High") → exit 2, message on stderr.

  CLI dispatch (via main()):
    - No subcommand → exit 2 (prints help to stderr).
    - Unknown verb → exit 2.
    - preflight with --workspace-root → exit 0, JSON on stdout.
    - write-bug happy path → exit 0, JSON array on stdout.
    - write-bug missing --date → exit 2.
    - write-bug bad --severity → exit 2, "Critical|Warning|Info" in stderr.
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
from _report_bug._cli import (  # noqa: E402
    main,
    cmd_preflight,
    cmd_write_bug,
    _VALID_SEVERITIES,
)

# Real producer used for round-trip verification.
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


def _make_bugs_dir(tmp):
    # type: (str) -> str
    """Return an empty bugs/ subdirectory within tmp."""
    bugs_dir = os.path.join(tmp, "bugs")
    os.makedirs(bugs_dir, exist_ok=True)
    return bugs_dir


def _minimal_write_bug_argv(bugs_dir, description="Login fails silently"):
    # type: (str, str) -> list
    """Return a minimal valid write-bug argv."""
    return [
        "write-bug",
        "--bugs-dir", bugs_dir,
        "--date", "2026-06-19",
        "--description", description,
    ]


def _read_first_bug(bugs_dir):
    # type: (str) -> str
    """Read the content of the first *.md file in bugs_dir (sorted)."""
    files = sorted(f for f in os.listdir(bugs_dir) if f.endswith(".md"))
    assert files, "no .md files in bugs_dir: {0}".format(bugs_dir)
    with open(os.path.join(bugs_dir, files[0]), "r", encoding="utf-8") as fh:
        return fh.read()


# ---------------------------------------------------------------------------
# Tests: preflight verb
# ---------------------------------------------------------------------------


class TestPreflight(unittest.TestCase):

    def test_standalone_workspace_is_wrapper_false(self):
        """Workspace with no project-config.json → is_wrapper=False."""
        with tempfile.TemporaryDirectory() as tmp:
            code, out, _ = _run_main(["preflight", "--workspace-root", tmp])
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertFalse(data["is_wrapper"])

    def test_standalone_bugs_dir_ends_with_bugs(self):
        """Standalone workspace → bugs_dir ends with /bugs."""
        with tempfile.TemporaryDirectory() as tmp:
            code, out, _ = _run_main(["preflight", "--workspace-root", tmp])
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertTrue(data["bugs_dir"].endswith("bugs"))

    def test_standalone_root_is_absolute(self):
        """Root in preflight output is an absolute path."""
        with tempfile.TemporaryDirectory() as tmp:
            code, out, _ = _run_main(["preflight", "--workspace-root", tmp])
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertTrue(os.path.isabs(data["root"]))

    def test_json_shape_has_exactly_required_keys(self):
        """JSON output has bugs_dir, is_wrapper, root — no extra keys."""
        with tempfile.TemporaryDirectory() as tmp:
            code, out, _ = _run_main(["preflight", "--workspace-root", tmp])
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(sorted(data.keys()), ["bugs_dir", "is_wrapper", "root"])

    def test_exit_code_is_zero(self):
        """preflight always exits 0 (fail-soft workspace resolution)."""
        with tempfile.TemporaryDirectory() as tmp:
            code, _, _ = _run_main(["preflight", "--workspace-root", tmp])
        self.assertEqual(code, 0)

    def test_wrapper_workspace_is_wrapper_true(self):
        """Workspace with non-trivial PROJECT_ROOT → is_wrapper=True."""
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

    def test_wrapper_bugs_dir_is_under_install_root(self):
        """Wrapper mode: bugs_dir lives under the install_root, not source_root."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge_dir = os.path.join(tmp, ".devforge")
            os.makedirs(devforge_dir)
            config = {"PROJECT_ROOT": "src/product-app"}
            with open(os.path.join(devforge_dir, "project-config.json"), "w", encoding="utf-8") as fh:
                json.dump(config, fh)
            code, out, _ = _run_main(["preflight", "--workspace-root", tmp])
        self.assertEqual(code, 0)
        data = json.loads(out)
        # bugs_dir must be under the install root (tmp), not the sub-dir
        self.assertTrue(data["bugs_dir"].startswith(str(Path(tmp).resolve())))
        self.assertNotIn("product-app", data["bugs_dir"])

    def test_default_workspace_root_resolves(self):
        """preflight with default --workspace-root '.' does not crash."""
        code, out, _ = _run_main(["preflight"])
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertIn("bugs_dir", data)


# ---------------------------------------------------------------------------
# Tests: write-bug verb — happy path
# ---------------------------------------------------------------------------


class TestWriteBugHappyPath(unittest.TestCase):

    def test_exit_code_zero_on_success(self):
        """write-bug with all required args → exit 0."""
        with tempfile.TemporaryDirectory() as tmp:
            bugs_dir = _make_bugs_dir(tmp)
            argv = _minimal_write_bug_argv(bugs_dir)
            code, _, _ = _run_main(argv)
        self.assertEqual(code, 0)

    def test_stdout_is_json_array_of_written_paths(self):
        """Stdout is a JSON array containing the written path."""
        with tempfile.TemporaryDirectory() as tmp:
            bugs_dir = _make_bugs_dir(tmp)
            argv = _minimal_write_bug_argv(bugs_dir)
            code, out, _ = _run_main(argv)
        self.assertEqual(code, 0)
        paths = json.loads(out)
        self.assertIsInstance(paths, list)
        self.assertEqual(len(paths), 1)

    def test_written_file_exists_on_disk(self):
        """The path reported in stdout actually exists on disk."""
        with tempfile.TemporaryDirectory() as tmp:
            bugs_dir = _make_bugs_dir(tmp)
            argv = _minimal_write_bug_argv(bugs_dir)
            _, out, _ = _run_main(argv)
            paths = json.loads(out)
            self.assertTrue(os.path.isfile(paths[0]))

    def test_file_name_starts_with_001(self):
        """First bug in an empty bugs/ dir gets 001- prefix."""
        with tempfile.TemporaryDirectory() as tmp:
            bugs_dir = _make_bugs_dir(tmp)
            argv = _minimal_write_bug_argv(bugs_dir)
            _, out, _ = _run_main(argv)
            paths = json.loads(out)
            self.assertTrue(os.path.basename(paths[0]).startswith("001-"))

    def test_source_field_is_manual(self):
        """Written file contains **Source**: manual."""
        with tempfile.TemporaryDirectory() as tmp:
            bugs_dir = _make_bugs_dir(tmp)
            argv = _minimal_write_bug_argv(bugs_dir)
            _run_main(argv)
            content = _read_first_bug(bugs_dir)
        self.assertIn("**Source**: manual", content)

    def test_status_field_is_open(self):
        """Written file contains **Status**: Open."""
        with tempfile.TemporaryDirectory() as tmp:
            bugs_dir = _make_bugs_dir(tmp)
            argv = _minimal_write_bug_argv(bugs_dir)
            _run_main(argv)
            content = _read_first_bug(bugs_dir)
        self.assertIn("**Status**: Open", content)

    def test_feature_field_is_na(self):
        """Written file contains **Feature**: N/A."""
        with tempfile.TemporaryDirectory() as tmp:
            bugs_dir = _make_bugs_dir(tmp)
            argv = _minimal_write_bug_argv(bugs_dir)
            _run_main(argv)
            content = _read_first_bug(bugs_dir)
        self.assertIn("**Feature**: N/A", content)

    def test_default_severity_is_warning(self):
        """Omitting --severity → severity Warning in file."""
        with tempfile.TemporaryDirectory() as tmp:
            bugs_dir = _make_bugs_dir(tmp)
            argv = _minimal_write_bug_argv(bugs_dir)
            _run_main(argv)
            content = _read_first_bug(bugs_dir)
        self.assertIn("**Severity**: Warning", content)

    def test_explicit_severity_critical(self):
        """--severity Critical persists to file."""
        with tempfile.TemporaryDirectory() as tmp:
            bugs_dir = _make_bugs_dir(tmp)
            argv = _minimal_write_bug_argv(bugs_dir) + ["--severity", "Critical"]
            _run_main(argv)
            content = _read_first_bug(bugs_dir)
        self.assertIn("**Severity**: Critical", content)

    def test_explicit_severity_info(self):
        """--severity Info persists to file."""
        with tempfile.TemporaryDirectory() as tmp:
            bugs_dir = _make_bugs_dir(tmp)
            argv = _minimal_write_bug_argv(bugs_dir) + ["--severity", "Info"]
            _run_main(argv)
            content = _read_first_bug(bugs_dir)
        self.assertIn("**Severity**: Info", content)

    def test_title_provided_appears_in_file(self):
        """--title provided → file heading uses --title."""
        with tempfile.TemporaryDirectory() as tmp:
            bugs_dir = _make_bugs_dir(tmp)
            argv = _minimal_write_bug_argv(bugs_dir) + ["--title", "Short Title"]
            _run_main(argv)
            content = _read_first_bug(bugs_dir)
        self.assertIn("Short Title", content)

    def test_title_omitted_defaults_to_description(self):
        """--title omitted → file heading uses --description text."""
        with tempfile.TemporaryDirectory() as tmp:
            bugs_dir = _make_bugs_dir(tmp)
            description = "Login fails silently on bad password"
            argv = ["write-bug", "--bugs-dir", bugs_dir, "--date", "2026-06-19",
                    "--description", description]
            _run_main(argv)
            content = _read_first_bug(bugs_dir)
        # The description text should appear in the heading or as the title
        self.assertIn("Login fails silently on bad password", content)

    def test_title_drives_filename_slug(self):
        """When --title and --description differ, the filename slug comes from --title."""
        with tempfile.TemporaryDirectory() as tmp:
            bugs_dir = _make_bugs_dir(tmp)
            argv = _minimal_write_bug_argv(
                bugs_dir,
                description="A much longer description that should not be in the filename",
            ) + ["--title", "Auth crash"]
            _run_main(argv)
            files = sorted(f for f in os.listdir(bugs_dir) if f.endswith(".md"))
        self.assertTrue(files, "no bug file written")
        name = files[0]
        # Pin the full filename: 001 (empty bugs/ → first), slug from --title ONLY
        # (not --description). Exclusivity is the contract being pinned.
        self.assertEqual(name, "001-auth-crash.md")

    def test_evidence_field_is_reported_by_user(self):
        """Written file contains 'Reported by user.' in Evidence section."""
        with tempfile.TemporaryDirectory() as tmp:
            bugs_dir = _make_bugs_dir(tmp)
            argv = _minimal_write_bug_argv(bugs_dir)
            _run_main(argv)
            content = _read_first_bug(bugs_dir)
        self.assertIn("Reported by user.", content)

    def test_ac_ref_is_na(self):
        """Written file contains **AC**: N/A."""
        with tempfile.TemporaryDirectory() as tmp:
            bugs_dir = _make_bugs_dir(tmp)
            argv = _minimal_write_bug_argv(bugs_dir)
            _run_main(argv)
            content = _read_first_bug(bugs_dir)
        self.assertIn("**AC**: N/A", content)


# ---------------------------------------------------------------------------
# Tests: write-bug — --file argument
# ---------------------------------------------------------------------------


class TestWriteBugFileArg(unittest.TestCase):

    def test_file_exists_appears_in_file_table(self):
        """--file with an existing path → that path appears in the File(s) table."""
        with tempfile.TemporaryDirectory() as tmp:
            bugs_dir = _make_bugs_dir(tmp)
            # Create a real file to reference
            real_file = os.path.join(tmp, "src", "auth.py")
            os.makedirs(os.path.dirname(real_file), exist_ok=True)
            with open(real_file, "w") as fh:
                fh.write("# auth\n")
            argv = _minimal_write_bug_argv(bugs_dir) + ["--file", real_file]
            code, _, _ = _run_main(argv)
            content = _read_first_bug(bugs_dir)
        self.assertEqual(code, 0)
        self.assertIn(real_file, content)

    def test_file_absent_emits_warning_but_exits_zero(self):
        """--file with a non-existent path → warning on stderr, exit 0."""
        with tempfile.TemporaryDirectory() as tmp:
            bugs_dir = _make_bugs_dir(tmp)
            missing = os.path.join(tmp, "nonexistent.py")
            argv = _minimal_write_bug_argv(bugs_dir) + ["--file", missing]
            code, _, err = _run_main(argv)
        self.assertEqual(code, 0)
        self.assertIn("warning", err.lower())
        self.assertIn("nonexistent.py", err)

    def test_file_absent_bug_still_written(self):
        """Even when --file path is absent, the bug file is created."""
        with tempfile.TemporaryDirectory() as tmp:
            bugs_dir = _make_bugs_dir(tmp)
            missing = os.path.join(tmp, "nonexistent.py")
            argv = _minimal_write_bug_argv(bugs_dir) + ["--file", missing]
            _, out, _ = _run_main(argv)
            paths = json.loads(out)
            self.assertEqual(len(paths), 1)
            self.assertTrue(os.path.isfile(paths[0]))

    def test_file_omitted_placeholder_row_in_table(self):
        """--file omitted → (unknown) placeholder row appears in File(s) table."""
        with tempfile.TemporaryDirectory() as tmp:
            bugs_dir = _make_bugs_dir(tmp)
            argv = _minimal_write_bug_argv(bugs_dir)
            _run_main(argv)
            content = _read_first_bug(bugs_dir)
        self.assertIn("(unknown)", content)


# ---------------------------------------------------------------------------
# Tests: write-bug — numbering continuity
# ---------------------------------------------------------------------------


class TestWriteBugNumbering(unittest.TestCase):

    def test_numbering_continues_from_existing(self):
        """If 003-*.md exists, next bug gets 004- prefix."""
        with tempfile.TemporaryDirectory() as tmp:
            bugs_dir = _make_bugs_dir(tmp)
            # Plant a dummy file with 003- prefix
            with open(os.path.join(bugs_dir, "003-existing.md"), "w") as fh:
                fh.write("# Bug 003: existing\n")
            argv = _minimal_write_bug_argv(bugs_dir)
            _, out, _ = _run_main(argv)
            paths = json.loads(out)
        self.assertTrue(os.path.basename(paths[0]).startswith("004-"))

    def test_empty_bugs_dir_starts_at_001(self):
        """An empty bugs/ dir → first written file gets 001- prefix."""
        with tempfile.TemporaryDirectory() as tmp:
            bugs_dir = _make_bugs_dir(tmp)
            argv = _minimal_write_bug_argv(bugs_dir)
            _, out, _ = _run_main(argv)
            paths = json.loads(out)
        self.assertTrue(os.path.basename(paths[0]).startswith("001-"))


# ---------------------------------------------------------------------------
# Tests: argument error paths — exit 2
# ---------------------------------------------------------------------------


class TestWriteBugArgErrors(unittest.TestCase):

    def test_missing_date_exits_2(self):
        """Missing --date → exit 2."""
        with tempfile.TemporaryDirectory() as tmp:
            bugs_dir = _make_bugs_dir(tmp)
            argv = ["write-bug", "--bugs-dir", bugs_dir, "--description", "Some bug"]
            code, _, err = _run_main(argv)
        self.assertEqual(code, 2)
        self.assertIn("--date", err)

    def test_missing_bugs_dir_exits_2(self):
        """Missing --bugs-dir → exit 2 (argparse required arg)."""
        argv = ["write-bug", "--date", "2026-06-19", "--description", "Some bug"]
        code, _, _ = _run_main(argv)
        self.assertEqual(code, 2)

    def test_missing_description_exits_2(self):
        """Missing --description → exit 2 (argparse required arg)."""
        with tempfile.TemporaryDirectory() as tmp:
            bugs_dir = _make_bugs_dir(tmp)
            argv = ["write-bug", "--bugs-dir", bugs_dir, "--date", "2026-06-19"]
            code, _, _ = _run_main(argv)
        self.assertEqual(code, 2)

    def test_invalid_severity_exits_2(self):
        """--severity with a value not in Critical|Warning|Info → exit 2."""
        with tempfile.TemporaryDirectory() as tmp:
            bugs_dir = _make_bugs_dir(tmp)
            argv = _minimal_write_bug_argv(bugs_dir) + ["--severity", "High"]
            code, _, err = _run_main(argv)
        # argparse choices enforcement returns exit 2
        self.assertEqual(code, 2)

    def test_invalid_severity_medium_exits_2(self):
        """--severity Medium (findings vocabulary, not storage-rules) → exit 2."""
        with tempfile.TemporaryDirectory() as tmp:
            bugs_dir = _make_bugs_dir(tmp)
            argv = _minimal_write_bug_argv(bugs_dir) + ["--severity", "Medium"]
            code, _, _ = _run_main(argv)
        self.assertEqual(code, 2)

    # -----------------------------------------------------------------------
    # Direct-call tests — second-layer defences (Finding 3 + Finding 1)
    # These call cmd_write_bug() with a hand-built Namespace, bypassing
    # argparse. They document that the guards inside cmd_write_bug ARE
    # intentional second-layer defences, not dead code, and verify they
    # fire independently of argparse.
    # -----------------------------------------------------------------------

    def test_direct_call_missing_bugs_dir_exits_2(self):
        """Direct call with bugs_dir=None → guard fires, exit 2."""
        import argparse as _ap
        import io as _io
        ns = _ap.Namespace(bugs_dir=None, date="2026-06-19",
                           description="x", title=None,
                           severity="Warning", file=None)
        old_stderr = sys.stderr
        sys.stderr = _io.StringIO()
        try:
            code = cmd_write_bug(ns)
        finally:
            captured = sys.stderr.getvalue()
            sys.stderr = old_stderr
        self.assertEqual(code, 2)
        self.assertIn("--bugs-dir", captured)

    def test_direct_call_missing_date_exits_2(self):
        """Direct call with date=None → guard fires, exit 2."""
        import argparse as _ap
        import io as _io
        with tempfile.TemporaryDirectory() as tmp:
            bugs_dir = _make_bugs_dir(tmp)
            ns = _ap.Namespace(bugs_dir=bugs_dir, date=None,
                               description="x", title=None,
                               severity="Warning", file=None)
            old_stderr = sys.stderr
            sys.stderr = _io.StringIO()
            try:
                code = cmd_write_bug(ns)
            finally:
                captured = sys.stderr.getvalue()
                sys.stderr = old_stderr
        self.assertEqual(code, 2)
        self.assertIn("--date", captured)

    def test_direct_call_missing_description_exits_2(self):
        """Direct call with description=None → guard fires, exit 2."""
        import argparse as _ap
        import io as _io
        with tempfile.TemporaryDirectory() as tmp:
            bugs_dir = _make_bugs_dir(tmp)
            ns = _ap.Namespace(bugs_dir=bugs_dir, date="2026-06-19",
                               description=None, title=None,
                               severity="Warning", file=None)
            old_stderr = sys.stderr
            sys.stderr = _io.StringIO()
            try:
                code = cmd_write_bug(ns)
            finally:
                captured = sys.stderr.getvalue()
                sys.stderr = old_stderr
        self.assertEqual(code, 2)
        self.assertIn("--description", captured)

    def test_direct_call_invalid_severity_exits_2(self):
        """Direct call with severity='High' → manual guard fires, exit 2.

        Finding 1: the manual check (lines 104-109 of _cli.py) is only
        reachable via direct-call, not via main() (argparse choices= fires
        first). This test documents and covers that intentional second-layer
        defence.
        """
        import argparse as _ap
        import io as _io
        with tempfile.TemporaryDirectory() as tmp:
            bugs_dir = _make_bugs_dir(tmp)
            ns = _ap.Namespace(bugs_dir=bugs_dir, date="2026-06-19",
                               description="x", title=None,
                               severity="High", file=None)
            old_stderr = sys.stderr
            sys.stderr = _io.StringIO()
            try:
                code = cmd_write_bug(ns)
            finally:
                captured = sys.stderr.getvalue()
                sys.stderr = old_stderr
        self.assertEqual(code, 2)
        # The manual guard should mention the valid severities
        self.assertTrue(
            any(v in captured for v in ("Critical", "Warning", "Info")),
            "stderr should name valid severities; got: {0!r}".format(captured),
        )


# ---------------------------------------------------------------------------
# Tests: CLI dispatch
# ---------------------------------------------------------------------------


class TestCLIDispatch(unittest.TestCase):

    def test_no_subcommand_exits_2(self):
        """No subcommand → exit 2."""
        code, _, _ = _run_main([])
        self.assertEqual(code, 2)

    def test_unknown_verb_exits_2(self):
        """Unknown verb → exit 2."""
        code, _, _ = _run_main(["unknown-verb"])
        self.assertEqual(code, 2)

    def test_preflight_emits_valid_json(self):
        """preflight emits parseable JSON to stdout."""
        with tempfile.TemporaryDirectory() as tmp:
            code, out, _ = _run_main(["preflight", "--workspace-root", tmp])
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertIsInstance(data, dict)

    def test_write_bug_happy_path_via_main(self):
        """write-bug via main() dispatches correctly → exit 0, JSON stdout."""
        with tempfile.TemporaryDirectory() as tmp:
            bugs_dir = _make_bugs_dir(tmp)
            argv = _minimal_write_bug_argv(bugs_dir)
            code, out, _ = _run_main(argv)
        self.assertEqual(code, 0)
        paths = json.loads(out)
        self.assertIsInstance(paths, list)
        self.assertEqual(len(paths), 1)

    def test_write_bug_missing_date_via_main(self):
        """write-bug missing --date via main() → exit 2."""
        with tempfile.TemporaryDirectory() as tmp:
            bugs_dir = _make_bugs_dir(tmp)
            argv = ["write-bug", "--bugs-dir", bugs_dir, "--description", "x"]
            code, _, err = _run_main(argv)
        self.assertEqual(code, 2)
        self.assertIn("--date", err)

    def test_write_bug_bad_severity_message_mentions_valid_values(self):
        """Bad --severity: stderr should mention valid choices."""
        with tempfile.TemporaryDirectory() as tmp:
            bugs_dir = _make_bugs_dir(tmp)
            argv = _minimal_write_bug_argv(bugs_dir) + ["--severity", "High"]
            code, _, err = _run_main(argv)
        self.assertEqual(code, 2)
        # argparse itself mentions "invalid choice" or "choices"
        self.assertTrue(
            any(v in err for v in ("Critical", "Warning", "Info", "invalid choice", "choices")),
            "stderr should mention valid severities; got: {0!r}".format(err),
        )


# ---------------------------------------------------------------------------
# Tests: round-trip through real shared writer
# ---------------------------------------------------------------------------


class TestRoundTripRealWriter(unittest.TestCase):
    """Round-trip: call write-bug CLI → assert file_bugs() output shape is correct."""

    def test_round_trip_file_has_correct_heading(self):
        """file_bugs() heading format: '# Bug 001: <title>'."""
        with tempfile.TemporaryDirectory() as tmp:
            bugs_dir = _make_bugs_dir(tmp)
            argv = _minimal_write_bug_argv(bugs_dir) + ["--title", "Null pointer crash"]
            _run_main(argv)
            content = _read_first_bug(bugs_dir)
        self.assertTrue(
            content.startswith("# Bug 001:"),
            "Expected heading '# Bug 001:...', got: {0!r}".format(content[:80]),
        )
        self.assertIn("Null pointer crash", content)

    def test_round_trip_all_required_sections_present(self):
        """All storage-rules sections appear in the round-trip output."""
        with tempfile.TemporaryDirectory() as tmp:
            bugs_dir = _make_bugs_dir(tmp)
            argv = _minimal_write_bug_argv(bugs_dir)
            _run_main(argv)
            content = _read_first_bug(bugs_dir)
        for section in (
            "## Description",
            "## Expected Behavior",
            "## Actual Behavior",
            "## File(s)",
            "## Evidence",
            "## Related Issues",
            "## Fix Notes",
        ):
            self.assertIn(section, content, "Missing section: {0}".format(section))

    def test_round_trip_date_appears_in_reported_field(self):
        """The --date argument appears in **Reported**: field."""
        with tempfile.TemporaryDirectory() as tmp:
            bugs_dir = _make_bugs_dir(tmp)
            argv = ["write-bug", "--bugs-dir", bugs_dir, "--date", "2026-06-19",
                    "--description", "Something broke"]
            _run_main(argv)
            content = _read_first_bug(bugs_dir)
        self.assertIn("**Reported**: 2026-06-19", content)

    def test_round_trip_no_tmp_files_left(self):
        """Atomic write: no .tmp-bug- files remain in bugs_dir after success."""
        with tempfile.TemporaryDirectory() as tmp:
            bugs_dir = _make_bugs_dir(tmp)
            argv = _minimal_write_bug_argv(bugs_dir)
            _run_main(argv)
            leftover = [f for f in os.listdir(bugs_dir) if ".tmp-bug-" in f]
        self.assertEqual(leftover, [], "Leftover tmp files: {0}".format(leftover))

    def test_round_trip_description_appears_in_description_section(self):
        """--description text appears in the ## Description section."""
        with tempfile.TemporaryDirectory() as tmp:
            bugs_dir = _make_bugs_dir(tmp)
            description = "Server returns 500 on empty payload"
            argv = ["write-bug", "--bugs-dir", bugs_dir, "--date", "2026-06-19",
                    "--description", description]
            _run_main(argv)
            content = _read_first_bug(bugs_dir)
        self.assertIn(description, content)


# ---------------------------------------------------------------------------
# Tests: valid severities constant
# ---------------------------------------------------------------------------


class TestValidSeverities(unittest.TestCase):

    def test_valid_severities_are_exactly_critical_warning_info(self):
        """_VALID_SEVERITIES matches storage-rules.md vocabulary."""
        self.assertEqual(set(_VALID_SEVERITIES), {"Critical", "Warning", "Info"})


if __name__ == "__main__":
    unittest.main()
