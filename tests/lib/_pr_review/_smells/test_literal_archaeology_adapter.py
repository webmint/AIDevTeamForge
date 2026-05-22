"""Tests for src/devforge/lib/_pr_review/_smells/literal_archaeology_adapter.py.

Coverage:
    _classify_intent           — each intent pattern; default fallback
    _parse_blame_sha           — valid porcelain output, empty, malformed
    _extract_literals_with_locations — basic, multi-hunk, cap at _MAX_LITERALS_PER_PR
    run()                      — positive (placeholder→finding), negative (deliberate→no finding),
                                 multi-literal, cap, git binary missing, no target, empty diff
    Finding schema             — correct keys + evidence format
"""

from __future__ import annotations

import sys
import unittest
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch, MagicMock

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _pr_review._smells.literal_archaeology_adapter import (  # noqa: E402
    _MAX_LITERALS_PER_PR,
    _classify_intent,
    _extract_literals_with_locations,
    _git_blame_sha,
    _git_commit_subject,
    _parse_blame_sha,
    run,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_state(diff: str, target: str = "/fake/target") -> SimpleNamespace:
    return SimpleNamespace(diff=diff, target=target)


def _make_diff_with_literal(literal: str, file_path: str = "src/foo.py") -> str:
    """Build a minimal diff that adds one line containing the given literal."""
    return (
        "diff --git a/{path} b/{path}\n"
        "+++ b/{path}\n"
        "--- a/{path}\n"
        "@@ -1,0 +1,1 @@\n"
        "+LIMIT = {lit}\n"
    ).format(path=file_path, lit=literal)


# Exactly 40 hex chars for a valid SHA-1.
_SHA40 = "abc1234567890123456789012345678901234567"

PORCELAIN_BLAME_OUTPUT = (
    "{sha} 1 1 1\n"
    "author Test User\n"
    "author-mail <test@example.com>\n"
    "author-time 1700000000\n"
    "author-tz +0000\n"
    "committer Test User\n"
    "committer-mail <test@example.com>\n"
    "committer-time 1700000000\n"
    "committer-tz +0000\n"
    "summary TODO: adjust limit\n"
    "filename src/foo.py\n"
    "\tLIMIT = 365\n"
).format(sha=_SHA40)


# ---------------------------------------------------------------------------
# _classify_intent
# ---------------------------------------------------------------------------


class TestAddedLineRENoBlankCross(unittest.TestCase):
    """F3: blank added line (+\\n) must not cross-contaminate adjacent lines."""

    def test_blank_added_line_does_not_merge_with_next(self):
        from _pr_review._smells.literal_archaeology_adapter import _ADDED_LINE_RE
        diff_fragment = "+first_line\n+\n+second_line\n"
        matches = _ADDED_LINE_RE.findall(diff_fragment)
        self.assertIn("first_line", matches)
        self.assertIn("second_line", matches)
        for m in matches:
            self.assertNotIn("\n", m)


class TestClassifyIntent(unittest.TestCase):
    def test_placeholder_todo(self):
        self.assertEqual(_classify_intent("TODO: adjust limit", "f.py", "365"), "placeholder")

    def test_placeholder_fixme(self):
        self.assertEqual(_classify_intent("FIXME: wrong value", "f.py", "100"), "placeholder")

    def test_placeholder_tbd(self):
        self.assertEqual(_classify_intent("TBD: needs confirmation", "f.py", "0"), "placeholder")

    def test_placeholder_wip(self):
        self.assertEqual(_classify_intent("WIP changes", "f.py", "5"), "placeholder")

    def test_forgotten_fix_colon(self):
        self.assertEqual(_classify_intent("fix: typo", "f.py", "1"), "forgotten")

    def test_forgotten_chore_colon(self):
        self.assertEqual(_classify_intent("chore: update deps", "f.py", "2"), "forgotten")

    def test_forgotten_fix_scope_colon(self):
        """F4: fix(scope): must match forgotten."""
        self.assertEqual(_classify_intent("fix(orderflow): adjust limit", "f.py", "5"), "forgotten")

    def test_forgotten_chore_scope_colon(self):
        """F4: chore(scope): must match forgotten."""
        self.assertEqual(_classify_intent("chore(deps): bump version", "f.py", "3"), "forgotten")

    def test_migrated_port_pattern(self):
        self.assertEqual(_classify_intent("TICKET-1234 porting logic", "f.py", "7"), "migrated")

    def test_migrated_migrate_word(self):
        self.assertEqual(_classify_intent("migrate users to new schema", "f.py", "3"), "migrated")

    def test_deliberate_adjust(self):
        self.assertEqual(_classify_intent("adjust timeout for CI", "f.py", "30"), "deliberate")

    def test_deliberate_update_x_to(self):
        self.assertEqual(_classify_intent("update limit to 500", "f.py", "500"), "deliberate")

    def test_inherited_refactor(self):
        self.assertEqual(_classify_intent("refactor auth module", "f.py", "10"), "inherited-refactor")

    def test_generated_scaffold(self):
        self.assertEqual(_classify_intent("scaffold generated by tool", "f.py", "0"), "generated")

    def test_fallback_deliberate(self):
        """No pattern matches → defaults to 'deliberate'."""
        self.assertEqual(
            _classify_intent("add new feature to the system", "f.py", "42"),
            "deliberate",
        )

    def test_placeholder_case_insensitive(self):
        """Pattern matching is case-insensitive."""
        self.assertEqual(_classify_intent("todo: fix this", "f.py", "1"), "placeholder")


# ---------------------------------------------------------------------------
# _parse_blame_sha
# ---------------------------------------------------------------------------


class TestParseBlameSha(unittest.TestCase):
    def test_valid_porcelain_output(self):
        sha = _parse_blame_sha(PORCELAIN_BLAME_OUTPUT)
        self.assertEqual(sha, _SHA40)

    def test_empty_output_returns_none(self):
        self.assertIsNone(_parse_blame_sha(""))

    def test_short_sha_returns_none(self):
        output = "abc1234 1 1 1\nauthor Test\n"
        self.assertIsNone(_parse_blame_sha(output))


# ---------------------------------------------------------------------------
# _extract_literals_with_locations
# ---------------------------------------------------------------------------


class TestExtractLiteralsWithLocations(unittest.TestCase):
    def test_single_numeric_literal(self):
        diff = _make_diff_with_literal("365")
        results = _extract_literals_with_locations(diff)
        self.assertTrue(any(lit == "365" for lit, _, _ in results))

    def test_file_path_correct(self):
        diff = _make_diff_with_literal("42", "src/bar.py")
        results = _extract_literals_with_locations(diff)
        self.assertTrue(all(fp == "src/bar.py" for _, fp, _ in results))

    def test_empty_diff_returns_empty(self):
        self.assertEqual(_extract_literals_with_locations(""), [])

    def test_cap_at_max_literals(self):
        # Generate a diff with more than _MAX_LITERALS_PER_PR literals.
        # Each added line has one literal; we add 60 lines.
        lines = ["+LINE_{i} = {i}\n".format(i=i) for i in range(60)]
        diff = (
            "diff --git a/src/foo.py b/src/foo.py\n"
            "+++ b/src/foo.py\n"
            "@@ -1,0 +1,60 @@\n"
            + "".join(lines)
        )
        results = _extract_literals_with_locations(diff)
        self.assertLessEqual(len(results), _MAX_LITERALS_PER_PR)

    def test_removed_lines_not_extracted(self):
        diff = (
            "diff --git a/src/foo.py b/src/foo.py\n"
            "+++ b/src/foo.py\n"
            "@@ -1,1 +1,0 @@\n"
            "-LIMIT = 999\n"
        )
        results = _extract_literals_with_locations(diff)
        self.assertFalse(any(lit == "999" for lit, _, _ in results))


# ---------------------------------------------------------------------------
# run() — with subprocess mocking
# ---------------------------------------------------------------------------


class TestLiteralArchaeologyRun(unittest.TestCase):
    """Mocks _git_blame_sha and _git_commit_subject to avoid real git calls."""

    def setUp(self):
        self.diff = _make_diff_with_literal("365")
        self.target = "/fake/repo"

    @patch(
        "_pr_review._smells.literal_archaeology_adapter._git_commit_subject"
    )
    @patch(
        "_pr_review._smells.literal_archaeology_adapter._git_blame_sha"
    )
    def test_positive_placeholder_intent_fires(self, mock_blame, mock_subject):
        mock_blame.return_value = "abc1234" + "0" * 33  # 40 chars
        mock_subject.return_value = "TODO: adjust limit"

        state = _make_state(self.diff)
        findings = run(state)
        self.assertEqual(len(findings), 1)
        f = findings[0]
        self.assertEqual(f["name"], "literal_archaeology_adapter")
        self.assertEqual(f["severity"], "low")
        self.assertIn("intent=placeholder", f["evidence"])

    @patch(
        "_pr_review._smells.literal_archaeology_adapter._git_commit_subject"
    )
    @patch(
        "_pr_review._smells.literal_archaeology_adapter._git_blame_sha"
    )
    def test_negative_deliberate_intent_no_finding(self, mock_blame, mock_subject):
        mock_blame.return_value = "abc1234" + "0" * 33
        mock_subject.return_value = "adjust timeout for CI"

        state = _make_state(self.diff)
        findings = run(state)
        self.assertEqual(findings, [])

    @patch(
        "_pr_review._smells.literal_archaeology_adapter._git_commit_subject"
    )
    @patch(
        "_pr_review._smells.literal_archaeology_adapter._git_blame_sha"
    )
    def test_forgotten_intent_fires(self, mock_blame, mock_subject):
        mock_blame.return_value = "abc1234" + "0" * 33
        mock_subject.return_value = "fix: wrong constant"

        state = _make_state(self.diff)
        findings = run(state)
        self.assertEqual(len(findings), 1)
        self.assertIn("intent=forgotten", findings[0]["evidence"])

    @patch(
        "_pr_review._smells.literal_archaeology_adapter._git_commit_subject"
    )
    @patch(
        "_pr_review._smells.literal_archaeology_adapter._git_blame_sha"
    )
    def test_generated_intent_nit_severity(self, mock_blame, mock_subject):
        mock_blame.return_value = "abc1234" + "0" * 33
        mock_subject.return_value = "scaffold generated by tool"

        state = _make_state(self.diff)
        findings = run(state)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["severity"], "nit")

    @patch(
        "_pr_review._smells.literal_archaeology_adapter._git_blame_sha"
    )
    def test_git_blame_fails_no_finding(self, mock_blame):
        """git blame returns None → fail-soft, no finding."""
        mock_blame.return_value = None

        state = _make_state(self.diff)
        findings = run(state)
        self.assertEqual(findings, [])

    def test_empty_diff_no_finding(self):
        state = _make_state("")
        findings = run(state)
        self.assertEqual(findings, [])

    def test_no_target_no_finding(self):
        state = SimpleNamespace(diff=self.diff, target="")
        findings = run(state)
        self.assertEqual(findings, [])

    @patch(
        "_pr_review._smells.literal_archaeology_adapter._git_commit_subject"
    )
    @patch(
        "_pr_review._smells.literal_archaeology_adapter._git_blame_sha"
    )
    def test_multi_literal_multiple_findings(self, mock_blame, mock_subject):
        """Diff with 3 literals, all placeholder → 3 findings (or up to cap)."""
        mock_blame.return_value = "abc1234" + "0" * 33
        mock_subject.return_value = "TODO: fix all these"

        # Build diff with 3 different literals on 3 added lines.
        diff = (
            "diff --git a/src/foo.py b/src/foo.py\n"
            "+++ b/src/foo.py\n"
            "@@ -1,0 +1,3 @@\n"
            "+A = 10\n"
            "+B = 20\n"
            "+C = 30\n"
        )
        state = _make_state(diff)
        findings = run(state)
        # Each numeric literal fires; expect 3.
        self.assertEqual(len(findings), 3)

    @patch(
        "_pr_review._smells.literal_archaeology_adapter._git_commit_subject"
    )
    @patch(
        "_pr_review._smells.literal_archaeology_adapter._git_blame_sha"
    )
    def test_cap_50_literals_respected(self, mock_blame, mock_subject):
        """More than 50 literals in diff → only first 50 processed."""
        mock_blame.return_value = "abc1234" + "0" * 33
        mock_subject.return_value = "TODO: needs review"

        lines = ["+X_{i} = {i}\n".format(i=i) for i in range(60)]
        diff = (
            "diff --git a/src/foo.py b/src/foo.py\n"
            "+++ b/src/foo.py\n"
            "@@ -1,0 +1,60 @@\n"
            + "".join(lines)
        )
        state = _make_state(diff)
        findings = run(state)
        self.assertLessEqual(len(findings), _MAX_LITERALS_PER_PR)

    def test_finding_schema(self):
        """Validate finding has all required keys with correct formats."""
        with (
            patch(
                "_pr_review._smells.literal_archaeology_adapter._git_blame_sha",
                return_value="abc1234" + "0" * 33,
            ),
            patch(
                "_pr_review._smells.literal_archaeology_adapter._git_commit_subject",
                return_value="TODO: adjust limit",
            ),
        ):
            state = _make_state(self.diff)
            findings = run(state)

        self.assertEqual(len(findings), 1)
        f = findings[0]
        self.assertIn("name", f)
        self.assertIn("severity", f)
        self.assertIn("location", f)
        self.assertIn("evidence", f)
        self.assertIn(":", f["location"])  # "file:line" format
        self.assertIn("literal", f["evidence"])
        self.assertIn("intent=", f["evidence"])


# ---------------------------------------------------------------------------
# _git_blame_sha and _git_commit_subject (fail-soft via mock)
# ---------------------------------------------------------------------------


class TestGitSubprocessFailSoft(unittest.TestCase):
    """These test the fail-soft behaviour by checking that FileNotFoundError
    (git not in PATH) returns None rather than raising."""

    def test_blame_sha_file_not_found_returns_none(self):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            result = _git_blame_sha("src/foo.py", 1, "/fake/repo")
        self.assertIsNone(result)

    def test_blame_sha_timeout_returns_none(self):
        import subprocess as sp
        with patch("subprocess.run", side_effect=sp.TimeoutExpired(cmd="git", timeout=30)):
            result = _git_blame_sha("src/foo.py", 1, "/fake/repo")
        self.assertIsNone(result)

    def test_commit_subject_file_not_found_returns_none(self):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            result = _git_commit_subject("abc123" * 7, "/fake/repo")
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
