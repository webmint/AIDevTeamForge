"""Tests for src/devforge/lib/_implement/_cmds_review_panel.py.

Coverage
--------

_parse_reviewer_verdict (unit):
  - All four reviewers with their clean token → (token, clean_token, None)
  - Each reviewer's not-clean tokens recognised
  - Unknown agent-name → error naming the reviewer
  - Missing ### Verdict: line → error naming the reviewer
  - Unfilled template (slash-separated tokens) → error naming the reviewer
  - Token not in that reviewer's vocab → error naming the reviewer (cross-vocab)
  - Unreadable file (OSError) → error naming the reviewer

cmd_merge_review_panel (integration via function call):
  - All 4 clean → {clean: true, per_reviewer: all clean}
  - One not-clean (security FAIL) → {clean: false, security-reviewer clean: false}
  - Each reviewer's not-clean token independently
  - escalate false below REVIEW_LOOP_CAP, true at/above cap
  - cap value is imported from _cmds_review_loop (not a local copy)
  - per_reviewer order matches CLI --reviewer order
  - Parse error (missing verdict) → exit 2, no JSON, stderr names reviewer
  - Parse error (unknown agent) → exit 2, no JSON, stderr names agent
  - Parse error (unfilled template) → exit 2, no JSON
  - Parse error (wrong-vocab token, e.g. code-reviewer PASS) → exit 2
  - No --reviewer args → exit 2
  - Malformed --reviewer (no colon) → exit 2
  - Negative iteration → exit 2

CLI wiring:
  - 'merge-review-panel --help' exits 0 (verb is registered)

Real markdown shapes:
  Fixtures use the actual agent Output template shapes from
  src/agents/{code-reviewer,qa-reviewer,security-reviewer,performance-analyst}.md
  -- not hand-faked uniform formats.  Each reviewer block mirrors the
  real output section the agent emits.

Stdlib only.  Python 3.8+.
"""

import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

# ---------------------------------------------------------------------------
# Path bootstrap: make _implement importable.
# ---------------------------------------------------------------------------
_LIB_DIR = str(Path(__file__).resolve().parents[3] / "src" / "devforge" / "lib")
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

from _implement._cmds_review_panel import (  # noqa: E402
    cmd_merge_review_panel,
    _parse_reviewer_verdict,
    EXIT_OK,
    EXIT_PARSE_ERROR,
    _REVIEWER_VOCAB,
)
from _implement._cmds_review_loop import REVIEW_LOOP_CAP  # noqa: E402


# ---------------------------------------------------------------------------
# Real reviewer markdown fixtures
# (shapes taken from the actual ## Output templates in each agent file)
# ---------------------------------------------------------------------------

# code-reviewer Output shape:
# ## Code Review
# ### Files Reviewed
# ### Issues
# #### Critical (must fix)
# #### High / Medium / Info
# ### Structural Integration
# ### Verdict: APPROVE / REQUEST CHANGES / BLOCK

_CODE_REVIEWER_APPROVE = """\
## Code Review

### Files Reviewed
- src/foo.py: Added helper function `_compute`

### Issues

#### Critical (must fix)
(none)

#### High
(none)

#### Medium
(none)

#### Info
- Consider adding a docstring to `_compute`.

### Structural Integration
- src/foo.py: INTEGRATED

### Verdict: APPROVE
"""

_CODE_REVIEWER_REQUEST_CHANGES = """\
## Code Review

### Files Reviewed
- src/bar.py: Rewrote error handler

### Issues

#### Critical (must fix)
- src/bar.py:42 — Missing rollback on DB failure

### Verdict: REQUEST CHANGES
"""

_CODE_REVIEWER_BLOCK = """\
## Code Review

### Issues

#### Critical (must fix)
- src/auth.py:10 — Hardcoded secret key

### Verdict: BLOCK
"""

# qa-reviewer Output shape:
# ## Test Assessment
# ### AC Coverage
# ### Gaps
# ### Verdict: ADEQUATE / GAPS FOUND

_QA_REVIEWER_ADEQUATE = """\
## Test Assessment

### AC Coverage
- AC-1: covered by test_compute_basic (unit)
- AC-2: covered by test_compute_edge (unit)

### Gaps
(none)

### Verdict: ADEQUATE
"""

_QA_REVIEWER_GAPS_FOUND = """\
## Test Assessment

### AC Coverage
- AC-1: covered by test_compute_basic (unit)
- AC-2: NOT COVERED — Severity: High

### Gaps
- No integration test for DB failure path — Severity: High
  Location: src/db.py:88
  Why it matters: Rollback logic is untested

### Verdict: GAPS FOUND
"""

# security-reviewer Output shape:
# ## Security Review
# ### Findings
# #### Critical / High / Medium / Info
# ### Summary
# ### Verdict: PASS / FAIL

_SECURITY_REVIEWER_PASS = """\
## Security Review

### Findings

#### Critical (exploit risk)
(none)

#### High (security weakness)
(none)

#### Medium (defense-in-depth gap)
(none)

#### Info (hardening suggestion)
- Consider adding rate limiting to the API endpoint.

### Summary
- Critical: 0 | High: 0 | Medium: 0 | Info: 1

### Verdict: PASS
"""

_SECURITY_REVIEWER_FAIL = """\
## Security Review

### Findings

#### Critical (exploit risk)
- src/auth.py:10 [CWE-798] — Hardcoded API secret in source code;
  remediation: move to environment variable or secrets manager

### Summary
- Critical: 1 | High: 0 | Medium: 0 | Info: 0

### Verdict: FAIL
"""

# performance-analyst Output shape:
# ## Performance Analysis
# ### Verdict: MEETS TARGETS / BOTTLENECKS FOUND     <-- note: FIRST in template
# ### Current Metrics
# ### Bottlenecks Found

_PERFORMANCE_ANALYST_MEETS_TARGETS = """\
## Performance Analysis

### Verdict: MEETS TARGETS

### Current Metrics
| Metric | Value | Target |
|--------|-------|--------|
| p95 latency | 48ms | <100ms |
| throughput | 1200 req/s | >1000 req/s |

### Bottlenecks Found
(none)
"""

_PERFORMANCE_ANALYST_BOTTLENECKS_FOUND = """\
## Performance Analysis

### Verdict: BOTTLENECKS FOUND

### Current Metrics
| Metric | Value | Target |
|--------|-------|--------|
| p95 latency | 420ms | <100ms |

### Bottlenecks Found
1. N+1 query in `list_users` — Severity: High
   - Root cause: ORM lazy-loads related records
   - Recommended fix: Use `select_related` — backend-engineer should apply
"""


# ---------------------------------------------------------------------------
# Helper: write markdown to a temp file; return path.
# ---------------------------------------------------------------------------


def _write_tmp(content, suffix=".md"):
    # type: (str, str) -> str
    """Write content to a temp file and return its path.  Caller must unlink."""
    fd, path = tempfile.mkstemp(suffix=suffix)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(content)
    except Exception:
        os.unlink(path)
        raise
    return path


# ---------------------------------------------------------------------------
# Helper: call cmd_merge_review_panel with a list of (agent, markdown_str).
# Returns (exit_code, payload_or_None).
# ---------------------------------------------------------------------------


def _call_panel(reviewer_pairs, iteration=0):
    # type: (list, int) -> tuple
    """
    reviewer_pairs: list of (agent_name, markdown_str).
    Writes each markdown to a temp file, builds --reviewer args, calls the
    handler, and cleans up.  Returns (exit_code, parsed_json_or_None).
    """
    tmp_paths = []
    reviewer_args = []
    try:
        for agent_name, markdown in reviewer_pairs:
            path = _write_tmp(markdown)
            tmp_paths.append(path)
            reviewer_args.append("{name}:{path}".format(name=agent_name, path=path))

        args = SimpleNamespace(reviewer=reviewer_args, iteration=iteration)
        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        with patch("sys.stdout", stdout_buf), patch("sys.stderr", stderr_buf):
            rc = cmd_merge_review_panel(args)
        out = stdout_buf.getvalue().strip()
        payload = json.loads(out) if out else None
        return rc, payload
    finally:
        for p in tmp_paths:
            try:
                os.unlink(p)
            except OSError:
                pass


def _call_panel_with_stderr(reviewer_pairs, iteration=0):
    # type: (list, int) -> tuple
    """Like _call_panel but also returns the stderr string."""
    tmp_paths = []
    reviewer_args = []
    try:
        for agent_name, markdown in reviewer_pairs:
            path = _write_tmp(markdown)
            tmp_paths.append(path)
            reviewer_args.append("{name}:{path}".format(name=agent_name, path=path))

        args = SimpleNamespace(reviewer=reviewer_args, iteration=iteration)
        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        with patch("sys.stdout", stdout_buf), patch("sys.stderr", stderr_buf):
            rc = cmd_merge_review_panel(args)
        out = stdout_buf.getvalue().strip()
        payload = json.loads(out) if out else None
        return rc, payload, stderr_buf.getvalue()
    finally:
        for p in tmp_paths:
            try:
                os.unlink(p)
            except OSError:
                pass


# ---------------------------------------------------------------------------
# Tests: _parse_reviewer_verdict (unit)
# ---------------------------------------------------------------------------


class TestParseReviewerVerdict(unittest.TestCase):
    """Unit tests for the per-reviewer verdict parser."""

    def _call(self, agent_name, markdown):
        # type: (str, str) -> tuple
        path = _write_tmp(markdown)
        try:
            return _parse_reviewer_verdict(agent_name, path)
        finally:
            os.unlink(path)

    # --- Clean tokens for all four reviewers ---

    def test_code_reviewer_approve(self):
        token, clean_token, err = self._call("code-reviewer", _CODE_REVIEWER_APPROVE)
        self.assertEqual(token, "APPROVE")
        self.assertEqual(clean_token, "APPROVE")
        self.assertIsNone(err)

    def test_qa_reviewer_adequate(self):
        token, clean_token, err = self._call("qa-reviewer", _QA_REVIEWER_ADEQUATE)
        self.assertEqual(token, "ADEQUATE")
        self.assertEqual(clean_token, "ADEQUATE")
        self.assertIsNone(err)

    def test_security_reviewer_pass(self):
        token, clean_token, err = self._call(
            "security-reviewer", _SECURITY_REVIEWER_PASS
        )
        self.assertEqual(token, "PASS")
        self.assertEqual(clean_token, "PASS")
        self.assertIsNone(err)

    def test_performance_analyst_meets_targets(self):
        token, clean_token, err = self._call(
            "performance-analyst", _PERFORMANCE_ANALYST_MEETS_TARGETS
        )
        self.assertEqual(token, "MEETS TARGETS")
        self.assertEqual(clean_token, "MEETS TARGETS")
        self.assertIsNone(err)

    # --- Not-clean tokens for all four reviewers ---

    def test_code_reviewer_request_changes(self):
        token, clean_token, err = self._call(
            "code-reviewer", _CODE_REVIEWER_REQUEST_CHANGES
        )
        self.assertEqual(token, "REQUEST CHANGES")
        self.assertIsNone(err)

    def test_code_reviewer_block(self):
        token, clean_token, err = self._call("code-reviewer", _CODE_REVIEWER_BLOCK)
        self.assertEqual(token, "BLOCK")
        self.assertIsNone(err)

    def test_qa_reviewer_gaps_found(self):
        token, clean_token, err = self._call("qa-reviewer", _QA_REVIEWER_GAPS_FOUND)
        self.assertEqual(token, "GAPS FOUND")
        self.assertIsNone(err)

    def test_security_reviewer_fail(self):
        token, clean_token, err = self._call(
            "security-reviewer", _SECURITY_REVIEWER_FAIL
        )
        self.assertEqual(token, "FAIL")
        self.assertIsNone(err)

    def test_performance_analyst_bottlenecks_found(self):
        token, clean_token, err = self._call(
            "performance-analyst", _PERFORMANCE_ANALYST_BOTTLENECKS_FOUND
        )
        self.assertEqual(token, "BOTTLENECKS FOUND")
        self.assertIsNone(err)

    # --- Unknown agent-name ---

    def test_unknown_agent_name(self):
        """Unknown agent-name → error that names the agent."""
        token, clean_token, err = self._call("unknown-agent", _CODE_REVIEWER_APPROVE)
        self.assertIsNone(token)
        self.assertIsNotNone(err)
        self.assertIn("unknown-agent", err)

    # --- Missing verdict line ---

    def test_missing_verdict_line(self):
        """No ### Verdict: line → error that names the reviewer."""
        markdown = """\
## Security Review

### Findings
(none)

### Summary
- Critical: 0
"""
        token, clean_token, err = self._call("security-reviewer", markdown)
        self.assertIsNone(token)
        self.assertIsNotNone(err)
        self.assertIn("security-reviewer", err)
        self.assertIn("Verdict", err)

    # --- Unfilled template ---

    def test_unfilled_template_code_reviewer(self):
        """### Verdict: APPROVE / REQUEST CHANGES / BLOCK (not filled) → error."""
        markdown = "### Verdict: APPROVE / REQUEST CHANGES / BLOCK\n"
        token, clean_token, err = self._call("code-reviewer", markdown)
        self.assertIsNone(token)
        self.assertIsNotNone(err)
        self.assertIn("code-reviewer", err)

    def test_unfilled_template_qa_reviewer(self):
        """### Verdict: ADEQUATE / GAPS FOUND (not filled) → error."""
        markdown = "### Verdict: ADEQUATE / GAPS FOUND\n"
        token, clean_token, err = self._call("qa-reviewer", markdown)
        self.assertIsNone(token)
        self.assertIsNotNone(err)
        self.assertIn("qa-reviewer", err)

    def test_unfilled_template_security_reviewer(self):
        """### Verdict: PASS / FAIL (not filled) → error."""
        markdown = "### Verdict: PASS / FAIL\n"
        token, clean_token, err = self._call("security-reviewer", markdown)
        self.assertIsNone(token)
        self.assertIsNotNone(err)
        self.assertIn("security-reviewer", err)

    def test_unfilled_template_performance_analyst(self):
        """### Verdict: MEETS TARGETS / BOTTLENECKS FOUND (not filled) → error."""
        markdown = "### Verdict: MEETS TARGETS / BOTTLENECKS FOUND\n"
        token, clean_token, err = self._call("performance-analyst", markdown)
        self.assertIsNone(token)
        self.assertIsNotNone(err)
        self.assertIn("performance-analyst", err)

    # --- Cross-vocab token (token valid for another reviewer) ---

    def test_cross_vocab_code_reviewer_gets_pass(self):
        """code-reviewer markdown says ### Verdict: PASS (security vocab) → error."""
        markdown = "### Verdict: PASS\n"
        token, clean_token, err = self._call("code-reviewer", markdown)
        self.assertIsNone(token)
        self.assertIsNotNone(err)
        self.assertIn("code-reviewer", err)

    def test_cross_vocab_security_reviewer_gets_approve(self):
        """security-reviewer markdown says ### Verdict: APPROVE (code-reviewer vocab) → error."""
        markdown = "### Verdict: APPROVE\n"
        token, clean_token, err = self._call("security-reviewer", markdown)
        self.assertIsNone(token)
        self.assertIsNotNone(err)
        self.assertIn("security-reviewer", err)

    def test_cross_vocab_qa_reviewer_gets_meets_targets(self):
        """qa-reviewer markdown says ### Verdict: MEETS TARGETS → error."""
        markdown = "### Verdict: MEETS TARGETS\n"
        token, clean_token, err = self._call("qa-reviewer", markdown)
        self.assertIsNone(token)
        self.assertIsNotNone(err)
        self.assertIn("qa-reviewer", err)

    def test_cross_vocab_performance_analyst_gets_approve(self):
        """performance-analyst markdown says ### Verdict: APPROVE (code-reviewer vocab) → error."""
        markdown = "### Verdict: APPROVE\n"
        token, clean_token, err = self._call("performance-analyst", markdown)
        self.assertIsNone(token)
        self.assertIsNotNone(err)
        self.assertIn("performance-analyst", err)

    def test_cross_vocab_performance_analyst_gets_pass(self):
        """performance-analyst markdown says ### Verdict: PASS (security vocab) → error."""
        markdown = "### Verdict: PASS\n"
        token, clean_token, err = self._call("performance-analyst", markdown)
        self.assertIsNone(token)
        self.assertIsNotNone(err)
        self.assertIn("performance-analyst", err)

    # --- Unreadable file ---

    def test_unreadable_file(self):
        """Non-existent file → error that names the reviewer."""
        token, clean_token, err = _parse_reviewer_verdict(
            "security-reviewer", "/tmp/__no_such_panel_file_xyz123.md"
        )
        self.assertIsNone(token)
        self.assertIsNotNone(err)
        self.assertIn("security-reviewer", err)

    # --- Case-insensitive heading ---

    def test_case_insensitive_heading_matches(self):
        """### verdict: PASS (lowercase heading) still parses."""
        markdown = "### verdict: PASS\n"
        token, clean_token, err = self._call("security-reviewer", markdown)
        self.assertEqual(token, "PASS")
        self.assertIsNone(err)

    # --- Verdict buried in prose ---

    def test_verdict_buried_in_prose(self):
        """Verdict line after several unrelated sections still found."""
        markdown = """\
## Security Review

Some preamble about the review process.

### Findings
(none)

### Summary
- All clear

### Verdict: PASS
"""
        token, clean_token, err = self._call("security-reviewer", markdown)
        self.assertEqual(token, "PASS")
        self.assertIsNone(err)

    # --- Meets Targets multi-word token precedence ---

    def test_meets_targets_not_shadowed_by_shorter(self):
        """'MEETS TARGETS' (2-word token) is correctly matched, not clipped."""
        token, clean_token, err = self._call(
            "performance-analyst", _PERFORMANCE_ANALYST_MEETS_TARGETS
        )
        self.assertEqual(token, "MEETS TARGETS")
        self.assertIsNone(err)


# ---------------------------------------------------------------------------
# Tests: cmd_merge_review_panel (integration)
# ---------------------------------------------------------------------------


class TestCmdMergeReviewPanel(unittest.TestCase):
    """Integration tests for cmd_merge_review_panel via function call."""

    # --- All-clean (all four reviewers with their clean token) ---

    def test_all_four_clean(self):
        """All four reviewers emit their clean token → clean=true."""
        rc, payload = _call_panel([
            ("code-reviewer", _CODE_REVIEWER_APPROVE),
            ("qa-reviewer", _QA_REVIEWER_ADEQUATE),
            ("security-reviewer", _SECURITY_REVIEWER_PASS),
            ("performance-analyst", _PERFORMANCE_ANALYST_MEETS_TARGETS),
        ], iteration=0)
        self.assertEqual(rc, EXIT_OK)
        self.assertIsNotNone(payload)
        self.assertTrue(payload["clean"])
        self.assertEqual(payload["iteration"], 0)
        self.assertFalse(payload["escalate"])
        self.assertEqual(len(payload["per_reviewer"]), 4)
        for reviewer in payload["per_reviewer"]:
            self.assertTrue(reviewer["clean"], msg="Expected clean for " + reviewer["agent"])

    # --- One reviewer not-clean ---

    def test_security_fail_makes_panel_not_clean(self):
        """Security FAIL → overall clean=false; only security-reviewer clean=false."""
        rc, payload = _call_panel([
            ("code-reviewer", _CODE_REVIEWER_APPROVE),
            ("qa-reviewer", _QA_REVIEWER_ADEQUATE),
            ("security-reviewer", _SECURITY_REVIEWER_FAIL),
            ("performance-analyst", _PERFORMANCE_ANALYST_MEETS_TARGETS),
        ], iteration=0)
        self.assertEqual(rc, EXIT_OK)
        self.assertIsNotNone(payload)
        self.assertFalse(payload["clean"])
        # security-reviewer should be not-clean
        sec = next(r for r in payload["per_reviewer"] if r["agent"] == "security-reviewer")
        self.assertFalse(sec["clean"])
        self.assertEqual(sec["verdict"], "FAIL")
        # others should be clean
        for r in payload["per_reviewer"]:
            if r["agent"] != "security-reviewer":
                self.assertTrue(r["clean"], msg=r["agent"] + " should be clean")

    # --- Each reviewer's not-clean token independently ---

    def test_code_reviewer_request_changes_not_clean(self):
        rc, payload = _call_panel([
            ("code-reviewer", _CODE_REVIEWER_REQUEST_CHANGES),
        ])
        self.assertEqual(rc, EXIT_OK)
        self.assertFalse(payload["clean"])
        self.assertEqual(payload["per_reviewer"][0]["verdict"], "REQUEST CHANGES")
        self.assertFalse(payload["per_reviewer"][0]["clean"])

    def test_code_reviewer_block_not_clean(self):
        rc, payload = _call_panel([
            ("code-reviewer", _CODE_REVIEWER_BLOCK),
        ])
        self.assertEqual(rc, EXIT_OK)
        self.assertFalse(payload["clean"])
        self.assertEqual(payload["per_reviewer"][0]["verdict"], "BLOCK")

    def test_qa_reviewer_gaps_found_not_clean(self):
        rc, payload = _call_panel([
            ("qa-reviewer", _QA_REVIEWER_GAPS_FOUND),
        ])
        self.assertEqual(rc, EXIT_OK)
        self.assertFalse(payload["clean"])
        self.assertEqual(payload["per_reviewer"][0]["verdict"], "GAPS FOUND")

    def test_performance_analyst_bottlenecks_found_not_clean(self):
        rc, payload = _call_panel([
            ("performance-analyst", _PERFORMANCE_ANALYST_BOTTLENECKS_FOUND),
        ])
        self.assertEqual(rc, EXIT_OK)
        self.assertFalse(payload["clean"])
        self.assertEqual(payload["per_reviewer"][0]["verdict"], "BOTTLENECKS FOUND")

    # --- escalate boundary: imported REVIEW_LOOP_CAP ---

    def test_escalate_false_below_cap(self):
        """iteration < REVIEW_LOOP_CAP → escalate=false."""
        rc, payload = _call_panel(
            [("security-reviewer", _SECURITY_REVIEWER_PASS)],
            iteration=REVIEW_LOOP_CAP - 1,
        )
        self.assertEqual(rc, EXIT_OK)
        self.assertFalse(payload["escalate"])

    def test_escalate_true_at_cap(self):
        """iteration == REVIEW_LOOP_CAP → escalate=true."""
        rc, payload = _call_panel(
            [("security-reviewer", _SECURITY_REVIEWER_PASS)],
            iteration=REVIEW_LOOP_CAP,
        )
        self.assertEqual(rc, EXIT_OK)
        self.assertTrue(payload["escalate"])
        self.assertEqual(payload["iteration"], REVIEW_LOOP_CAP)

    def test_escalate_true_above_cap(self):
        """iteration > REVIEW_LOOP_CAP → escalate=true."""
        rc, payload = _call_panel(
            [("security-reviewer", _SECURITY_REVIEWER_PASS)],
            iteration=REVIEW_LOOP_CAP + 1,
        )
        self.assertEqual(rc, EXIT_OK)
        self.assertTrue(payload["escalate"])

    def test_escalate_false_at_iteration_0(self):
        rc, payload = _call_panel(
            [("security-reviewer", _SECURITY_REVIEWER_PASS)],
            iteration=0,
        )
        self.assertFalse(payload["escalate"])

    def test_cap_is_imported_from_review_loop_module(self):
        """REVIEW_LOOP_CAP imported from _cmds_review_loop matches panel module's import."""
        # Both the panel module and this test import from the same source.
        # If the panel module had a LOCAL copy it would be a different object;
        # instead we verify the value is the same constant used in _cmds_review_loop.
        from _implement._cmds_review_panel import REVIEW_LOOP_CAP as PANEL_CAP  # noqa: E402
        from _implement._cmds_review_loop import REVIEW_LOOP_CAP as LOOP_CAP  # noqa: E402
        self.assertIs(PANEL_CAP, LOOP_CAP,
                      "REVIEW_LOOP_CAP must be the imported object, not a local copy")

    # --- per_reviewer order matches CLI order ---

    def test_per_reviewer_order_matches_cli_order(self):
        """per_reviewer list is ordered as given on the CLI."""
        rc, payload = _call_panel([
            ("performance-analyst", _PERFORMANCE_ANALYST_MEETS_TARGETS),
            ("qa-reviewer", _QA_REVIEWER_ADEQUATE),
            ("code-reviewer", _CODE_REVIEWER_APPROVE),
            ("security-reviewer", _SECURITY_REVIEWER_PASS),
        ])
        self.assertEqual(rc, EXIT_OK)
        agents = [r["agent"] for r in payload["per_reviewer"]]
        self.assertEqual(
            agents,
            ["performance-analyst", "qa-reviewer", "code-reviewer", "security-reviewer"],
        )

    # --- JSON fields present and typed ---

    def test_json_shape(self):
        """Output JSON has exactly the four expected keys with correct types."""
        rc, payload = _call_panel([
            ("code-reviewer", _CODE_REVIEWER_APPROVE),
        ])
        self.assertEqual(rc, EXIT_OK)
        self.assertIn("clean", payload)
        self.assertIn("escalate", payload)
        self.assertIn("iteration", payload)
        self.assertIn("per_reviewer", payload)
        self.assertIsInstance(payload["clean"], bool)
        self.assertIsInstance(payload["escalate"], bool)
        self.assertIsInstance(payload["iteration"], int)
        self.assertIsInstance(payload["per_reviewer"], list)

    def test_per_reviewer_entry_shape(self):
        """Each per_reviewer entry has agent, verdict, clean."""
        rc, payload = _call_panel([
            ("code-reviewer", _CODE_REVIEWER_APPROVE),
        ])
        entry = payload["per_reviewer"][0]
        self.assertIn("agent", entry)
        self.assertIn("verdict", entry)
        self.assertIn("clean", entry)
        self.assertEqual(entry["agent"], "code-reviewer")
        self.assertIsInstance(entry["clean"], bool)

    # --- Parse errors → exit 2, no JSON, stderr names reviewer ---

    def test_parse_error_missing_verdict_exits_2_names_reviewer(self):
        """Missing ### Verdict: line → exit 2, stderr names the failing reviewer."""
        markdown_no_verdict = """\
## Security Review

### Findings
(none)
"""
        rc, payload, stderr = _call_panel_with_stderr([
            ("code-reviewer", _CODE_REVIEWER_APPROVE),
            ("security-reviewer", markdown_no_verdict),
        ])
        self.assertEqual(rc, EXIT_PARSE_ERROR)
        self.assertIsNone(payload)
        self.assertIn("security-reviewer", stderr)

    def test_parse_error_unknown_agent_exits_2_names_agent(self):
        """Unknown agent-name → exit 2, stderr contains the bad name."""
        rc, payload, stderr = _call_panel_with_stderr([
            ("mystery-reviewer", _CODE_REVIEWER_APPROVE),
        ])
        self.assertEqual(rc, EXIT_PARSE_ERROR)
        self.assertIsNone(payload)
        self.assertIn("mystery-reviewer", stderr)

    def test_parse_error_unfilled_template_exits_2(self):
        """Unfilled template → exit 2, no JSON."""
        markdown_unfilled = "### Verdict: PASS / FAIL\n"
        rc, payload, stderr = _call_panel_with_stderr([
            ("security-reviewer", markdown_unfilled),
        ])
        self.assertEqual(rc, EXIT_PARSE_ERROR)
        self.assertIsNone(payload)
        self.assertIn("security-reviewer", stderr)

    def test_parse_error_wrong_vocab_token_exits_2_names_reviewer(self):
        """code-reviewer markdown says PASS (security vocab) → exit 2, stderr names reviewer."""
        markdown_wrong_vocab = "### Verdict: PASS\n"
        rc, payload, stderr = _call_panel_with_stderr([
            ("code-reviewer", markdown_wrong_vocab),
        ])
        self.assertEqual(rc, EXIT_PARSE_ERROR)
        self.assertIsNone(payload)
        self.assertIn("code-reviewer", stderr)

    def test_parse_error_stops_before_later_reviewers(self):
        """Error on second reviewer → exit 2; no output even though first was OK."""
        rc, payload, stderr = _call_panel_with_stderr([
            ("code-reviewer", _CODE_REVIEWER_APPROVE),
            ("security-reviewer", "### Verdict: PASS / FAIL\n"),  # unfilled
            ("qa-reviewer", _QA_REVIEWER_ADEQUATE),
        ])
        self.assertEqual(rc, EXIT_PARSE_ERROR)
        self.assertIsNone(payload)
        self.assertIn("security-reviewer", stderr)

    # --- No --reviewer args ---

    def test_no_reviewer_args_exits_2(self):
        """No --reviewer arguments → exit 2."""
        args = SimpleNamespace(reviewer=None, iteration=0)
        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        with patch("sys.stdout", stdout_buf), patch("sys.stderr", stderr_buf):
            rc = cmd_merge_review_panel(args)
        self.assertEqual(rc, EXIT_PARSE_ERROR)
        self.assertEqual(stdout_buf.getvalue().strip(), "")

    def test_empty_reviewer_list_exits_2(self):
        """Empty --reviewer list → exit 2."""
        args = SimpleNamespace(reviewer=[], iteration=0)
        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        with patch("sys.stdout", stdout_buf), patch("sys.stderr", stderr_buf):
            rc = cmd_merge_review_panel(args)
        self.assertEqual(rc, EXIT_PARSE_ERROR)
        self.assertEqual(stdout_buf.getvalue().strip(), "")

    # --- Malformed --reviewer (no colon) ---

    def test_malformed_reviewer_no_colon_exits_2(self):
        """--reviewer without a colon separator → exit 2."""
        args = SimpleNamespace(reviewer=["code-reviewer-no-path"], iteration=0)
        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        with patch("sys.stdout", stdout_buf), patch("sys.stderr", stderr_buf):
            rc = cmd_merge_review_panel(args)
        self.assertEqual(rc, EXIT_PARSE_ERROR)
        self.assertEqual(stdout_buf.getvalue().strip(), "")

    def test_malformed_reviewer_leading_colon_exits_2(self):
        """--reviewer ':path' (empty agent name) → exit 2."""
        args = SimpleNamespace(reviewer=[":/tmp/foo.md"], iteration=0)
        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        with patch("sys.stdout", stdout_buf), patch("sys.stderr", stderr_buf):
            rc = cmd_merge_review_panel(args)
        self.assertEqual(rc, EXIT_PARSE_ERROR)
        self.assertEqual(stdout_buf.getvalue().strip(), "")

    # --- Negative iteration ---

    def test_negative_iteration_exits_2(self):
        """Negative iteration → exit 2, no JSON."""
        args = SimpleNamespace(reviewer=["code-reviewer:/tmp/foo.md"], iteration=-1)
        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        with patch("sys.stdout", stdout_buf), patch("sys.stderr", stderr_buf):
            rc = cmd_merge_review_panel(args)
        self.assertEqual(rc, EXIT_PARSE_ERROR)
        self.assertEqual(stdout_buf.getvalue().strip(), "")

    # --- Single reviewer, clean=true iff that reviewer is clean ---

    def test_single_reviewer_clean(self):
        rc, payload = _call_panel([
            ("qa-reviewer", _QA_REVIEWER_ADEQUATE),
        ])
        self.assertEqual(rc, EXIT_OK)
        self.assertTrue(payload["clean"])
        self.assertEqual(len(payload["per_reviewer"]), 1)
        self.assertTrue(payload["per_reviewer"][0]["clean"])

    def test_single_reviewer_not_clean(self):
        rc, payload = _call_panel([
            ("qa-reviewer", _QA_REVIEWER_GAPS_FOUND),
        ])
        self.assertEqual(rc, EXIT_OK)
        self.assertFalse(payload["clean"])

    # --- Multiple not-clean reviewers ---

    def test_two_not_clean_reviewers(self):
        """Two dirty reviewers → clean=false, both marked not-clean."""
        rc, payload = _call_panel([
            ("code-reviewer", _CODE_REVIEWER_BLOCK),
            ("security-reviewer", _SECURITY_REVIEWER_FAIL),
        ])
        self.assertEqual(rc, EXIT_OK)
        self.assertFalse(payload["clean"])
        for r in payload["per_reviewer"]:
            self.assertFalse(r["clean"])

    # --- Iteration value is echoed in output ---

    def test_iteration_echoed_in_output(self):
        rc, payload = _call_panel(
            [("code-reviewer", _CODE_REVIEWER_APPROVE)],
            iteration=2,
        )
        self.assertEqual(rc, EXIT_OK)
        self.assertEqual(payload["iteration"], 2)


# ---------------------------------------------------------------------------
# Tests: CLI wiring (verb registered in _cli.py)
# ---------------------------------------------------------------------------


class TestCliWiring(unittest.TestCase):
    """Verify merge-review-panel is wired into the CLI."""

    def test_help_exits_zero_and_mentions_reviewer(self):
        """implement_helper.py merge-review-panel --help exits 0."""
        helper_py = str(
            Path(__file__).resolve().parents[3]
            / "src"
            / "devforge"
            / "lib"
            / "implement_helper.py"
        )
        result = subprocess.run(
            [sys.executable, helper_py, "merge-review-panel", "--help"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("reviewer", result.stdout.lower())

    def test_verb_appears_in_top_level_help(self):
        """merge-review-panel appears in implement_helper --help output."""
        helper_py = str(
            Path(__file__).resolve().parents[3]
            / "src"
            / "devforge"
            / "lib"
            / "implement_helper.py"
        )
        result = subprocess.run(
            [sys.executable, helper_py, "--help"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("merge-review-panel", result.stdout)


if __name__ == "__main__":
    unittest.main()
