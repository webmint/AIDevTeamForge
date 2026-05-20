"""Tests for src/devforge/lib/_pr_review/_bundle.py.

Coverage:
  _find_constitution via _load_constitution: src/constitution.md present;
    root-fallback constitution.md; neither present.
  _load_constitute_json: valid JSON; missing file; malformed JSON (fail-soft).
  _scan_concern_docs: dirs with both files; missing architecture.md;
    infra-dir filter (lib/template/pr-reviews skipped).
  _scan_adrs: each priority candidate; multi-file ADR dir; empty dir;
    no ADR dir at all.
  _scan_plan_files: multiple *-PLAN.md at repo root; non-PLAN.md ignored.
  _read_file_truncated: content under cap unchanged; over-cap truncated.
  run (happy path): end-to-end against tmp dir with all sources.
  run (persistence): state.json updated; existing fields preserved.
  run (caps): 40 concern dirs → only 30 retained; 110 ADRs → 100 retained;
    60 plan files → 50 retained.
  run (research_handoffs preservation): existing bundle["research_handoffs"]
    is preserved when re-running bundle-context.
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

from _pr_review._bundle import (  # noqa: E402
    _load_constitution,
    _load_constitute_json,
    _read_file_truncated,
    _scan_adrs,
    _scan_concern_docs,
    _scan_plan_files,
    _MAX_ADRS,
    _MAX_CONCERN_DOCS,
    _MAX_PLANS,
    _MAX_CONTENT_CHARS,
    _TRUNCATION_MARKER,
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


def _make_state(tmpdir: str, pr_number: int = 1) -> str:
    """Write a minimal PRReviewState to state.json and return the path."""
    abs_devforge = os.path.join(tmpdir, ".devforge")
    sp = state_path(abs_devforge, pr_number)
    os.makedirs(os.path.dirname(sp), exist_ok=True)
    state = PRReviewState(pr_number=pr_number, repo="acme/app")
    with open(sp, "w", encoding="utf-8") as fh:
        json.dump(dataclasses.asdict(state), fh, indent=2)
        fh.write("\n")
    return sp


# ---------------------------------------------------------------------------
# TestReadFileTruncated.
# ---------------------------------------------------------------------------


class TestReadFileTruncated(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_under_cap_content_unchanged(self):
        p = os.path.join(self._tmp, "small.md")
        _write_file(p, "hello world")
        result = _read_file_truncated(p, max_chars=100)
        self.assertEqual(result, "hello world")

    def test_exactly_at_cap_no_truncation(self):
        content = "x" * 100
        p = os.path.join(self._tmp, "exact.md")
        _write_file(p, content)
        result = _read_file_truncated(p, max_chars=100)
        self.assertEqual(result, content)
        self.assertNotIn(_TRUNCATION_MARKER, result)

    def test_over_cap_truncated_with_marker(self):
        content = "y" * 200
        p = os.path.join(self._tmp, "big.md")
        _write_file(p, content)
        result = _read_file_truncated(p, max_chars=100)
        self.assertTrue(result.endswith(_TRUNCATION_MARKER))
        # The non-marker part should be exactly 100 chars.
        self.assertEqual(len(result) - len(_TRUNCATION_MARKER), 100)

    def test_missing_file_returns_empty_string(self):
        result = _read_file_truncated(os.path.join(self._tmp, "nonexistent.md"))
        self.assertEqual(result, "")

    def test_default_cap_is_50000(self):
        self.assertEqual(_MAX_CONTENT_CHARS, 50_000)

    def test_empty_file_returns_empty_string(self):
        p = os.path.join(self._tmp, "empty.md")
        _write_file(p, "")
        result = _read_file_truncated(p)
        self.assertEqual(result, "")


# ---------------------------------------------------------------------------
# TestFindConstitution (via _load_constitution).
# ---------------------------------------------------------------------------


class TestFindConstitution(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_src_constitution_md_found_first(self):
        src_path = os.path.join(self._tmp, "src", "constitution.md")
        _write_file(src_path, "# src constitution")
        result = _load_constitution(self._tmp)
        self.assertEqual(result["constitution_md"], src_path)
        self.assertEqual(result["constitution_md_content"], "# src constitution")

    def test_root_constitution_md_fallback(self):
        root_path = os.path.join(self._tmp, "constitution.md")
        _write_file(root_path, "# root constitution")
        result = _load_constitution(self._tmp)
        self.assertEqual(result["constitution_md"], root_path)
        self.assertEqual(result["constitution_md_content"], "# root constitution")

    def test_src_takes_priority_over_root(self):
        src_path = os.path.join(self._tmp, "src", "constitution.md")
        root_path = os.path.join(self._tmp, "constitution.md")
        _write_file(src_path, "src")
        _write_file(root_path, "root")
        result = _load_constitution(self._tmp)
        self.assertEqual(result["constitution_md"], src_path)
        self.assertEqual(result["constitution_md_content"], "src")

    def test_neither_present_returns_none_and_empty_content(self):
        result = _load_constitution(self._tmp)
        self.assertIsNone(result["constitution_md"])
        self.assertEqual(result["constitution_md_content"], "")


# ---------------------------------------------------------------------------
# TestLoadConstituteJson.
# ---------------------------------------------------------------------------


class TestLoadConstituteJson(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._devforge = os.path.join(self._tmp, ".devforge")
        os.makedirs(self._devforge, exist_ok=True)

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_valid_json_returns_dict(self):
        p = os.path.join(self._devforge, "constitute.json")
        _write_file(p, '{"tier": "full", "overrides": []}')
        result = _load_constitute_json(self._devforge)
        self.assertIsInstance(result, dict)
        self.assertEqual(result["tier"], "full")

    def test_missing_file_returns_none(self):
        result = _load_constitute_json(self._devforge)
        self.assertIsNone(result)

    def test_malformed_json_returns_none(self):
        p = os.path.join(self._devforge, "constitute.json")
        _write_file(p, "{not valid json")
        result = _load_constitute_json(self._devforge)
        self.assertIsNone(result)

    def test_empty_file_returns_none(self):
        p = os.path.join(self._devforge, "constitute.json")
        _write_file(p, "")
        result = _load_constitute_json(self._devforge)
        self.assertIsNone(result)

    def test_json_array_returns_list(self):
        p = os.path.join(self._devforge, "constitute.json")
        _write_file(p, '[{"key": "value"}]')
        result = _load_constitute_json(self._devforge)
        self.assertIsInstance(result, list)


# ---------------------------------------------------------------------------
# TestScanConcernDocs.
# ---------------------------------------------------------------------------


class TestScanConcernDocs(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._devforge = os.path.join(self._tmp, ".devforge")
        os.makedirs(self._devforge, exist_ok=True)

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _make_concern(self, name: str, overview: str = None, arch: str = None):
        d = os.path.join(self._devforge, name)
        os.makedirs(d, exist_ok=True)
        if overview is not None:
            _write_file(os.path.join(d, "overview.md"), overview)
        if arch is not None:
            _write_file(os.path.join(d, "architecture.md"), arch)

    def test_empty_devforge_returns_empty_list(self):
        result = _scan_concern_docs(self._devforge)
        self.assertEqual(result, [])

    def test_concern_with_both_files(self):
        self._make_concern("auth", overview="Auth overview", arch="Auth arch")
        result = _scan_concern_docs(self._devforge)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["concern"], "auth")
        self.assertEqual(result[0]["overview_content"], "Auth overview")
        self.assertEqual(result[0]["architecture_content"], "Auth arch")
        self.assertTrue(result[0]["overview_path"].endswith("overview.md"))
        self.assertTrue(result[0]["architecture_path"].endswith("architecture.md"))

    def test_concern_with_only_overview(self):
        self._make_concern("payments", overview="Payments overview")
        result = _scan_concern_docs(self._devforge)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["overview_content"], "Payments overview")
        self.assertEqual(result[0]["architecture_content"], "")
        self.assertEqual(result[0]["architecture_path"], "")

    def test_concern_with_only_architecture(self):
        self._make_concern("reporting", arch="Reporting arch")
        result = _scan_concern_docs(self._devforge)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["overview_content"], "")
        self.assertEqual(result[0]["architecture_content"], "Reporting arch")

    def test_infra_dirs_are_filtered(self):
        """lib, template, pr-reviews must not appear as concern docs."""
        for infra in ("lib", "template", "pr-reviews"):
            d = os.path.join(self._devforge, infra)
            os.makedirs(d, exist_ok=True)
            _write_file(os.path.join(d, "overview.md"), "infra content")
        result = _scan_concern_docs(self._devforge)
        concern_names = [r["concern"] for r in result]
        for infra in ("lib", "template", "pr-reviews"):
            self.assertNotIn(infra, concern_names)

    def test_results_sorted_alphabetically(self):
        for name in ("zzz", "aaa", "mmm"):
            self._make_concern(name, overview="x")
        result = _scan_concern_docs(self._devforge)
        names = [r["concern"] for r in result]
        self.assertEqual(names, sorted(names))

    def test_non_directory_entries_ignored(self):
        # A file (not dir) at devforge root should not appear.
        _write_file(os.path.join(self._devforge, "notadir.md"), "content")
        result = _scan_concern_docs(self._devforge)
        names = [r["concern"] for r in result]
        self.assertNotIn("notadir.md", names)

    def test_missing_devforge_returns_empty(self):
        result = _scan_concern_docs(os.path.join(self._tmp, "nonexistent"))
        self.assertEqual(result, [])


# ---------------------------------------------------------------------------
# TestScanAdrs.
# ---------------------------------------------------------------------------


class TestScanAdrs(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _make_adr_dir(self, relpath: str, files: list) -> str:
        d = os.path.join(self._tmp, relpath)
        os.makedirs(d, exist_ok=True)
        for fname in files:
            _write_file(os.path.join(d, fname), "# ADR: {0}".format(fname))
        return d

    def test_no_adr_dir_returns_empty(self):
        result = _scan_adrs(self._tmp)
        self.assertEqual(result, [])

    def test_docs_adr_candidate_found(self):
        self._make_adr_dir("docs/adr", ["0001-init.md", "0002-auth.md"])
        result = _scan_adrs(self._tmp)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["filename"], "0001-init.md")
        self.assertEqual(result[1]["filename"], "0002-auth.md")

    def test_second_priority_candidate_used_when_first_absent(self):
        self._make_adr_dir("docs/architecture/decisions", ["adr-001.md"])
        result = _scan_adrs(self._tmp)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["filename"], "adr-001.md")

    def test_third_priority_candidate(self):
        self._make_adr_dir("architecture/decisions", ["decision-1.md"])
        result = _scan_adrs(self._tmp)
        self.assertEqual(len(result), 1)

    def test_fourth_priority_candidate(self):
        self._make_adr_dir("adr", ["001.md"])
        result = _scan_adrs(self._tmp)
        self.assertEqual(len(result), 1)

    def test_first_priority_takes_precedence(self):
        """docs/adr wins over adr/ even if both exist."""
        self._make_adr_dir("docs/adr", ["priority.md"])
        self._make_adr_dir("adr", ["fallback.md"])
        result = _scan_adrs(self._tmp)
        filenames = [r["filename"] for r in result]
        self.assertIn("priority.md", filenames)
        self.assertNotIn("fallback.md", filenames)

    def test_empty_adr_dir_returns_empty(self):
        d = os.path.join(self._tmp, "docs", "adr")
        os.makedirs(d, exist_ok=True)
        result = _scan_adrs(self._tmp)
        self.assertEqual(result, [])

    def test_non_md_files_ignored(self):
        d = os.path.join(self._tmp, "docs", "adr")
        os.makedirs(d, exist_ok=True)
        _write_file(os.path.join(d, "README.txt"), "not md")
        _write_file(os.path.join(d, "0001.md"), "# ADR")
        result = _scan_adrs(self._tmp)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["filename"], "0001.md")

    def test_adr_content_read(self):
        self._make_adr_dir("docs/adr", ["0001.md"])
        result = _scan_adrs(self._tmp)
        self.assertIn("# ADR: 0001.md", result[0]["content"])

    def test_adr_path_is_absolute(self):
        self._make_adr_dir("docs/adr", ["0001.md"])
        result = _scan_adrs(self._tmp)
        self.assertTrue(os.path.isabs(result[0]["path"]))

    def test_sorted_by_filename(self):
        self._make_adr_dir("docs/adr", ["0003.md", "0001.md", "0002.md"])
        result = _scan_adrs(self._tmp)
        filenames = [r["filename"] for r in result]
        self.assertEqual(filenames, sorted(filenames))


# ---------------------------------------------------------------------------
# TestScanPlanFiles.
# ---------------------------------------------------------------------------


class TestScanPlanFiles(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_no_plan_files_returns_empty(self):
        result = _scan_plan_files(self._tmp)
        self.assertEqual(result, [])

    def test_plan_files_discovered(self):
        _write_file(os.path.join(self._tmp, "FEATURE-PLAN.md"), "# Feature Plan")
        _write_file(os.path.join(self._tmp, "RESEARCH-PLAN.md"), "# Research Plan")
        result = _scan_plan_files(self._tmp)
        self.assertEqual(len(result), 2)

    def test_non_plan_files_ignored(self):
        _write_file(os.path.join(self._tmp, "README.md"), "readme")
        _write_file(os.path.join(self._tmp, "PLAN-NOTES.md"), "notes")  # doesn't end with -PLAN.md
        _write_file(os.path.join(self._tmp, "FEATURE-PLAN.md"), "plan")
        result = _scan_plan_files(self._tmp)
        names = [r["name"] for r in result]
        self.assertIn("FEATURE-PLAN.md", names)
        self.assertNotIn("README.md", names)
        self.assertNotIn("PLAN-NOTES.md", names)

    def test_sorted_alphabetically(self):
        for name in ("Z-PLAN.md", "A-PLAN.md", "M-PLAN.md"):
            _write_file(os.path.join(self._tmp, name), "content")
        result = _scan_plan_files(self._tmp)
        names = [r["name"] for r in result]
        self.assertEqual(names, sorted(names))

    def test_plan_file_content_read(self):
        _write_file(os.path.join(self._tmp, "TEST-PLAN.md"), "Plan content here")
        result = _scan_plan_files(self._tmp)
        self.assertEqual(result[0]["content"], "Plan content here")

    def test_plan_file_path_is_absolute(self):
        _write_file(os.path.join(self._tmp, "TEST-PLAN.md"), "x")
        result = _scan_plan_files(self._tmp)
        self.assertTrue(os.path.isabs(result[0]["path"]))

    def test_subdirectory_plan_files_not_included(self):
        """Only root-level *-PLAN.md; subdirs are not searched."""
        sub = os.path.join(self._tmp, "subdir")
        os.makedirs(sub, exist_ok=True)
        _write_file(os.path.join(sub, "SUB-PLAN.md"), "sub plan")
        _write_file(os.path.join(self._tmp, "ROOT-PLAN.md"), "root plan")
        result = _scan_plan_files(self._tmp)
        names = [r["name"] for r in result]
        self.assertIn("ROOT-PLAN.md", names)
        self.assertNotIn("SUB-PLAN.md", names)


# ---------------------------------------------------------------------------
# TestRunHappyPath.
# ---------------------------------------------------------------------------


class TestRunHappyPath(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._pr_number = 42
        self._sp = _make_state(self._tmp, self._pr_number)
        self._devforge = os.path.join(self._tmp, ".devforge")

        # Constitution.
        _write_file(
            os.path.join(self._tmp, "src", "constitution.md"),
            "# Constitution",
        )
        # constitute.json.
        _write_file(
            os.path.join(self._devforge, "constitute.json"),
            '{"tier": "full"}',
        )
        # Concern doc.
        concern_dir = os.path.join(self._devforge, "auth")
        os.makedirs(concern_dir, exist_ok=True)
        _write_file(os.path.join(concern_dir, "overview.md"), "Auth overview")
        _write_file(os.path.join(concern_dir, "architecture.md"), "Auth arch")
        # ADR.
        _write_file(
            os.path.join(self._tmp, "docs", "adr", "0001.md"),
            "# ADR 0001",
        )
        # Plan file.
        _write_file(
            os.path.join(self._tmp, "FEATURE-PLAN.md"),
            "# Feature Plan",
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_run_returns_ok_status(self):
        result = run(self._tmp, self._pr_number)
        self.assertEqual(result["status"], "ok")

    def test_run_returns_state_path(self):
        result = run(self._tmp, self._pr_number)
        self.assertEqual(result["state_path"], self._sp)

    def test_run_returns_pr_number(self):
        result = run(self._tmp, self._pr_number)
        self.assertEqual(result["pr_number"], self._pr_number)

    def test_run_returns_sources_gathered(self):
        result = run(self._tmp, self._pr_number)
        sg = result["sources_gathered"]
        self.assertTrue(sg["constitution_md"])
        self.assertTrue(sg["constitute_json"])
        self.assertEqual(sg["concern_docs_count"], 1)
        self.assertEqual(sg["adrs_count"], 1)
        self.assertEqual(sg["plan_files_count"], 1)

    def test_state_bundle_constitution_md_content(self):
        run(self._tmp, self._pr_number)
        with open(self._sp, "r", encoding="utf-8") as fh:
            state = json.load(fh)
        self.assertEqual(state["bundle"]["constitution_md_content"], "# Constitution")

    def test_state_bundle_constitute_json(self):
        run(self._tmp, self._pr_number)
        with open(self._sp, "r", encoding="utf-8") as fh:
            state = json.load(fh)
        self.assertEqual(state["bundle"]["constitute_json"]["tier"], "full")

    def test_state_bundle_concern_docs(self):
        run(self._tmp, self._pr_number)
        with open(self._sp, "r", encoding="utf-8") as fh:
            state = json.load(fh)
        self.assertEqual(len(state["bundle"]["concern_docs"]), 1)
        self.assertEqual(state["bundle"]["concern_docs"][0]["concern"], "auth")
        self.assertEqual(
            state["bundle"]["concern_docs"][0]["overview_content"], "Auth overview"
        )

    def test_state_bundle_adrs(self):
        run(self._tmp, self._pr_number)
        with open(self._sp, "r", encoding="utf-8") as fh:
            state = json.load(fh)
        self.assertEqual(len(state["bundle"]["adrs"]), 1)
        self.assertEqual(state["bundle"]["adrs"][0]["filename"], "0001.md")

    def test_state_bundle_plan_files(self):
        run(self._tmp, self._pr_number)
        with open(self._sp, "r", encoding="utf-8") as fh:
            state = json.load(fh)
        self.assertEqual(len(state["bundle"]["plan_files"]), 1)
        self.assertEqual(state["bundle"]["plan_files"][0]["name"], "FEATURE-PLAN.md")

    def test_state_bundle_has_required_keys(self):
        run(self._tmp, self._pr_number)
        with open(self._sp, "r", encoding="utf-8") as fh:
            state = json.load(fh)
        bundle = state["bundle"]
        for key in (
            "constitution_md",
            "constitution_md_content",
            "constitute_json",
            "concern_docs",
            "adrs",
            "plan_files",
        ):
            self.assertIn(key, bundle, "bundle missing key: {0}".format(key))


# ---------------------------------------------------------------------------
# TestRunPersistence.
# ---------------------------------------------------------------------------


class TestRunPersistence(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._pr_number = 7
        self._sp = _make_state(self._tmp, self._pr_number)

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_existing_state_fields_preserved(self):
        """After run, non-bundle state fields (e.g. repo) are preserved."""
        run(self._tmp, self._pr_number)
        with open(self._sp, "r", encoding="utf-8") as fh:
            state = json.load(fh)
        self.assertEqual(state["repo"], "acme/app")
        self.assertEqual(state["pr_number"], self._pr_number)

    def test_existing_research_handoffs_preserved(self):
        """research_handoffs in bundle is preserved by re-run of bundle-context."""
        # Pre-populate bundle with research_handoffs.
        with open(self._sp, "r", encoding="utf-8") as fh:
            state_dict = json.load(fh)
        state_dict["bundle"]["research_handoffs"] = [{"path": "/fake/handoff.json"}]
        with open(self._sp, "w", encoding="utf-8") as fh:
            json.dump(state_dict, fh)

        run(self._tmp, self._pr_number)

        with open(self._sp, "r", encoding="utf-8") as fh:
            state_after = json.load(fh)
        self.assertIn("research_handoffs", state_after["bundle"])
        self.assertEqual(
            state_after["bundle"]["research_handoffs"],
            [{"path": "/fake/handoff.json"}],
        )

    def test_no_state_json_raises_value_error(self):
        with self.assertRaises(ValueError) as ctx:
            run(self._tmp, 9999)
        self.assertIn("intake", str(ctx.exception))

    def test_run_is_idempotent(self):
        """Running twice produces the same bundle content."""
        # Add a constitution so there's something to collect.
        _write_file(
            os.path.join(self._tmp, "src", "constitution.md"),
            "idempotent test",
        )
        run(self._tmp, self._pr_number)
        with open(self._sp, "r", encoding="utf-8") as fh:
            bundle_first = json.load(fh)["bundle"]

        run(self._tmp, self._pr_number)
        with open(self._sp, "r", encoding="utf-8") as fh:
            bundle_second = json.load(fh)["bundle"]

        self.assertEqual(
            bundle_first["constitution_md_content"],
            bundle_second["constitution_md_content"],
        )

    def test_bundle_replaces_prior_bundle_keys(self):
        """Running bundle-context replaces non-research_handoffs bundle keys."""
        # Pre-populate bundle with an old stale value.
        with open(self._sp, "r", encoding="utf-8") as fh:
            state_dict = json.load(fh)
        state_dict["bundle"]["constitution_md_content"] = "old value"
        with open(self._sp, "w", encoding="utf-8") as fh:
            json.dump(state_dict, fh)

        # Now add a real constitution and re-run.
        _write_file(
            os.path.join(self._tmp, "src", "constitution.md"),
            "fresh value",
        )
        run(self._tmp, self._pr_number)

        with open(self._sp, "r", encoding="utf-8") as fh:
            state_after = json.load(fh)
        self.assertEqual(
            state_after["bundle"]["constitution_md_content"], "fresh value"
        )


# ---------------------------------------------------------------------------
# TestCaps.
# ---------------------------------------------------------------------------


class TestCaps(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._devforge = os.path.join(self._tmp, ".devforge")
        os.makedirs(self._devforge, exist_ok=True)

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_concern_docs_capped_at_30(self):
        # Create 40 concern dirs.
        for i in range(40):
            d = os.path.join(self._devforge, "concern-{0:03d}".format(i))
            os.makedirs(d, exist_ok=True)
            _write_file(os.path.join(d, "overview.md"), "overview")
        result = _scan_concern_docs(self._devforge)
        self.assertEqual(len(result), _MAX_CONCERN_DOCS)
        self.assertEqual(_MAX_CONCERN_DOCS, 30)

    def test_adrs_capped_at_100(self):
        adr_dir = os.path.join(self._tmp, "docs", "adr")
        os.makedirs(adr_dir, exist_ok=True)
        for i in range(110):
            _write_file(
                os.path.join(adr_dir, "{0:04d}.md".format(i)),
                "ADR",
            )
        result = _scan_adrs(self._tmp)
        self.assertEqual(len(result), _MAX_ADRS)
        self.assertEqual(_MAX_ADRS, 100)

    def test_plan_files_capped_at_50(self):
        for i in range(60):
            _write_file(
                os.path.join(self._tmp, "PLAN-{0:03d}-PLAN.md".format(i)),
                "plan",
            )
        result = _scan_plan_files(self._tmp)
        self.assertEqual(len(result), _MAX_PLANS)
        self.assertEqual(_MAX_PLANS, 50)

    def test_concern_docs_cap_takes_alphabetical_first_30(self):
        for i in range(40):
            d = os.path.join(self._devforge, "concern-{0:03d}".format(i))
            os.makedirs(d, exist_ok=True)
            _write_file(os.path.join(d, "overview.md"), "x")
        result = _scan_concern_docs(self._devforge)
        # Should be concern-000 through concern-029 (alphabetically first 30).
        names = [r["concern"] for r in result]
        self.assertEqual(names[0], "concern-000")
        self.assertEqual(names[-1], "concern-029")


# ---------------------------------------------------------------------------
# TestRunMinimalEnv.
# ---------------------------------------------------------------------------


class TestRunMinimalEnv(unittest.TestCase):
    """run() against a minimal tmp dir (no sources) returns empty bundle."""

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._pr_number = 3
        self._sp = _make_state(self._tmp, self._pr_number)

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_run_empty_repo_produces_null_constitution(self):
        result = run(self._tmp, self._pr_number)
        self.assertEqual(result["status"], "ok")
        with open(self._sp, "r", encoding="utf-8") as fh:
            state = json.load(fh)
        self.assertIsNone(state["bundle"]["constitution_md"])
        self.assertEqual(state["bundle"]["constitution_md_content"], "")

    def test_run_empty_repo_produces_null_constitute_json(self):
        run(self._tmp, self._pr_number)
        with open(self._sp, "r", encoding="utf-8") as fh:
            state = json.load(fh)
        self.assertIsNone(state["bundle"]["constitute_json"])

    def test_run_empty_repo_produces_empty_concern_docs(self):
        run(self._tmp, self._pr_number)
        with open(self._sp, "r", encoding="utf-8") as fh:
            state = json.load(fh)
        self.assertEqual(state["bundle"]["concern_docs"], [])

    def test_run_empty_repo_produces_empty_adrs(self):
        run(self._tmp, self._pr_number)
        with open(self._sp, "r", encoding="utf-8") as fh:
            state = json.load(fh)
        self.assertEqual(state["bundle"]["adrs"], [])

    def test_run_empty_repo_produces_empty_plan_files(self):
        run(self._tmp, self._pr_number)
        with open(self._sp, "r", encoding="utf-8") as fh:
            state = json.load(fh)
        self.assertEqual(state["bundle"]["plan_files"], [])


if __name__ == "__main__":
    unittest.main()
