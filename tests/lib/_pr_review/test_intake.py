"""Tests for src/devforge/lib/_pr_review/_intake.py.

Coverage:
  run()                       — full happy path + error paths (subprocess mocked)
  _fetch_pr_view              — subprocess success + non-zero exit
  _fetch_pr_diff              — subprocess success + non-zero exit
  _extract_linked_issues      — short refs, full URLs, dedup, sort
  _issues_from_closing_refs   — structured field extraction
  _read_ticket_file           — read + missing-file error
  _write_state                — atomic write pattern (no stale .tmp)
"""

from __future__ import annotations

import dataclasses
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch, call

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _pr_review._intake import (  # noqa: E402
    _extract_commit_subjects,
    _extract_linked_issues,
    _fetch_pr_diff,
    _fetch_pr_view,
    _issues_from_closing_refs,
    _read_ticket_file,
    _write_state,
    run,
)
from _pr_review._state import PRReviewState, state_path  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers for building mock subprocess results.
# ---------------------------------------------------------------------------


def _mock_proc(stdout: str = "", returncode: int = 0, stderr: str = "") -> MagicMock:
    m = MagicMock()
    m.stdout = stdout
    m.returncode = returncode
    m.stderr = stderr
    return m


_SAMPLE_PR_VIEW = {
    "title": "Add spinner component",
    "body": "Fixes #123\nSee also https://github.com/acme/app/issues/456",
    "additions": 120,
    "deletions": 15,
    "baseRefName": "main",
    "headRefName": "feat/spinner",
    "files": [
        {"path": "src/Spinner.tsx"},
        {"path": "src/Spinner.css"},
        {"path": "tests/Spinner.test.tsx"},
    ],
    "state": "OPEN",
    "author": {"login": "dev1"},
    "url": "https://github.com/acme/app/pull/42",
    "number": 42,
    "closingIssuesReferences": [],
    "commits": [
        {"messageHeadline": "feat(spinner): add spinner component", "messageBody": ""},
        {"messageHeadline": "fix: correct animation timing", "messageBody": ""},
    ],
}

_SAMPLE_DIFF = (
    "diff --git a/src/Spinner.tsx b/src/Spinner.tsx\n"
    "index 0000000..1111111 100644\n"
    "+++ b/src/Spinner.tsx\n"
    "+export function Spinner() { return <div />; }\n"
)


# ---------------------------------------------------------------------------
# _fetch_pr_view
# ---------------------------------------------------------------------------


class TestFetchPrView(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_returns_parsed_json_on_success(self):
        payload = json.dumps(_SAMPLE_PR_VIEW)
        with patch("_pr_review._intake.subprocess.run") as mock_run:
            mock_run.return_value = _mock_proc(stdout=payload, returncode=0)
            result = _fetch_pr_view("acme/app", 42, self._tmp)
        self.assertEqual(result["number"], 42)
        self.assertEqual(result["title"], "Add spinner component")

    def test_raises_value_error_on_non_zero_exit(self):
        with patch("_pr_review._intake.subprocess.run") as mock_run:
            mock_run.return_value = _mock_proc(
                stdout="", returncode=1, stderr="no such PR"
            )
            with self.assertRaises(ValueError) as ctx:
                _fetch_pr_view("acme/app", 99, self._tmp)
        self.assertIn("1", str(ctx.exception))
        self.assertIn("no such PR", str(ctx.exception))

    def test_raises_value_error_on_bad_json(self):
        with patch("_pr_review._intake.subprocess.run") as mock_run:
            mock_run.return_value = _mock_proc(stdout="not-json", returncode=0)
            with self.assertRaises(ValueError):
                _fetch_pr_view("acme/app", 42, self._tmp)

    def test_passes_repo_and_pr_number_in_cmd(self):
        payload = json.dumps(_SAMPLE_PR_VIEW)
        with patch("_pr_review._intake.subprocess.run") as mock_run:
            mock_run.return_value = _mock_proc(stdout=payload)
            _fetch_pr_view("org/repo", 7, self._tmp)
        cmd = mock_run.call_args[0][0]
        self.assertIn("7", cmd)
        self.assertIn("org/repo", cmd)

    def test_cwd_passed_to_subprocess(self):
        payload = json.dumps(_SAMPLE_PR_VIEW)
        with patch("_pr_review._intake.subprocess.run") as mock_run:
            mock_run.return_value = _mock_proc(stdout=payload)
            _fetch_pr_view("acme/app", 42, self._tmp)
        cwd = (
            mock_run.call_args.kwargs.get("cwd")
            or mock_run.call_args[1].get("cwd")
        )
        self.assertEqual(cwd, self._tmp)


# ---------------------------------------------------------------------------
# _fetch_pr_diff
# ---------------------------------------------------------------------------


class TestFetchPrDiff(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_returns_diff_string_on_success(self):
        with patch("_pr_review._intake.subprocess.run") as mock_run:
            mock_run.return_value = _mock_proc(stdout=_SAMPLE_DIFF, returncode=0)
            result = _fetch_pr_diff("acme/app", 42, self._tmp)
        self.assertEqual(result, _SAMPLE_DIFF)

    def test_raises_value_error_on_non_zero_exit(self):
        with patch("_pr_review._intake.subprocess.run") as mock_run:
            mock_run.return_value = _mock_proc(
                stdout="", returncode=1, stderr="not authenticated"
            )
            with self.assertRaises(ValueError) as ctx:
                _fetch_pr_diff("acme/app", 42, self._tmp)
        self.assertIn("not authenticated", str(ctx.exception))

    def test_passes_repo_and_pr_number_in_cmd(self):
        with patch("_pr_review._intake.subprocess.run") as mock_run:
            mock_run.return_value = _mock_proc(stdout="diff text")
            _fetch_pr_diff("my/repo", 3, self._tmp)
        cmd = mock_run.call_args[0][0]
        self.assertIn("3", cmd)
        self.assertIn("my/repo", cmd)

    def test_empty_diff_returned_as_is(self):
        """Some PRs legitimately have no diff (e.g. merge commit only)."""
        with patch("_pr_review._intake.subprocess.run") as mock_run:
            mock_run.return_value = _mock_proc(stdout="", returncode=0)
            result = _fetch_pr_diff("acme/app", 1, self._tmp)
        self.assertEqual(result, "")


# ---------------------------------------------------------------------------
# _extract_linked_issues
# ---------------------------------------------------------------------------


class TestExtractLinkedIssues(unittest.TestCase):
    def test_empty_body_returns_empty_list(self):
        self.assertEqual(_extract_linked_issues("", "acme/app"), [])

    def test_none_body_returns_empty_list(self):
        # Defensive — body may be None from gh output.
        self.assertEqual(_extract_linked_issues(None, "acme/app"), [])  # type: ignore[arg-type]

    def test_short_ref_extracted_and_expanded(self):
        body = "Fixes #123"
        result = _extract_linked_issues(body, "acme/app")
        self.assertEqual(result, ["https://github.com/acme/app/issues/123"])

    def test_multiple_short_refs(self):
        body = "Closes #456, addresses #123"
        result = _extract_linked_issues(body, "acme/app")
        # Should be sorted ascending by number.
        self.assertEqual(result, [
            "https://github.com/acme/app/issues/123",
            "https://github.com/acme/app/issues/456",
        ])

    def test_full_url_extracted(self):
        body = "See https://github.com/foo/bar/issues/789"
        result = _extract_linked_issues(body, "acme/app")
        self.assertIn("https://github.com/foo/bar/issues/789", result)

    def test_deduplication_short_ref(self):
        body = "Fixes #123 and also #123"
        result = _extract_linked_issues(body, "acme/app")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], "https://github.com/acme/app/issues/123")

    def test_deduplication_full_url(self):
        body = (
            "https://github.com/acme/app/issues/99 "
            "and https://github.com/acme/app/issues/99"
        )
        result = _extract_linked_issues(body, "acme/app")
        self.assertEqual(len(result), 1)

    def test_sort_ascending_by_number(self):
        body = "#456 then #123"
        result = _extract_linked_issues(body, "acme/app")
        numbers = [int(url.rsplit("/", 1)[-1]) for url in result]
        self.assertEqual(numbers, sorted(numbers))

    def test_no_false_positive_in_normal_text(self):
        """Text without issue refs should produce empty list."""
        body = "This PR refactors the spinner component for performance."
        result = _extract_linked_issues(body, "acme/app")
        self.assertEqual(result, [])

    def test_mixed_short_and_full_url_deduped(self):
        """#123 and matching full URL should be deduped to one entry."""
        body = "Fixes #123 and https://github.com/acme/app/issues/123"
        result = _extract_linked_issues(body, "acme/app")
        self.assertEqual(len(result), 1)

    def test_short_ref_format_is_full_url(self):
        """Short refs are expanded to https://github.com/<repo>/issues/<N>."""
        body = "#7"
        result = _extract_linked_issues(body, "owner/name")
        self.assertTrue(result[0].startswith("https://github.com/"))
        self.assertIn("/issues/7", result[0])

    def test_cross_repo_same_number_not_deduped(self):
        """Cross-repo full URL and same-number short ref are distinct entries.

        Body has https://github.com/foo/other/issues/123 (different repo) AND
        #123 (expands to acme/app/issues/123) — these are different URLs and
        must both appear in the result. Old dedup-by-number would drop the
        short ref because 123 was already 'seen'.
        """
        body = "See https://github.com/foo/other/issues/123, Fixes #123"
        result = _extract_linked_issues(body, "acme/app")
        self.assertEqual(len(result), 2, "Expected 2 distinct issue URLs, got: {0}".format(result))
        self.assertIn("https://github.com/foo/other/issues/123", result)
        self.assertIn("https://github.com/acme/app/issues/123", result)


# ---------------------------------------------------------------------------
# _issues_from_closing_refs
# ---------------------------------------------------------------------------


class TestIssuesFromClosingRefs(unittest.TestCase):
    def test_empty_list_returns_empty(self):
        self.assertEqual(_issues_from_closing_refs([], "acme/app"), [])

    def test_single_ref_extracted(self):
        refs = [{"url": "https://github.com/acme/app/issues/10", "number": 10}]
        result = _issues_from_closing_refs(refs, "acme/app")
        self.assertEqual(result, ["https://github.com/acme/app/issues/10"])

    def test_multiple_refs_sorted(self):
        refs = [
            {"url": "https://github.com/acme/app/issues/30"},
            {"url": "https://github.com/acme/app/issues/5"},
        ]
        result = _issues_from_closing_refs(refs, "acme/app")
        self.assertEqual(result, [
            "https://github.com/acme/app/issues/5",
            "https://github.com/acme/app/issues/30",
        ])

    def test_deduped(self):
        refs = [
            {"url": "https://github.com/acme/app/issues/10"},
            {"url": "https://github.com/acme/app/issues/10"},
        ]
        result = _issues_from_closing_refs(refs, "acme/app")
        self.assertEqual(len(result), 1)

    def test_missing_url_field_skipped(self):
        refs = [{"number": 10}]  # no 'url' key
        result = _issues_from_closing_refs(refs, "acme/app")
        self.assertEqual(result, [])


# ---------------------------------------------------------------------------
# _extract_commit_subjects
# ---------------------------------------------------------------------------


class TestExtractCommitSubjects(unittest.TestCase):
    def test_empty_list_returns_empty(self):
        self.assertEqual(_extract_commit_subjects([]), [])

    def test_single_commit_returns_subject(self):
        commits = [{"messageHeadline": "feat: add spinner", "messageBody": ""}]
        result = _extract_commit_subjects(commits)
        self.assertEqual(result, ["feat: add spinner"])

    def test_multiple_commits_preserves_order(self):
        commits = [
            {"messageHeadline": "feat: first", "messageBody": ""},
            {"messageHeadline": "fix: second", "messageBody": ""},
            {"messageHeadline": "chore: third", "messageBody": ""},
        ]
        result = _extract_commit_subjects(commits)
        self.assertEqual(result, ["feat: first", "fix: second", "chore: third"])

    def test_fallback_to_message_field_when_headline_absent(self):
        """If messageHeadline is absent, fall back to first line of message."""
        commits = [{"message": "fix: spinner on refresh\n\nMore details here."}]
        result = _extract_commit_subjects(commits)
        self.assertEqual(result, ["fix: spinner on refresh"])

    def test_empty_messageHeadline_uses_message_fallback(self):
        commits = [{"messageHeadline": "", "message": "docs: update README\n"}]
        result = _extract_commit_subjects(commits)
        self.assertEqual(result, ["docs: update README"])

    def test_commit_with_no_subject_skipped(self):
        """Commits with no messageHeadline AND no message are excluded."""
        commits = [
            {"messageHeadline": "feat: real commit"},
            {},  # No subject fields at all.
        ]
        result = _extract_commit_subjects(commits)
        self.assertEqual(result, ["feat: real commit"])

    def test_empty_string_both_fields_skipped(self):
        commits = [{"messageHeadline": "", "message": ""}]
        result = _extract_commit_subjects(commits)
        self.assertEqual(result, [])


# ---------------------------------------------------------------------------
# _read_ticket_file
# ---------------------------------------------------------------------------


class TestReadTicketFile(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_reads_utf8_content(self):
        path = os.path.join(self._tmp, "ticket.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write("Update the spinner delay to 200ms.")
        result = _read_ticket_file(path)
        self.assertEqual(result, "Update the spinner delay to 200ms.")

    def test_missing_file_raises_value_error(self):
        with self.assertRaises(ValueError) as ctx:
            _read_ticket_file("/nonexistent/path/ticket.txt")
        self.assertIn("not found", str(ctx.exception))

    def test_empty_file_returns_empty_string(self):
        path = os.path.join(self._tmp, "empty.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write("")
        result = _read_ticket_file(path)
        self.assertEqual(result, "")

    def test_multiline_content_preserved(self):
        content = "Line 1\nLine 2\nLine 3\n"
        path = os.path.join(self._tmp, "multi.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        result = _read_ticket_file(path)
        self.assertEqual(result, content)


# ---------------------------------------------------------------------------
# _write_state
# ---------------------------------------------------------------------------


class TestWriteState(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _make_state(self, pr_number: int = 1) -> PRReviewState:
        return PRReviewState(
            pr_number=pr_number,
            repo="acme/app",
            diff=_SAMPLE_DIFF,
            pr_body="Fixes #1",
            linked_issues=["https://github.com/acme/app/issues/1"],
            ticket_text="Update spinner",
        )

    def test_writes_valid_json(self):
        path = os.path.join(self._tmp, "state.json")
        _write_state(path, self._make_state())
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["pr_number"], 1)
        self.assertEqual(data["repo"], "acme/app")

    def test_no_stale_tmp_files(self):
        """After a successful write, no .tmp file remains in the directory."""
        path = os.path.join(self._tmp, "state.json")
        _write_state(path, self._make_state())
        tmp_files = [
            f for f in os.listdir(self._tmp) if f.endswith(".tmp.json")
        ]
        self.assertEqual(tmp_files, [])

    def test_overwrites_existing_file(self):
        path = os.path.join(self._tmp, "state.json")
        _write_state(path, self._make_state(pr_number=1))
        _write_state(path, self._make_state(pr_number=2))
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["pr_number"], 2)

    def test_state_has_all_dataclass_fields(self):
        path = os.path.join(self._tmp, "state.json")
        state = self._make_state()
        _write_state(path, state)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Every field in the dataclass must appear in the JSON.
        expected_keys = set(f.name for f in dataclasses.fields(PRReviewState))
        self.assertEqual(set(data.keys()), expected_keys)


# ---------------------------------------------------------------------------
# run() — subprocess mocked.
# ---------------------------------------------------------------------------


def _make_run_mocks(view_payload=None, diff_text=None, returncode=0, stderr=""):
    """Return a side_effect function for patching subprocess.run.

    First call → pr view JSON; second call → pr diff text.
    """
    view_json = json.dumps(view_payload or _SAMPLE_PR_VIEW)
    diff = diff_text if diff_text is not None else _SAMPLE_DIFF

    calls = [0]

    def _side_effect(cmd, **kwargs):
        idx = calls[0]
        calls[0] += 1
        if idx == 0:
            return _mock_proc(stdout=view_json, returncode=returncode, stderr=stderr)
        return _mock_proc(stdout=diff, returncode=returncode, stderr=stderr)

    return _side_effect


class TestRun(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_happy_path_state_file_created(self):
        with patch("_pr_review._intake.subprocess.run", side_effect=_make_run_mocks()):
            run(target=self._tmp, pr_number=42, repo="acme/app")
        sp = state_path(os.path.join(self._tmp, ".devforge"), 42)
        self.assertTrue(os.path.isfile(sp), "state.json not created at {0}".format(sp))

    def test_state_file_path_structure(self):
        """State file is at <target>/.devforge/pr-reviews/<pr>/state.json."""
        with patch("_pr_review._intake.subprocess.run", side_effect=_make_run_mocks()):
            result = run(target=self._tmp, pr_number=42, repo="acme/app")
        expected_sp = state_path(os.path.join(self._tmp, ".devforge"), 42)
        self.assertEqual(result["state_path"], expected_sp)

    def test_state_path_in_output_is_absolute(self):
        with patch("_pr_review._intake.subprocess.run", side_effect=_make_run_mocks()):
            result = run(target=self._tmp, pr_number=42, repo="acme/app")
        self.assertTrue(os.path.isabs(result["state_path"]))

    def test_directory_created_if_missing(self):
        """The pr-reviews/<N>/ directory is created when absent."""
        pr_dir = os.path.join(self._tmp, ".devforge", "pr-reviews", "42")
        self.assertFalse(os.path.isdir(pr_dir))
        with patch("_pr_review._intake.subprocess.run", side_effect=_make_run_mocks()):
            run(target=self._tmp, pr_number=42, repo="acme/app")
        self.assertTrue(os.path.isdir(pr_dir))

    def test_output_schema_keys(self):
        """Returned dict has exactly the documented keys."""
        expected_keys = {
            "status",
            "state_path",
            "pr_number",
            "repo",
            "files_changed",
            "additions",
            "deletions",
            "title",
            "ticket_text_length",
        }
        with patch("_pr_review._intake.subprocess.run", side_effect=_make_run_mocks()):
            result = run(target=self._tmp, pr_number=42, repo="acme/app")
        self.assertEqual(set(result.keys()), expected_keys)

    def test_output_status_is_ok(self):
        with patch("_pr_review._intake.subprocess.run", side_effect=_make_run_mocks()):
            result = run(target=self._tmp, pr_number=42, repo="acme/app")
        self.assertEqual(result["status"], "ok")

    def test_output_files_changed_count(self):
        with patch("_pr_review._intake.subprocess.run", side_effect=_make_run_mocks()):
            result = run(target=self._tmp, pr_number=42, repo="acme/app")
        # _SAMPLE_PR_VIEW has 3 files.
        self.assertEqual(result["files_changed"], 3)

    def test_output_additions_deletions(self):
        with patch("_pr_review._intake.subprocess.run", side_effect=_make_run_mocks()):
            result = run(target=self._tmp, pr_number=42, repo="acme/app")
        self.assertEqual(result["additions"], 120)
        self.assertEqual(result["deletions"], 15)

    def test_output_title(self):
        with patch("_pr_review._intake.subprocess.run", side_effect=_make_run_mocks()):
            result = run(target=self._tmp, pr_number=42, repo="acme/app")
        self.assertEqual(result["title"], "Add spinner component")

    def test_ticket_text_inline(self):
        with patch("_pr_review._intake.subprocess.run", side_effect=_make_run_mocks()):
            result = run(
                target=self._tmp, pr_number=42, repo="acme/app",
                ticket_text="Update spinner delay"
            )
        self.assertEqual(result["ticket_text_length"], len("Update spinner delay"))
        sp = state_path(os.path.join(self._tmp, ".devforge"), 42)
        with open(sp, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["ticket_text"], "Update spinner delay")

    def test_ticket_text_default_empty(self):
        with patch("_pr_review._intake.subprocess.run", side_effect=_make_run_mocks()):
            result = run(target=self._tmp, pr_number=42, repo="acme/app")
        self.assertEqual(result["ticket_text_length"], 0)
        sp = state_path(os.path.join(self._tmp, ".devforge"), 42)
        with open(sp, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["ticket_text"], "")

    def test_pr_not_found_raises_value_error(self):
        """gh pr view non-zero exit raises ValueError."""
        with patch("_pr_review._intake.subprocess.run") as mock_run:
            mock_run.return_value = _mock_proc(
                stdout="", returncode=1, stderr="pull request not found"
            )
            with self.assertRaises(ValueError) as ctx:
                run(target=self._tmp, pr_number=99, repo="acme/app")
        self.assertIn("pull request not found", str(ctx.exception))

    def test_gh_not_authenticated_raises_value_error(self):
        """gh auth failure (non-zero exit) raises ValueError with helpful message."""
        with patch("_pr_review._intake.subprocess.run") as mock_run:
            mock_run.return_value = _mock_proc(
                stdout="", returncode=4, stderr="To authenticate, run: gh auth login"
            )
            with self.assertRaises(ValueError) as ctx:
                run(target=self._tmp, pr_number=42, repo="acme/app")
        self.assertIn("gh auth login", str(ctx.exception))

    def test_linked_issues_from_closing_refs_used_when_present(self):
        """closingIssuesReferences is used when non-empty."""
        view = dict(_SAMPLE_PR_VIEW)
        view["closingIssuesReferences"] = [
            {"url": "https://github.com/acme/app/issues/55", "number": 55},
        ]
        with patch("_pr_review._intake.subprocess.run", side_effect=_make_run_mocks(view_payload=view)):
            run(target=self._tmp, pr_number=42, repo="acme/app")
        sp = state_path(os.path.join(self._tmp, ".devforge"), 42)
        with open(sp, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn("https://github.com/acme/app/issues/55", data["linked_issues"])

    def test_linked_issues_fallback_to_body_when_closing_refs_empty(self):
        """Falls back to body regex when closingIssuesReferences is empty."""
        view = dict(_SAMPLE_PR_VIEW)
        view["closingIssuesReferences"] = []
        view["body"] = "Fixes #123"
        with patch("_pr_review._intake.subprocess.run", side_effect=_make_run_mocks(view_payload=view)):
            run(target=self._tmp, pr_number=42, repo="acme/app")
        sp = state_path(os.path.join(self._tmp, ".devforge"), 42)
        with open(sp, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn("https://github.com/acme/app/issues/123", data["linked_issues"])

    def test_state_file_contains_diff(self):
        with patch("_pr_review._intake.subprocess.run", side_effect=_make_run_mocks()):
            run(target=self._tmp, pr_number=42, repo="acme/app")
        sp = state_path(os.path.join(self._tmp, ".devforge"), 42)
        with open(sp, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["diff"], _SAMPLE_DIFF)

    def test_state_file_contains_pr_body(self):
        with patch("_pr_review._intake.subprocess.run", side_effect=_make_run_mocks()):
            run(target=self._tmp, pr_number=42, repo="acme/app")
        sp = state_path(os.path.join(self._tmp, ".devforge"), 42)
        with open(sp, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["pr_body"], _SAMPLE_PR_VIEW["body"])

    def test_forge_tier_left_at_default(self):
        """intake does NOT populate forge_tier; it stays at default 'none'."""
        with patch("_pr_review._intake.subprocess.run", side_effect=_make_run_mocks()):
            run(target=self._tmp, pr_number=42, repo="acme/app")
        sp = state_path(os.path.join(self._tmp, ".devforge"), 42)
        with open(sp, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["forge_tier"], "none")

    def test_commit_subjects_populated_from_commits_field(self):
        """commit_subjects is populated from the commits list in gh pr view output."""
        with patch("_pr_review._intake.subprocess.run", side_effect=_make_run_mocks()):
            run(target=self._tmp, pr_number=42, repo="acme/app")
        sp = state_path(os.path.join(self._tmp, ".devforge"), 42)
        with open(sp, "r", encoding="utf-8") as f:
            data = json.load(f)
        # _SAMPLE_PR_VIEW has 2 commits.
        self.assertEqual(data["commit_subjects"], [
            "feat(spinner): add spinner component",
            "fix: correct animation timing",
        ])

    def test_commit_subjects_empty_when_no_commits_field(self):
        """When the gh response has no commits field, commit_subjects is []."""
        view = dict(_SAMPLE_PR_VIEW)
        del view["commits"]
        with patch("_pr_review._intake.subprocess.run",
                   side_effect=_make_run_mocks(view_payload=view)):
            run(target=self._tmp, pr_number=42, repo="acme/app")
        sp = state_path(os.path.join(self._tmp, ".devforge"), 42)
        with open(sp, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["commit_subjects"], [])

    def test_no_stale_tmp_file_after_write(self):
        """No .tmp.json file remains after successful run."""
        with patch("_pr_review._intake.subprocess.run", side_effect=_make_run_mocks()):
            run(target=self._tmp, pr_number=42, repo="acme/app")
        pr_dir = os.path.join(self._tmp, ".devforge", "pr-reviews", "42")
        tmp_files = [f for f in os.listdir(pr_dir) if f.endswith(".tmp.json")]
        self.assertEqual(tmp_files, [])

    def test_target_relative_resolved_to_absolute_in_state_path(self):
        """Even a relative target produces an absolute state_path in output."""
        # Use cwd-relative path by pointing at a subdir of tmp.
        # We create the subdir so the path is valid.
        sub = os.path.join(self._tmp, "sub")
        os.makedirs(sub)
        # We need to patch cwd to be self._tmp so that a relative "sub" resolves.
        original_cwd = os.getcwd()
        try:
            os.chdir(self._tmp)
            with patch("_pr_review._intake.subprocess.run", side_effect=_make_run_mocks()):
                result = run(target="sub", pr_number=1, repo="acme/app")
            self.assertTrue(os.path.isabs(result["state_path"]))
        finally:
            os.chdir(original_cwd)

    def test_custom_devforge_dir(self):
        """devforge_dir parameter is respected; state file placed accordingly."""
        custom_dir = ".custom-forge"
        with patch("_pr_review._intake.subprocess.run", side_effect=_make_run_mocks()):
            result = run(
                target=self._tmp, pr_number=5, repo="acme/app",
                devforge_dir=custom_dir
            )
        expected_sp = state_path(os.path.join(self._tmp, custom_dir), 5)
        self.assertEqual(result["state_path"], expected_sp)
        self.assertTrue(os.path.isfile(expected_sp))


class TestRunIdempotent(unittest.TestCase):
    """Re-invoking run() overwrites the existing state file without error."""

    def setUp(self):
        self._tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_second_invocation_overwrites_state(self):
        with patch("_pr_review._intake.subprocess.run", side_effect=_make_run_mocks()):
            run(target=self._tmp, pr_number=1, repo="acme/app", ticket_text="first")
        view2 = dict(_SAMPLE_PR_VIEW)
        view2["title"] = "Updated title"
        with patch("_pr_review._intake.subprocess.run", side_effect=_make_run_mocks(view_payload=view2)):
            result = run(target=self._tmp, pr_number=1, repo="acme/app", ticket_text="second")
        sp = state_path(os.path.join(self._tmp, ".devforge"), 1)
        with open(sp, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["ticket_text"], "second")
        self.assertEqual(result["title"], "Updated title")


if __name__ == "__main__":
    unittest.main()
