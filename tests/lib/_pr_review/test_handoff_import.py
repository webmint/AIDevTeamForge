"""Tests for src/devforge/lib/_pr_review/_handoff_import.py.

Coverage:
  _scan_research_dir: glob discovery; empty dir; missing dir.
  _parse_handoff: valid handoff.json with all fields; missing optional fields;
    malformed JSON (fail-soft None); missing file (fail-soft None);
    dir name without expected date-slug format.
  _filter_by_ticket_text: substring match by ticket_text token; substring
    match by pr_title; no filter content returns all with matched_via="all";
    no match returns empty; short tokens below min length ignored.
  _excerpt_handoff: under cap unchanged; exactly at cap; over cap with marker.
  run (happy path): multi-handoff dir + state.json with ticket_text →
    filtered set in state.bundle["research_handoffs"].
  run (persistence): bundle["research_handoffs"] replaced on re-run;
    other bundle keys preserved.
  run (cap): 30 handoffs → capped to 20; sorted most-recent-first.
  run (no filter): no ticket_text + no pr_body → all returned with
    matched_via="all".
  run (no state.json → ValueError).
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

from _pr_review._handoff_import import (  # noqa: E402
    _excerpt_handoff,
    _filter_by_ticket_text,
    _parse_handoff,
    _scan_research_dir,
    _MAX_HANDOFFS,
    _EXCERPT_CHARS,
    run,
)
from _pr_review._state import PRReviewState, state_path  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers.
# ---------------------------------------------------------------------------


def _write_file(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)


def _make_state(tmpdir: str, pr_number: int = 1, **kwargs) -> str:
    """Write a PRReviewState to state.json and return the path."""
    abs_devforge = os.path.join(tmpdir, ".devforge")
    sp = state_path(abs_devforge, pr_number)
    os.makedirs(os.path.dirname(sp), exist_ok=True)
    state = PRReviewState(pr_number=pr_number, repo="acme/app", **kwargs)
    with open(sp, "w", encoding="utf-8") as fh:
        json.dump(dataclasses.asdict(state), fh, indent=2)
        fh.write("\n")
    return sp


def _make_handoff(research_dir: str, date_slug: str, mode: str = "bug", extra: dict = None) -> str:
    """Create a minimal handoff.json and return its path."""
    subdir = os.path.join(research_dir, date_slug)
    os.makedirs(subdir, exist_ok=True)
    data = {"schema_version": "1.0", "mode": mode, "verdict": "proceed"}
    if extra:
        data.update(extra)
    hf = os.path.join(subdir, "handoff.json")
    _write_file(hf, json.dumps(data, indent=2))
    return hf


# ---------------------------------------------------------------------------
# TestScanResearchDir.
# ---------------------------------------------------------------------------


class TestScanResearchDir(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_missing_research_dir_returns_empty(self):
        result = _scan_research_dir(self._tmp)
        self.assertEqual(result, [])

    def test_empty_research_dir_returns_empty(self):
        os.makedirs(os.path.join(self._tmp, "research"))
        result = _scan_research_dir(self._tmp)
        self.assertEqual(result, [])

    def test_discovers_handoff_json_files(self):
        research = os.path.join(self._tmp, "research")
        _make_handoff(research, "2026-05-01-auth-bug")
        result = _scan_research_dir(self._tmp)
        self.assertEqual(len(result), 1)
        self.assertTrue(result[0].endswith("handoff.json"))

    def test_discovers_multiple_handoff_files(self):
        research = os.path.join(self._tmp, "research")
        _make_handoff(research, "2026-05-01-alpha")
        _make_handoff(research, "2026-05-02-beta")
        _make_handoff(research, "2026-05-03-gamma")
        result = _scan_research_dir(self._tmp)
        self.assertEqual(len(result), 3)

    def test_dirs_without_handoff_json_skipped(self):
        research = os.path.join(self._tmp, "research")
        sub = os.path.join(research, "2026-05-01-no-handoff")
        os.makedirs(sub, exist_ok=True)
        _write_file(os.path.join(sub, "notes.md"), "notes")
        result = _scan_research_dir(self._tmp)
        self.assertEqual(result, [])

    def test_result_contains_absolute_paths(self):
        research = os.path.join(self._tmp, "research")
        _make_handoff(research, "2026-05-01-auth-bug")
        result = _scan_research_dir(self._tmp)
        self.assertTrue(os.path.isabs(result[0]))


# ---------------------------------------------------------------------------
# TestParseHandoff.
# ---------------------------------------------------------------------------


class TestParseHandoff(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._research = os.path.join(self._tmp, "research")

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_valid_handoff_returns_metadata(self):
        hf = _make_handoff(self._research, "2026-05-10-login-bug", mode="bug")
        result = _parse_handoff(hf)
        self.assertIsNotNone(result)
        self.assertEqual(result["date"], "2026-05-10")
        self.assertEqual(result["slug"], "login-bug")
        self.assertEqual(result["mode"], "bug")
        self.assertEqual(result["verdict"], "proceed")

    def test_path_field_matches_input(self):
        hf = _make_handoff(self._research, "2026-05-10-login-bug")
        result = _parse_handoff(hf)
        self.assertEqual(result["path"], hf)

    def test_missing_mode_field_defaults_to_empty(self):
        subdir = os.path.join(self._research, "2026-05-10-no-mode")
        os.makedirs(subdir, exist_ok=True)
        hf = os.path.join(subdir, "handoff.json")
        _write_file(hf, '{"schema_version": "1.0"}')
        result = _parse_handoff(hf)
        self.assertIsNotNone(result)
        self.assertEqual(result["mode"], "")

    def test_malformed_json_returns_none(self):
        subdir = os.path.join(self._research, "2026-05-10-broken")
        os.makedirs(subdir, exist_ok=True)
        hf = os.path.join(subdir, "handoff.json")
        _write_file(hf, "{bad json}")
        result = _parse_handoff(hf)
        self.assertIsNone(result)

    def test_missing_file_returns_none(self):
        result = _parse_handoff(os.path.join(self._tmp, "nonexistent.json"))
        self.assertIsNone(result)

    def test_dir_without_date_slug_format(self):
        subdir = os.path.join(self._research, "nondated-dir")
        os.makedirs(subdir, exist_ok=True)
        hf = os.path.join(subdir, "handoff.json")
        _write_file(hf, '{"mode": "bug"}')
        result = _parse_handoff(hf)
        self.assertIsNotNone(result)
        self.assertEqual(result["date"], "")
        self.assertEqual(result["slug"], "nondated-dir")

    def test_content_excerpt_present(self):
        hf = _make_handoff(self._research, "2026-05-10-test")
        result = _parse_handoff(hf)
        self.assertIn("content_excerpt", result)
        self.assertIsInstance(result["content_excerpt"], str)
        self.assertGreater(len(result["content_excerpt"]), 0)

    def test_content_excerpt_truncated_when_large(self):
        subdir = os.path.join(self._research, "2026-05-10-big")
        os.makedirs(subdir, exist_ok=True)
        hf = os.path.join(subdir, "handoff.json")
        # Build a valid JSON object large enough to exceed _EXCERPT_CHARS (5000).
        big_value = "a" * 6000
        _write_file(hf, json.dumps({"mode": "bug", "big_field": big_value}))
        result = _parse_handoff(hf)
        self.assertIsNotNone(result)
        self.assertTrue(result["content_excerpt"].endswith("... [truncated]"))

    def test_empty_json_file_returns_metadata_with_empty_fields(self):
        subdir = os.path.join(self._research, "2026-05-10-empty")
        os.makedirs(subdir, exist_ok=True)
        hf = os.path.join(subdir, "handoff.json")
        _write_file(hf, "{}")
        result = _parse_handoff(hf)
        self.assertIsNotNone(result)
        self.assertEqual(result["mode"], "")

    def test_verdict_falls_back_to_mode_when_verdict_absent(self):
        """handoff.json with mode but no verdict key -> verdict equals mode value."""
        subdir = os.path.join(self._research, "2026-05-10-mode-only")
        os.makedirs(subdir, exist_ok=True)
        hf = os.path.join(subdir, "handoff.json")
        # Older handoff shape: has 'mode' but no 'verdict'.
        _write_file(hf, json.dumps({"schema_version": "1.0", "mode": "bug"}))
        result = _parse_handoff(hf)
        self.assertIsNotNone(result)
        self.assertEqual(result["verdict"], "bug",
                         "verdict should fall back to mode value when verdict key absent")


# ---------------------------------------------------------------------------
# TestFilterByTicketText.
# ---------------------------------------------------------------------------


class TestFilterByTicketText(unittest.TestCase):
    def _make_handoff_meta(self, slug: str, mode: str = "bug") -> dict:
        return {
            "path": "/fake/{0}/handoff.json".format(slug),
            "date": "2026-05-01",
            "slug": slug,
            "verdict": "proceed",
            "mode": mode,
            "content_excerpt": "excerpt",
        }

    def test_empty_criteria_returns_all_with_matched_via_all(self):
        handoffs = [
            self._make_handoff_meta("auth-login"),
            self._make_handoff_meta("payment-fix"),
        ]
        result = _filter_by_ticket_text(handoffs, "", "")
        self.assertEqual(len(result), 2)
        for r in result:
            self.assertEqual(r["matched_via"], "all")

    def test_ticket_text_substring_match(self):
        handoffs = [
            self._make_handoff_meta("auth-login"),
            self._make_handoff_meta("payment-gateway"),
        ]
        result = _filter_by_ticket_text(handoffs, "auth login fix", "")
        slugs = [r["slug"] for r in result]
        self.assertIn("auth-login", slugs)
        self.assertNotIn("payment-gateway", slugs)

    def test_ticket_text_match_via_is_ticket_text_substring(self):
        handoffs = [self._make_handoff_meta("auth-login")]
        result = _filter_by_ticket_text(handoffs, "auth fix", "")
        self.assertEqual(result[0]["matched_via"], "ticket_text_substring")

    def test_pr_title_substring_match(self):
        handoffs = [
            self._make_handoff_meta("auth-refactor"),
            self._make_handoff_meta("billing-update"),
        ]
        result = _filter_by_ticket_text(handoffs, "", "Refactor auth module")
        slugs = [r["slug"] for r in result]
        self.assertIn("auth-refactor", slugs)
        self.assertNotIn("billing-update", slugs)

    def test_pr_title_match_via_is_title_substring(self):
        handoffs = [self._make_handoff_meta("auth-refactor")]
        result = _filter_by_ticket_text(handoffs, "", "Refactor auth module")
        self.assertEqual(result[0]["matched_via"], "title_substring")

    def test_ticket_text_takes_priority_over_title(self):
        handoffs = [self._make_handoff_meta("auth-bug")]
        result = _filter_by_ticket_text(handoffs, "auth ticket", "auth PR title")
        self.assertEqual(result[0]["matched_via"], "ticket_text_substring")

    def test_no_match_returns_empty(self):
        handoffs = [self._make_handoff_meta("xyz-unrelated")]
        result = _filter_by_ticket_text(handoffs, "auth token fix", "auth PR")
        self.assertEqual(result, [])

    def test_short_tokens_ignored(self):
        """Tokens shorter than _MIN_FILTER_TOKEN_LEN chars are ignored."""
        handoffs = [self._make_handoff_meta("auth-login")]
        # "au" is 2 chars → below minimum of 3.
        result = _filter_by_ticket_text(handoffs, "au", "")
        # No filter-qualifying tokens → treated as no filter → all returned.
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["matched_via"], "all")

    def test_case_insensitive_match(self):
        handoffs = [self._make_handoff_meta("auth-login")]
        result = _filter_by_ticket_text(handoffs, "AUTH LOGIN", "")
        self.assertEqual(len(result), 1)

    def test_empty_handoffs_list_returns_empty(self):
        result = _filter_by_ticket_text([], "auth fix", "Auth PR")
        self.assertEqual(result, [])


# ---------------------------------------------------------------------------
# TestExcerptHandoff.
# ---------------------------------------------------------------------------


class TestExcerptHandoff(unittest.TestCase):
    def test_under_cap_unchanged(self):
        content = "hello world"
        self.assertEqual(_excerpt_handoff(content, max_chars=100), content)

    def test_exactly_at_cap_no_truncation(self):
        content = "x" * 100
        result = _excerpt_handoff(content, max_chars=100)
        self.assertEqual(result, content)
        self.assertNotIn("truncated", result)

    def test_over_cap_truncated_with_marker(self):
        content = "y" * 200
        result = _excerpt_handoff(content, max_chars=100)
        self.assertTrue(result.endswith("... [truncated]"))
        self.assertEqual(len(result) - len("... [truncated]"), 100)

    def test_default_cap_is_5000(self):
        self.assertEqual(_EXCERPT_CHARS, 5000)

    def test_empty_string_unchanged(self):
        self.assertEqual(_excerpt_handoff(""), "")


# ---------------------------------------------------------------------------
# TestRunHappyPath.
# ---------------------------------------------------------------------------


class TestRunHappyPath(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._pr_number = 11
        self._sp = _make_state(
            self._tmp,
            self._pr_number,
            ticket_text="login auth issue",
        )
        self._research = os.path.join(self._tmp, "research")
        # Relevant handoff.
        _make_handoff(self._research, "2026-05-10-auth-login-fix", mode="bug")
        # Irrelevant handoff.
        _make_handoff(self._research, "2026-05-01-billing-update", mode="feature_addition")

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_run_returns_ok_status(self):
        result = run(self._tmp, self._pr_number)
        self.assertEqual(result["status"], "ok")

    def test_run_returns_pr_number(self):
        result = run(self._tmp, self._pr_number)
        self.assertEqual(result["pr_number"], self._pr_number)

    def test_run_returns_handoffs_found(self):
        result = run(self._tmp, self._pr_number)
        self.assertEqual(result["handoffs_found"], 2)

    def test_run_returns_handoffs_matched(self):
        result = run(self._tmp, self._pr_number)
        # "login" and "auth" match "auth-login-fix"; "billing" does not match.
        self.assertEqual(result["handoffs_matched"], 1)

    def test_filter_applied_when_ticket_text_present(self):
        result = run(self._tmp, self._pr_number)
        self.assertTrue(result["filter_applied"])

    def test_state_bundle_research_handoffs_written(self):
        run(self._tmp, self._pr_number)
        with open(self._sp, "r", encoding="utf-8") as fh:
            state = json.load(fh)
        self.assertIn("research_handoffs", state["bundle"])
        self.assertEqual(len(state["bundle"]["research_handoffs"]), 1)

    def test_matched_handoff_has_required_keys(self):
        run(self._tmp, self._pr_number)
        with open(self._sp, "r", encoding="utf-8") as fh:
            state = json.load(fh)
        h = state["bundle"]["research_handoffs"][0]
        for key in ("path", "date", "slug", "verdict", "mode", "matched_via", "content_excerpt"):
            self.assertIn(key, h, "handoff missing key: {0}".format(key))

    def test_matched_handoff_has_correct_slug(self):
        run(self._tmp, self._pr_number)
        with open(self._sp, "r", encoding="utf-8") as fh:
            state = json.load(fh)
        h = state["bundle"]["research_handoffs"][0]
        self.assertEqual(h["slug"], "auth-login-fix")

    def test_matched_via_ticket_text_substring(self):
        run(self._tmp, self._pr_number)
        with open(self._sp, "r", encoding="utf-8") as fh:
            state = json.load(fh)
        h = state["bundle"]["research_handoffs"][0]
        self.assertEqual(h["matched_via"], "ticket_text_substring")


# ---------------------------------------------------------------------------
# TestRunNoFilter.
# ---------------------------------------------------------------------------


class TestRunNoFilter(unittest.TestCase):
    """When state has no ticket_text and no pr_body, all handoffs are returned."""

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._pr_number = 22
        self._sp = _make_state(self._tmp, self._pr_number)  # no ticket_text
        self._research = os.path.join(self._tmp, "research")
        _make_handoff(self._research, "2026-05-01-alpha")
        _make_handoff(self._research, "2026-05-02-beta")

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_all_returned_when_no_filter(self):
        result = run(self._tmp, self._pr_number)
        self.assertEqual(result["handoffs_matched"], 2)

    def test_filter_not_applied_when_no_criteria(self):
        result = run(self._tmp, self._pr_number)
        self.assertFalse(result["filter_applied"])

    def test_matched_via_all_when_no_filter(self):
        run(self._tmp, self._pr_number)
        with open(self._sp, "r", encoding="utf-8") as fh:
            state = json.load(fh)
        for h in state["bundle"]["research_handoffs"]:
            self.assertEqual(h["matched_via"], "all")


# ---------------------------------------------------------------------------
# TestRunPersistence.
# ---------------------------------------------------------------------------


class TestRunPersistence(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._pr_number = 33
        self._sp = _make_state(self._tmp, self._pr_number)

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_existing_bundle_keys_preserved(self):
        """Non-research_handoffs keys in state.bundle are not erased."""
        with open(self._sp, "r", encoding="utf-8") as fh:
            state_dict = json.load(fh)
        state_dict["bundle"]["constitution_md_content"] = "preserved value"
        with open(self._sp, "w", encoding="utf-8") as fh:
            json.dump(state_dict, fh)

        run(self._tmp, self._pr_number)

        with open(self._sp, "r", encoding="utf-8") as fh:
            state_after = json.load(fh)
        self.assertEqual(
            state_after["bundle"]["constitution_md_content"], "preserved value"
        )

    def test_research_handoffs_replaced_on_rerun(self):
        """Re-running replaces research_handoffs — no merge."""
        research = os.path.join(self._tmp, "research")
        _make_handoff(research, "2026-05-10-alpha")

        # First run: 1 handoff.
        run(self._tmp, self._pr_number)
        with open(self._sp, "r", encoding="utf-8") as fh:
            count_after_first = len(json.load(fh)["bundle"]["research_handoffs"])

        # Second run: same files → same count (not doubled).
        run(self._tmp, self._pr_number)
        with open(self._sp, "r", encoding="utf-8") as fh:
            count_after_second = len(json.load(fh)["bundle"]["research_handoffs"])

        self.assertEqual(count_after_first, count_after_second)

    def test_state_fields_other_than_bundle_preserved(self):
        run(self._tmp, self._pr_number)
        with open(self._sp, "r", encoding="utf-8") as fh:
            state = json.load(fh)
        self.assertEqual(state["repo"], "acme/app")

    def test_no_state_json_raises_value_error(self):
        with self.assertRaises(ValueError) as ctx:
            run(self._tmp, 9999)
        self.assertIn("intake", str(ctx.exception))


# ---------------------------------------------------------------------------
# TestRunCap.
# ---------------------------------------------------------------------------


class TestRunCap(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._pr_number = 55
        self._sp = _make_state(self._tmp, self._pr_number)
        research = os.path.join(self._tmp, "research")
        # Create 30 handoff dirs (well above the cap of 20).
        for i in range(30):
            date = "2026-{0:02d}-{1:02d}".format((i % 12) + 1, (i % 28) + 1)
            slug = "topic-{0:03d}".format(i)
            _make_handoff(research, "{0}-{1}".format(date, slug))

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_cap_at_20(self):
        result = run(self._tmp, self._pr_number)
        self.assertEqual(result["handoffs_matched"], _MAX_HANDOFFS)
        self.assertEqual(_MAX_HANDOFFS, 20)

    def test_state_bundle_capped(self):
        run(self._tmp, self._pr_number)
        with open(self._sp, "r", encoding="utf-8") as fh:
            state = json.load(fh)
        self.assertEqual(len(state["bundle"]["research_handoffs"]), _MAX_HANDOFFS)

    def test_most_recent_first(self):
        run(self._tmp, self._pr_number)
        with open(self._sp, "r", encoding="utf-8") as fh:
            state = json.load(fh)
        handoffs = state["bundle"]["research_handoffs"]
        dates = [h["date"] for h in handoffs if h["date"]]
        # Dates should be in descending order.
        self.assertEqual(dates, sorted(dates, reverse=True))


# ---------------------------------------------------------------------------
# TestRunEmptyResearchDir.
# ---------------------------------------------------------------------------


class TestRunEmptyResearchDir(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._pr_number = 77
        self._sp = _make_state(self._tmp, self._pr_number)

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_no_research_dir_produces_empty_list(self):
        result = run(self._tmp, self._pr_number)
        self.assertEqual(result["handoffs_found"], 0)
        self.assertEqual(result["handoffs_matched"], 0)
        with open(self._sp, "r", encoding="utf-8") as fh:
            state = json.load(fh)
        self.assertEqual(state["bundle"]["research_handoffs"], [])

    def test_empty_research_dir_produces_empty_list(self):
        os.makedirs(os.path.join(self._tmp, "research"))
        result = run(self._tmp, self._pr_number)
        self.assertEqual(result["handoffs_found"], 0)


if __name__ == "__main__":
    unittest.main()
