"""Tests for src/devforge/lib/_pr_review/_handoff_import.py.

Coverage:
  _scan_specs_dir: glob discovery of research-handoff.json /
    discover-handoff.json under specs/*/; empty dir; missing dir; mixed
    kinds in one specs/ tree.
  _parse_handoff: valid research-handoff.json with all fields; valid
    discover-handoff.json (nested discovery_block.verdict extraction);
    missing optional fields; malformed JSON (fail-soft None); missing
    file (fail-soft None); dir name without the NNN-slug shape.
  _filter_by_ticket_text: substring match by ticket_text token; substring
    match by pr_title; no filter content returns all with matched_via="all";
    no match returns empty; short tokens below min length ignored.
  _excerpt_handoff: under cap unchanged; exactly at cap; over cap with marker.
  run (happy path): multi-handoff specs/ tree + state.json with ticket_text →
    filtered set in state.bundle["research_handoffs"].
  run (persistence): bundle["research_handoffs"] replaced on re-run;
    other bundle keys preserved.
  run (cap): 30 handoffs → capped to 20; sorted most-recent-first.
  run (no filter): no ticket_text + no pr_body → all returned with
    matched_via="all".
  run (no state.json → ValueError).

68-INTAKE-OWNS-FEATURE-DIR-PLAN.md Phase 5 re-point: fixtures write
specs/NNN-slug/{research-handoff.json,discover-handoff.json} — the D2/D7
unified layout — not the retired research/<date>-slug>/handoff.json shape.
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
    _scan_specs_dir,
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


def _make_research_handoff(
    specs_dir: str,
    feature_dir: str,
    mode: str = "bug",
    completed_at: str = "2026-05-10T12:00:00+00:00",
    extra: dict = None,
) -> str:
    """Create a minimal specs/<feature_dir>/research-handoff.json and return its path."""
    subdir = os.path.join(specs_dir, feature_dir)
    os.makedirs(subdir, exist_ok=True)
    data = {
        "schema_version": "1.0",
        "mode": mode,
        "research_completed_at": completed_at,
    }
    if extra:
        data.update(extra)
    hf = os.path.join(subdir, "research-handoff.json")
    _write_file(hf, json.dumps(data, indent=2))
    return hf


def _make_discover_handoff(
    specs_dir: str,
    feature_dir: str,
    verdict: str = "Worth pursuing",
    completed_at: str = "2026-05-10T12:00:00+00:00",
    extra: dict = None,
) -> str:
    """Create a minimal specs/<feature_dir>/discover-handoff.json and return its path."""
    subdir = os.path.join(specs_dir, feature_dir)
    os.makedirs(subdir, exist_ok=True)
    data = {
        "schema_version": "1.0",
        "handoff_kind": "discover",
        "discover_completed_at": completed_at,
        "discovery_block": {"verdict": verdict},
    }
    if extra:
        data.update(extra)
    hf = os.path.join(subdir, "discover-handoff.json")
    _write_file(hf, json.dumps(data, indent=2))
    return hf


# ---------------------------------------------------------------------------
# TestScanSpecsDir.
# ---------------------------------------------------------------------------


class TestScanSpecsDir(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_missing_specs_dir_returns_empty(self):
        result = _scan_specs_dir(self._tmp)
        self.assertEqual(result, [])

    def test_empty_specs_dir_returns_empty(self):
        os.makedirs(os.path.join(self._tmp, "specs"))
        result = _scan_specs_dir(self._tmp)
        self.assertEqual(result, [])

    def test_discovers_research_handoff_json(self):
        specs = os.path.join(self._tmp, "specs")
        _make_research_handoff(specs, "001-auth-bug")
        result = _scan_specs_dir(self._tmp)
        self.assertEqual(len(result), 1)
        self.assertTrue(result[0].endswith("research-handoff.json"))

    def test_discovers_discover_handoff_json(self):
        specs = os.path.join(self._tmp, "specs")
        _make_discover_handoff(specs, "001-new-widget")
        result = _scan_specs_dir(self._tmp)
        self.assertEqual(len(result), 1)
        self.assertTrue(result[0].endswith("discover-handoff.json"))

    def test_discovers_both_kinds_in_same_specs_tree(self):
        specs = os.path.join(self._tmp, "specs")
        _make_research_handoff(specs, "001-alpha")
        _make_discover_handoff(specs, "002-beta")
        result = _scan_specs_dir(self._tmp)
        self.assertEqual(len(result), 2)

    def test_discovers_multiple_handoff_files(self):
        specs = os.path.join(self._tmp, "specs")
        _make_research_handoff(specs, "001-alpha")
        _make_research_handoff(specs, "002-beta")
        _make_research_handoff(specs, "003-gamma")
        result = _scan_specs_dir(self._tmp)
        self.assertEqual(len(result), 3)

    def test_feature_dirs_without_intake_handoffs_skipped(self):
        specs = os.path.join(self._tmp, "specs")
        sub = os.path.join(specs, "001-no-handoff")
        os.makedirs(sub, exist_ok=True)
        _write_file(os.path.join(sub, "spec.md"), "# spec")
        result = _scan_specs_dir(self._tmp)
        self.assertEqual(result, [])

    def test_feature_dir_with_spec_md_still_scanned(self):
        """Unlike /specify's find-handoffs, a completed feature (spec.md
        present) is NOT filtered out — pr-review wants historical context
        regardless of completion state."""
        specs = os.path.join(self._tmp, "specs")
        _make_research_handoff(specs, "001-done-feature")
        _write_file(os.path.join(specs, "001-done-feature", "spec.md"), "# spec")
        result = _scan_specs_dir(self._tmp)
        self.assertEqual(len(result), 1)

    def test_result_contains_absolute_paths(self):
        specs = os.path.join(self._tmp, "specs")
        _make_research_handoff(specs, "001-auth-bug")
        result = _scan_specs_dir(self._tmp)
        self.assertTrue(os.path.isabs(result[0]))

    def test_old_layout_research_dir_not_scanned(self):
        """D3 clean cut: a pre-migration top-level research/ dir is invisible."""
        old_research = os.path.join(self._tmp, "research", "2026-05-01-old-topic")
        os.makedirs(old_research, exist_ok=True)
        _write_file(os.path.join(old_research, "handoff.json"), '{"mode": "bug"}')
        result = _scan_specs_dir(self._tmp)
        self.assertEqual(result, [])


# ---------------------------------------------------------------------------
# TestScanSpecsDirAccessorMigration (91-FEATURE-DIR-IDENTITY-AND-
# PROVENANCE-PLAN.md Phase 1 -- _scan_specs_dir migrated onto
# _shared/feature_alloc.py's find_feature_dirs_with).
# ---------------------------------------------------------------------------


class TestScanSpecsDirAccessorMigration(unittest.TestCase):
    """Pins the legacy shape unchanged and proves the forward-compat
    payoff (a Phase-3 specs/YYYY/MM/TICKET/ dir is now also found, even
    though no writer produces that shape yet)."""

    def setUp(self):
        self._tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_legacy_shape_still_resolves(self):
        specs = os.path.join(self._tmp, "specs")
        hf = _make_research_handoff(specs, "001-auth-bug")
        result = _scan_specs_dir(self._tmp)
        self.assertEqual(result, [hf])

    def test_new_shape_tree_also_found(self):
        """Forward-compat payoff: a Phase-3-shaped
        specs/YYYY/MM/TICKET/research-handoff.json is ALSO found, even
        though no writer produces this shape yet."""
        specs = os.path.join(self._tmp, "specs")
        feature_dir = "2026/08/PROJ-123"
        hf = _make_research_handoff(specs, feature_dir)
        result = _scan_specs_dir(self._tmp)
        self.assertEqual(result, [hf])

    def test_both_kinds_in_same_new_shape_dir_both_found(self):
        """A single new-shape feature dir carrying BOTH
        research-handoff.json AND discover-handoff.json (mirrors
        find-handoffs' equivalent legacy-shape test) surfaces both hits."""
        specs = os.path.join(self._tmp, "specs")
        feature_dir = "2026/08/PROJ-999"
        research_hf = _make_research_handoff(specs, feature_dir)
        discover_hf = _make_discover_handoff(specs, feature_dir)
        result = _scan_specs_dir(self._tmp)
        self.assertEqual(sorted(result), sorted([research_hf, discover_hf]))


# ---------------------------------------------------------------------------
# TestParseHandoff.
# ---------------------------------------------------------------------------


class TestParseHandoff(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._specs = os.path.join(self._tmp, "specs")

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_valid_research_handoff_returns_metadata(self):
        hf = _make_research_handoff(
            self._specs, "001-login-bug", mode="bug",
            completed_at="2026-05-10T09:30:00+00:00",
        )
        result = _parse_handoff(hf)
        self.assertIsNotNone(result)
        self.assertEqual(result["date"], "2026-05-10")
        self.assertEqual(result["slug"], "login-bug")
        self.assertEqual(result["mode"], "bug")
        self.assertEqual(result["verdict"], "bug")
        self.assertEqual(result["kind"], "research")

    def test_research_top_level_verdict_takes_priority_over_mode(self):
        hf = _make_research_handoff(
            self._specs, "001-login-bug", mode="bug",
            extra={"verdict": "proceed"},
        )
        result = _parse_handoff(hf)
        self.assertEqual(result["verdict"], "proceed")

    def test_valid_discover_handoff_returns_metadata(self):
        hf = _make_discover_handoff(
            self._specs, "002-new-widget", verdict="Worth pursuing",
            completed_at="2026-05-12T14:00:00+00:00",
        )
        result = _parse_handoff(hf)
        self.assertIsNotNone(result)
        self.assertEqual(result["date"], "2026-05-12")
        self.assertEqual(result["slug"], "new-widget")
        self.assertEqual(result["kind"], "discover")
        self.assertEqual(result["verdict"], "Worth pursuing")
        self.assertEqual(result["mode"], "")

    def test_path_field_matches_input(self):
        hf = _make_research_handoff(self._specs, "001-login-bug")
        result = _parse_handoff(hf)
        self.assertEqual(result["path"], hf)

    def test_missing_mode_field_defaults_to_empty(self):
        subdir = os.path.join(self._specs, "001-no-mode")
        os.makedirs(subdir, exist_ok=True)
        hf = os.path.join(subdir, "research-handoff.json")
        _write_file(hf, '{"schema_version": "1.0"}')
        result = _parse_handoff(hf)
        self.assertIsNotNone(result)
        self.assertEqual(result["mode"], "")

    def test_malformed_json_returns_none(self):
        subdir = os.path.join(self._specs, "001-broken")
        os.makedirs(subdir, exist_ok=True)
        hf = os.path.join(subdir, "research-handoff.json")
        _write_file(hf, "{bad json}")
        result = _parse_handoff(hf)
        self.assertIsNone(result)

    def test_missing_file_returns_none(self):
        result = _parse_handoff(os.path.join(self._tmp, "nonexistent.json"))
        self.assertIsNone(result)

    def test_dir_without_nnn_slug_format(self):
        subdir = os.path.join(self._specs, "nondated-dir")
        os.makedirs(subdir, exist_ok=True)
        hf = os.path.join(subdir, "research-handoff.json")
        _write_file(hf, '{"mode": "bug"}')
        result = _parse_handoff(hf)
        self.assertIsNotNone(result)
        self.assertEqual(result["date"], "")
        self.assertEqual(result["slug"], "nondated-dir")

    def test_content_excerpt_present(self):
        hf = _make_research_handoff(self._specs, "001-test")
        result = _parse_handoff(hf)
        self.assertIn("content_excerpt", result)
        self.assertIsInstance(result["content_excerpt"], str)
        self.assertGreater(len(result["content_excerpt"]), 0)

    def test_content_excerpt_truncated_when_large(self):
        subdir = os.path.join(self._specs, "001-big")
        os.makedirs(subdir, exist_ok=True)
        hf = os.path.join(subdir, "research-handoff.json")
        # Build a valid JSON object large enough to exceed _EXCERPT_CHARS (5000).
        big_value = "a" * 6000
        _write_file(hf, json.dumps({"mode": "bug", "big_field": big_value}))
        result = _parse_handoff(hf)
        self.assertIsNotNone(result)
        self.assertTrue(result["content_excerpt"].endswith("... [truncated]"))

    def test_empty_json_file_returns_metadata_with_empty_fields(self):
        subdir = os.path.join(self._specs, "001-empty")
        os.makedirs(subdir, exist_ok=True)
        hf = os.path.join(subdir, "research-handoff.json")
        _write_file(hf, "{}")
        result = _parse_handoff(hf)
        self.assertIsNotNone(result)
        self.assertEqual(result["mode"], "")

    def test_verdict_falls_back_to_mode_when_verdict_absent(self):
        """research-handoff.json with mode but no verdict key -> verdict equals mode value."""
        subdir = os.path.join(self._specs, "001-mode-only")
        os.makedirs(subdir, exist_ok=True)
        hf = os.path.join(subdir, "research-handoff.json")
        # Older handoff shape: has 'mode' but no 'verdict'.
        _write_file(hf, json.dumps({"schema_version": "1.0", "mode": "bug"}))
        result = _parse_handoff(hf)
        self.assertIsNotNone(result)
        self.assertEqual(result["verdict"], "bug",
                         "verdict should fall back to mode value when verdict key absent")

    def test_discover_verdict_falls_back_to_mode_when_block_absent(self):
        """discover-handoff.json with no discovery_block -> verdict falls back to mode ('')."""
        subdir = os.path.join(self._specs, "001-no-block")
        os.makedirs(subdir, exist_ok=True)
        hf = os.path.join(subdir, "discover-handoff.json")
        _write_file(hf, json.dumps({"schema_version": "1.0"}))
        result = _parse_handoff(hf)
        self.assertIsNotNone(result)
        self.assertEqual(result["verdict"], "")
        self.assertEqual(result["kind"], "discover")

    def test_discover_top_level_verdict_takes_priority(self):
        """A future top-level 'verdict' key (forward-compat) wins over the nested one."""
        subdir = os.path.join(self._specs, "001-top-level")
        os.makedirs(subdir, exist_ok=True)
        hf = os.path.join(subdir, "discover-handoff.json")
        _write_file(hf, json.dumps({
            "verdict": "top-level-value",
            "discovery_block": {"verdict": "nested-value"},
        }))
        result = _parse_handoff(hf)
        self.assertEqual(result["verdict"], "top-level-value")


# ---------------------------------------------------------------------------
# TestFilterByTicketText.
# ---------------------------------------------------------------------------


class TestFilterByTicketText(unittest.TestCase):
    def _make_handoff_meta(self, slug: str, mode: str = "bug") -> dict:
        return {
            "path": "/fake/specs/001-{0}/research-handoff.json".format(slug),
            "date": "2026-05-01",
            "slug": slug,
            "verdict": "proceed",
            "mode": mode,
            "kind": "research",
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
        self._specs = os.path.join(self._tmp, "specs")
        # Relevant handoff.
        _make_research_handoff(self._specs, "001-auth-login-fix", mode="bug")
        # Irrelevant handoff.
        _make_research_handoff(self._specs, "002-billing-update", mode="feature_addition")

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
        for key in ("path", "date", "slug", "verdict", "mode", "kind", "matched_via", "content_excerpt"):
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
# TestRunDiscoverLane.
# ---------------------------------------------------------------------------


class TestRunDiscoverLane(unittest.TestCase):
    """discover-handoff.json is scanned alongside research-handoff.json."""

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._pr_number = 66
        self._sp = _make_state(self._tmp, self._pr_number)
        self._specs = os.path.join(self._tmp, "specs")
        _make_research_handoff(self._specs, "001-auth-fix")
        _make_discover_handoff(self._specs, "002-new-widget")

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_both_lanes_found(self):
        result = run(self._tmp, self._pr_number)
        self.assertEqual(result["handoffs_found"], 2)

    def test_kinds_present_in_bundle(self):
        run(self._tmp, self._pr_number)
        with open(self._sp, "r", encoding="utf-8") as fh:
            state = json.load(fh)
        kinds = sorted(h["kind"] for h in state["bundle"]["research_handoffs"])
        self.assertEqual(kinds, ["discover", "research"])


# ---------------------------------------------------------------------------
# TestRunNoFilter.
# ---------------------------------------------------------------------------


class TestRunNoFilter(unittest.TestCase):
    """When state has no ticket_text and no pr_body, all handoffs are returned."""

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._pr_number = 22
        self._sp = _make_state(self._tmp, self._pr_number)  # no ticket_text
        self._specs = os.path.join(self._tmp, "specs")
        _make_research_handoff(self._specs, "001-alpha")
        _make_research_handoff(self._specs, "002-beta")

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
        specs = os.path.join(self._tmp, "specs")
        _make_research_handoff(specs, "001-alpha")

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
        specs = os.path.join(self._tmp, "specs")
        # Create 30 feature dirs (well above the cap of 20).
        for i in range(30):
            month = (i % 12) + 1
            day = (i % 28) + 1
            completed_at = "2026-{0:02d}-{1:02d}T00:00:00+00:00".format(month, day)
            slug = "topic-{0:03d}".format(i)
            _make_research_handoff(
                specs, "{0:03d}-{1}".format(i + 1, slug),
                completed_at=completed_at,
            )

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
# TestRunEmptySpecsDir.
# ---------------------------------------------------------------------------


class TestRunEmptySpecsDir(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._pr_number = 77
        self._sp = _make_state(self._tmp, self._pr_number)

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_no_specs_dir_produces_empty_list(self):
        result = run(self._tmp, self._pr_number)
        self.assertEqual(result["handoffs_found"], 0)
        self.assertEqual(result["handoffs_matched"], 0)
        with open(self._sp, "r", encoding="utf-8") as fh:
            state = json.load(fh)
        self.assertEqual(state["bundle"]["research_handoffs"], [])

    def test_empty_specs_dir_produces_empty_list(self):
        os.makedirs(os.path.join(self._tmp, "specs"))
        result = run(self._tmp, self._pr_number)
        self.assertEqual(result["handoffs_found"], 0)


if __name__ == "__main__":
    unittest.main()
