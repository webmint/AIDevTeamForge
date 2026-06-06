"""Tests for src/devforge/lib/_implement/_cmds_review_loop.py.

Coverage:

  parse_verdict (unit):
    - APPROVE token → clean=true, verdict='APPROVE'
    - 'APPROVE (with warnings)' → clean=true (APPROVE is still the signal)
    - REQUEST CHANGES → clean=false, verdict='REQUEST CHANGES'
    - BLOCK → clean=false, verdict='BLOCK'
    - Missing verdict line → parse error (returns None, error_msg)
    - Unfilled template (all three tokens slash-separated) → parse error
    - 2-token slash mix 'APPROVE / REQUEST CHANGES' → parse error
    - 2-token slash mix 'BLOCK / APPROVE' → parse error
    - 'APPROVE (with warnings)' — no slash between known tokens → still clean APPROVE
    - Case-insensitive heading match (### verdict: APPROVE) → parses ok
    - Trailing punctuation after token (APPROVE.) → parses as APPROVE
    - Verdict line buried in prose → still found
    - Empty markdown → parse error

  cmd_review_loop_step (integration via function call):
    - APPROVE, iteration=0 → {clean:true, escalate:false, iteration:0, verdict:'APPROVE'}
    - REQUEST CHANGES, iteration=0 → {clean:false, escalate:false, ...}
    - BLOCK, iteration=0 → {clean:false, escalate:false, ...}
    - APPROVE, iteration=2 → escalate=false (below cap of 3)
    - APPROVE, iteration=3 → escalate=true (at cap)
    - APPROVE, iteration=4 → escalate=true (above cap)
    - iteration=-1 → exit 2, empty stdout (negative iteration rejected)
    - Missing verdict → exit 2, no stdout JSON
    - Unfilled template → exit 2, no stdout JSON
    - --verdict-file reads from a real temp file
    - stdin path (no --verdict-file) → reads from stdin mock

  CLI wiring:
    - 'review-loop-step --help' exits 0 (verifies verb is registered)

Stdlib only.  Python 3.8+.
"""

import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace

# ---------------------------------------------------------------------------
# Path bootstrap: make _implement importable.
# ---------------------------------------------------------------------------
_LIB_DIR = str(Path(__file__).resolve().parents[3] / "src" / "devforge" / "lib")
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

from _implement._cmds_review_loop import (  # noqa: E402
    REVIEW_LOOP_CAP,
    parse_verdict,
    cmd_review_loop_step,
    EXIT_OK,
    EXIT_FINDINGS,
)


# ---------------------------------------------------------------------------
# Sample markdown templates
# ---------------------------------------------------------------------------

_REVIEW_APPROVE = """\
## Code Review

### Critical
(none)

### Warnings
- Consider renaming `x` to `value` for clarity.

### Structural Integration
- [new-file]: INTEGRATED

### Verdict: APPROVE
"""

_REVIEW_APPROVE_WITH_NOTES = """\
### Verdict: APPROVE (with warnings)
"""

_REVIEW_REQUEST_CHANGES = """\
### Verdict: REQUEST CHANGES
"""

_REVIEW_BLOCK = """\
### Verdict: BLOCK
"""

_REVIEW_UNFILLED_TEMPLATE = """\
### Verdict: APPROVE / REQUEST CHANGES / BLOCK
"""

# 2-token slash mixes — should be parse errors (F2 fix)
_REVIEW_TWO_TOKEN_APPROVE_REQUEST = """\
### Verdict: APPROVE / REQUEST CHANGES
"""

_REVIEW_TWO_TOKEN_BLOCK_APPROVE = """\
### Verdict: BLOCK / APPROVE
"""

_REVIEW_NO_VERDICT = """\
## Code Review

### Critical
(none)
"""

_REVIEW_BURIED = """\
Some preamble.

More text here.

### Other Section
stuff

### Verdict: BLOCK

trailing text
"""

_REVIEW_CASE_INSENSITIVE = """\
### verdict: APPROVE
"""

_REVIEW_TRAILING_PERIOD = """\
### Verdict: APPROVE.
"""

_REVIEW_EMPTY = ""


# ---------------------------------------------------------------------------
# Tests: parse_verdict (unit)
# ---------------------------------------------------------------------------


class TestParseVerdict(unittest.TestCase):

    def test_approve(self):
        token, err = parse_verdict(_REVIEW_APPROVE)
        self.assertEqual(token, "APPROVE")
        self.assertIsNone(err)

    def test_approve_with_warnings(self):
        """APPROVE with parenthetical note is still APPROVE."""
        token, err = parse_verdict(_REVIEW_APPROVE_WITH_NOTES)
        self.assertEqual(token, "APPROVE")
        self.assertIsNone(err)

    def test_request_changes(self):
        token, err = parse_verdict(_REVIEW_REQUEST_CHANGES)
        self.assertEqual(token, "REQUEST CHANGES")
        self.assertIsNone(err)

    def test_block(self):
        token, err = parse_verdict(_REVIEW_BLOCK)
        self.assertEqual(token, "BLOCK")
        self.assertIsNone(err)

    def test_missing_verdict_line(self):
        token, err = parse_verdict(_REVIEW_NO_VERDICT)
        self.assertIsNone(token)
        self.assertIsNotNone(err)
        self.assertIn("Verdict", err)

    def test_unfilled_template(self):
        """Template with all three slash-separated tokens → parse error."""
        token, err = parse_verdict(_REVIEW_UNFILLED_TEMPLATE)
        self.assertIsNone(token)
        self.assertIsNotNone(err)
        self.assertIn("unfilled", err.lower())

    def test_two_token_approve_request_changes_is_parse_error(self):
        """'APPROVE / REQUEST CHANGES' (2-token) → parse error, not clean APPROVE."""
        token, err = parse_verdict(_REVIEW_TWO_TOKEN_APPROVE_REQUEST)
        self.assertIsNone(token)
        self.assertIsNotNone(err)

    def test_two_token_block_approve_is_parse_error(self):
        """'BLOCK / APPROVE' (2-token, different order) → parse error."""
        token, err = parse_verdict(_REVIEW_TWO_TOKEN_BLOCK_APPROVE)
        self.assertIsNone(token)
        self.assertIsNotNone(err)

    def test_approve_with_warnings_no_slash_between_known_tokens(self):
        """'APPROVE (with warnings)' has no slash between known tokens → clean APPROVE."""
        token, err = parse_verdict(_REVIEW_APPROVE_WITH_NOTES)
        self.assertEqual(token, "APPROVE")
        self.assertIsNone(err)

    def test_case_insensitive_heading(self):
        """'### verdict:' (lowercase) matches the heading."""
        token, err = parse_verdict(_REVIEW_CASE_INSENSITIVE)
        self.assertEqual(token, "APPROVE")
        self.assertIsNone(err)

    def test_trailing_punctuation(self):
        """'APPROVE.' is parsed as APPROVE."""
        token, err = parse_verdict(_REVIEW_TRAILING_PERIOD)
        self.assertEqual(token, "APPROVE")
        self.assertIsNone(err)

    def test_verdict_buried_in_prose(self):
        """Verdict line buried after other headings still found."""
        token, err = parse_verdict(_REVIEW_BURIED)
        self.assertEqual(token, "BLOCK")
        self.assertIsNone(err)

    def test_empty_markdown(self):
        token, err = parse_verdict(_REVIEW_EMPTY)
        self.assertIsNone(token)
        self.assertIsNotNone(err)


# ---------------------------------------------------------------------------
# Tests: cmd_review_loop_step (integration)
# ---------------------------------------------------------------------------


class TestCmdReviewLoopStep(unittest.TestCase):
    """Tests for cmd_review_loop_step via direct function call."""

    def _call(self, markdown_text, iteration=0):
        """Call cmd_review_loop_step with markdown from a temp file.

        Returns (exit_code, stdout_json_or_none).
        """
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", encoding="utf-8", delete=False
        ) as fh:
            fh.write(markdown_text)
            tmp_path = fh.name
        try:
            args = SimpleNamespace(verdict_file=tmp_path, iteration=iteration)
            stdout_buf = io.StringIO()
            with patch("sys.stdout", stdout_buf):
                rc = cmd_review_loop_step(args)
            out = stdout_buf.getvalue().strip()
            payload = json.loads(out) if out else None
            return rc, payload
        finally:
            os.unlink(tmp_path)

    # --- Clean / dirty verdict ---

    def test_approve_iteration_0(self):
        rc, payload = self._call(_REVIEW_APPROVE, iteration=0)
        self.assertEqual(rc, EXIT_OK)
        self.assertIsNotNone(payload)
        self.assertTrue(payload["clean"])
        self.assertFalse(payload["escalate"])
        self.assertEqual(payload["iteration"], 0)
        self.assertEqual(payload["verdict"], "APPROVE")

    def test_approve_with_notes_is_clean(self):
        """APPROVE (with warnings) still emits clean=true."""
        rc, payload = self._call(_REVIEW_APPROVE_WITH_NOTES, iteration=0)
        self.assertEqual(rc, EXIT_OK)
        self.assertTrue(payload["clean"])
        self.assertEqual(payload["verdict"], "APPROVE")

    def test_request_changes_not_clean(self):
        rc, payload = self._call(_REVIEW_REQUEST_CHANGES, iteration=0)
        self.assertEqual(rc, EXIT_OK)
        self.assertFalse(payload["clean"])
        self.assertEqual(payload["verdict"], "REQUEST CHANGES")

    def test_block_not_clean(self):
        rc, payload = self._call(_REVIEW_BLOCK, iteration=0)
        self.assertEqual(rc, EXIT_OK)
        self.assertFalse(payload["clean"])
        self.assertEqual(payload["verdict"], "BLOCK")

    # --- Iteration / escalation boundary ---

    def test_iteration_0_no_escalate(self):
        rc, payload = self._call(_REVIEW_APPROVE, iteration=0)
        self.assertFalse(payload["escalate"])

    def test_iteration_1_no_escalate(self):
        rc, payload = self._call(_REVIEW_APPROVE, iteration=1)
        self.assertFalse(payload["escalate"])

    def test_iteration_2_no_escalate(self):
        """iteration=2 is still below cap of 3."""
        rc, payload = self._call(_REVIEW_APPROVE, iteration=2)
        self.assertEqual(REVIEW_LOOP_CAP, 3, "cap sentinel: test depends on cap=3")
        self.assertFalse(payload["escalate"])

    def test_iteration_3_escalates(self):
        """iteration=3 equals the cap → escalate=true."""
        rc, payload = self._call(_REVIEW_APPROVE, iteration=REVIEW_LOOP_CAP)
        self.assertEqual(rc, EXIT_OK)
        self.assertTrue(payload["escalate"])
        self.assertEqual(payload["iteration"], REVIEW_LOOP_CAP)

    def test_iteration_above_cap_escalates(self):
        rc, payload = self._call(_REVIEW_APPROVE, iteration=REVIEW_LOOP_CAP + 1)
        self.assertTrue(payload["escalate"])

    # --- Negative iteration validation ---

    def test_negative_iteration_exits_2(self):
        """iteration=-1 is invalid → exit 2, empty stdout."""
        args = SimpleNamespace(verdict_file=None, iteration=-1)
        stdin_mock = io.StringIO(_REVIEW_APPROVE)
        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        with (
            patch("sys.stdin", stdin_mock),
            patch("sys.stdout", stdout_buf),
            patch("sys.stderr", stderr_buf),
        ):
            rc = cmd_review_loop_step(args)
        self.assertEqual(rc, EXIT_FINDINGS)
        self.assertEqual(stdout_buf.getvalue().strip(), "")

    # --- Parse errors → exit 2 ---

    def test_missing_verdict_exits_2(self):
        rc, payload = self._call(_REVIEW_NO_VERDICT, iteration=0)
        self.assertEqual(rc, EXIT_FINDINGS)
        self.assertIsNone(payload)

    def test_unfilled_template_exits_2(self):
        rc, payload = self._call(_REVIEW_UNFILLED_TEMPLATE, iteration=0)
        self.assertEqual(rc, EXIT_FINDINGS)
        self.assertIsNone(payload)

    def test_two_token_slash_mix_approve_request_exits_2(self):
        """'APPROVE / REQUEST CHANGES' ambiguous template → exit 2 (F2)."""
        rc, payload = self._call(_REVIEW_TWO_TOKEN_APPROVE_REQUEST, iteration=0)
        self.assertEqual(rc, EXIT_FINDINGS)
        self.assertIsNone(payload)

    def test_two_token_slash_mix_block_approve_exits_2(self):
        """'BLOCK / APPROVE' ambiguous template → exit 2 (F2)."""
        rc, payload = self._call(_REVIEW_TWO_TOKEN_BLOCK_APPROVE, iteration=0)
        self.assertEqual(rc, EXIT_FINDINGS)
        self.assertIsNone(payload)

    def test_approve_with_warnings_is_clean_not_parse_error(self):
        """'APPROVE (with warnings)' does not trigger slash-mix guard → clean APPROVE."""
        rc, payload = self._call(_REVIEW_APPROVE_WITH_NOTES, iteration=0)
        self.assertEqual(rc, EXIT_OK)
        self.assertIsNotNone(payload)
        self.assertTrue(payload["clean"])

    # --- stdin path ---

    def test_reads_from_stdin_when_no_verdict_file(self):
        args = SimpleNamespace(verdict_file=None, iteration=0)
        stdin_mock = io.StringIO(_REVIEW_BLOCK)
        stdout_buf = io.StringIO()
        with patch("sys.stdin", stdin_mock), patch("sys.stdout", stdout_buf):
            rc = cmd_review_loop_step(args)
        self.assertEqual(rc, EXIT_OK)
        payload = json.loads(stdout_buf.getvalue().strip())
        self.assertFalse(payload["clean"])
        self.assertEqual(payload["verdict"], "BLOCK")

    # --- --verdict-file path ---

    def test_reads_from_verdict_file(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", encoding="utf-8", delete=False
        ) as fh:
            fh.write(_REVIEW_APPROVE)
            tmp_path = fh.name
        try:
            args = SimpleNamespace(verdict_file=tmp_path, iteration=0)
            stdout_buf = io.StringIO()
            with patch("sys.stdout", stdout_buf):
                rc = cmd_review_loop_step(args)
            self.assertEqual(rc, EXIT_OK)
            payload = json.loads(stdout_buf.getvalue().strip())
            self.assertTrue(payload["clean"])
        finally:
            os.unlink(tmp_path)

    def test_missing_verdict_file_exits_2(self):
        args = SimpleNamespace(
            verdict_file="/tmp/__nonexistent_review_file_xyz123.md",
            iteration=0,
        )
        stderr_buf = io.StringIO()
        stdout_buf = io.StringIO()
        with patch("sys.stderr", stderr_buf), patch("sys.stdout", stdout_buf):
            rc = cmd_review_loop_step(args)
        self.assertEqual(rc, EXIT_FINDINGS)
        self.assertEqual(stdout_buf.getvalue().strip(), "")


# ---------------------------------------------------------------------------
# Tests: CLI wiring (verb registered in _cli.py)
# ---------------------------------------------------------------------------


class TestCliWiring(unittest.TestCase):
    """Verify review-loop-step is wired into the CLI."""

    def test_help_exits_zero(self):
        """implement_helper.py review-loop-step --help exits 0."""
        helper_py = str(
            Path(__file__).resolve().parents[3]
            / "src"
            / "devforge"
            / "lib"
            / "implement_helper.py"
        )
        import subprocess
        result = subprocess.run(
            [sys.executable, helper_py, "review-loop-step", "--help"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("verdict", result.stdout.lower())


if __name__ == "__main__":
    unittest.main()
