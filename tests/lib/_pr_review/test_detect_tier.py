"""Tests for src/devforge/lib/_pr_review/_detect_tier.py.

Covers:
  run()            — public entry point, all tier outcomes
  _find_concern_dirs — subdirectory discovery
  _find_adr_dir    — ADR priority ordering
  _find_constitution — src/ preference + root fallback
  _classify_tier   — pure mapping (all four input combinations)
  path absoluteness — all manifest paths must start with /
"""

import os
import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _pr_review._detect_tier import (  # noqa: E402
    _ADR_CANDIDATES,
    _DEVFORGE_INFRA_SUBDIRS,
    _classify_tier,
    _find_adr_dir,
    _find_concern_dirs,
    _find_constitution,
    run,
)


def _make_file(path: str) -> None:
    """Create file at path, creating parent directories as needed."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write("")


def _make_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


# ---------------------------------------------------------------------------
# _classify_tier — pure function, no filesystem.
# ---------------------------------------------------------------------------


class TestClassifyTier(unittest.TestCase):
    def test_none_when_both_absent(self):
        self.assertEqual(_classify_tier(None, None, []), "none")

    def test_partial_when_only_constitute_json(self):
        self.assertEqual(_classify_tier("/a/constitute.json", None, []), "partial")

    def test_partial_when_only_constitution_md(self):
        self.assertEqual(_classify_tier(None, "/a/constitution.md", []), "partial")

    def test_partial_when_both_but_no_concern_dirs(self):
        self.assertEqual(
            _classify_tier("/a/constitute.json", "/a/constitution.md", []),
            "partial",
        )

    def test_partial_when_concern_dirs_but_missing_one_key_file(self):
        # constitution_md + dirs but no constitute_json → partial
        self.assertEqual(
            _classify_tier(None, "/a/constitution.md", ["/x/concern1"]),
            "partial",
        )

    def test_full_when_all_three_present(self):
        self.assertEqual(
            _classify_tier(
                "/a/constitute.json", "/a/constitution.md", ["/x/concern1"]
            ),
            "full",
        )


# ---------------------------------------------------------------------------
# _find_concern_dirs — filesystem.
# ---------------------------------------------------------------------------


class TestFindConcernDirs(unittest.TestCase):
    def setUp(self):
        import tempfile
        self._tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_empty_dir_returns_empty(self):
        result = _find_concern_dirs(self._tmp)
        self.assertEqual(result, [])

    def test_nonexistent_dir_returns_empty(self):
        result = _find_concern_dirs(os.path.join(self._tmp, "does-not-exist"))
        self.assertEqual(result, [])

    def test_only_files_excluded(self):
        _make_file(os.path.join(self._tmp, "constitute.json"))
        result = _find_concern_dirs(self._tmp)
        self.assertEqual(result, [])

    def test_subdirs_returned_sorted(self):
        _make_dir(os.path.join(self._tmp, "zzz_concern"))
        _make_dir(os.path.join(self._tmp, "aaa_concern"))
        _make_dir(os.path.join(self._tmp, "mmm_concern"))
        result = _find_concern_dirs(self._tmp)
        self.assertEqual(
            result,
            [
                os.path.join(self._tmp, "aaa_concern"),
                os.path.join(self._tmp, "mmm_concern"),
                os.path.join(self._tmp, "zzz_concern"),
            ],
        )

    def test_mixed_files_and_dirs(self):
        _make_dir(os.path.join(self._tmp, "concern1"))
        _make_file(os.path.join(self._tmp, "constitute.json"))
        _make_dir(os.path.join(self._tmp, "concern2"))
        result = _find_concern_dirs(self._tmp)
        self.assertEqual(len(result), 2)
        self.assertTrue(all(os.path.isdir(p) for p in result))

    def test_concern_dirs_excludes_lib(self):
        """lib/ is an infra dir installed by install.sh — must not appear as a concern dir."""
        _make_dir(os.path.join(self._tmp, "lib"))
        result = _find_concern_dirs(self._tmp)
        self.assertEqual(result, [])

    def test_concern_dirs_excludes_template(self):
        """template/ is created by install.sh — must not appear as a concern dir."""
        _make_dir(os.path.join(self._tmp, "template"))
        result = _find_concern_dirs(self._tmp)
        self.assertEqual(result, [])

    def test_concern_dirs_excludes_pr_reviews(self):
        """pr-reviews/ is created by /pr-review itself — must not appear as a concern dir."""
        _make_dir(os.path.join(self._tmp, "pr-reviews"))
        result = _find_concern_dirs(self._tmp)
        self.assertEqual(result, [])

    def test_concern_dirs_mixed_filters_infra(self):
        """Infra dirs are filtered; real concern dirs pass through sorted."""
        _make_dir(os.path.join(self._tmp, "lib"))
        _make_dir(os.path.join(self._tmp, "template"))
        _make_dir(os.path.join(self._tmp, "api"))
        _make_dir(os.path.join(self._tmp, "auth"))
        result = _find_concern_dirs(self._tmp)
        self.assertEqual(len(result), 2)
        self.assertTrue(result[0].endswith("api"))
        self.assertTrue(result[1].endswith("auth"))

    def test_infra_subdirs_constant_contains_expected_names(self):
        """_DEVFORGE_INFRA_SUBDIRS contains the three known infra dirs."""
        self.assertIn("lib", _DEVFORGE_INFRA_SUBDIRS)
        self.assertIn("template", _DEVFORGE_INFRA_SUBDIRS)
        self.assertIn("pr-reviews", _DEVFORGE_INFRA_SUBDIRS)


# ---------------------------------------------------------------------------
# _find_adr_dir — priority ordering.
# ---------------------------------------------------------------------------


class TestFindAdrDir(unittest.TestCase):
    def setUp(self):
        import tempfile
        self._tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_none_when_no_adr_dir(self):
        self.assertIsNone(_find_adr_dir(self._tmp))

    def test_finds_docs_adr(self):
        _make_dir(os.path.join(self._tmp, "docs", "adr"))
        result = _find_adr_dir(self._tmp)
        self.assertEqual(result, os.path.join(self._tmp, "docs", "adr"))

    def test_priority_docs_adr_over_later_candidates(self):
        # Create both docs/adr and docs/architecture/decisions — first wins.
        _make_dir(os.path.join(self._tmp, "docs", "adr"))
        _make_dir(os.path.join(self._tmp, "docs", "architecture", "decisions"))
        result = _find_adr_dir(self._tmp)
        self.assertEqual(result, os.path.join(self._tmp, "docs", "adr"))

    def test_falls_through_to_second_candidate(self):
        # Only docs/architecture/decisions exists.
        _make_dir(os.path.join(self._tmp, "docs", "architecture", "decisions"))
        result = _find_adr_dir(self._tmp)
        self.assertEqual(
            result,
            os.path.join(self._tmp, "docs", "architecture", "decisions"),
        )

    def test_falls_through_to_root_adr(self):
        _make_dir(os.path.join(self._tmp, "adr"))
        result = _find_adr_dir(self._tmp)
        self.assertEqual(result, os.path.join(self._tmp, "adr"))

    def test_adr_candidates_priority_order(self):
        """_ADR_CANDIDATES is ordered: docs/adr first, adr last."""
        self.assertEqual(_ADR_CANDIDATES[0], "docs/adr")
        self.assertEqual(_ADR_CANDIDATES[-1], "adr")


# ---------------------------------------------------------------------------
# _find_constitution — src/ preference + root fallback.
# ---------------------------------------------------------------------------


class TestFindConstitution(unittest.TestCase):
    def setUp(self):
        import tempfile
        self._tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_none_when_absent(self):
        self.assertIsNone(_find_constitution(self._tmp))

    def test_finds_src_constitution(self):
        path = os.path.join(self._tmp, "src", "constitution.md")
        _make_file(path)
        result = _find_constitution(self._tmp)
        self.assertEqual(result, path)

    def test_root_fallback_when_src_absent(self):
        path = os.path.join(self._tmp, "constitution.md")
        _make_file(path)
        result = _find_constitution(self._tmp)
        self.assertEqual(result, path)

    def test_src_preferred_when_both_exist(self):
        src_path = os.path.join(self._tmp, "src", "constitution.md")
        root_path = os.path.join(self._tmp, "constitution.md")
        _make_file(src_path)
        _make_file(root_path)
        result = _find_constitution(self._tmp)
        self.assertEqual(result, src_path)


# ---------------------------------------------------------------------------
# run() — full integration with temp directories.
# ---------------------------------------------------------------------------


class TestRun(unittest.TestCase):
    def setUp(self):
        import tempfile
        self._tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_tier_none_empty_dir(self):
        result = run(self._tmp)
        self.assertEqual(result["tier"], "none")
        self.assertIsNone(result["manifest"]["constitute_json"])
        self.assertIsNone(result["manifest"]["constitution_md"])
        self.assertEqual(result["manifest"]["concern_doc_dirs"], [])
        self.assertIsNone(result["manifest"]["adr_dir"])

    def test_tier_partial_constitute_only(self):
        _make_file(os.path.join(self._tmp, ".devforge", "constitute.json"))
        result = run(self._tmp)
        self.assertEqual(result["tier"], "partial")
        self.assertIsNotNone(result["manifest"]["constitute_json"])

    def test_tier_partial_constitution_md_only(self):
        _make_file(os.path.join(self._tmp, "src", "constitution.md"))
        result = run(self._tmp)
        self.assertEqual(result["tier"], "partial")
        self.assertIsNotNone(result["manifest"]["constitution_md"])

    def test_tier_full(self):
        _make_file(os.path.join(self._tmp, ".devforge", "constitute.json"))
        _make_file(os.path.join(self._tmp, "src", "constitution.md"))
        _make_dir(os.path.join(self._tmp, ".devforge", "api"))
        result = run(self._tmp)
        self.assertEqual(result["tier"], "full")

    def test_concern_dirs_listed_sorted(self):
        _make_file(os.path.join(self._tmp, ".devforge", "constitute.json"))
        _make_dir(os.path.join(self._tmp, ".devforge", "zzz"))
        _make_dir(os.path.join(self._tmp, ".devforge", "aaa"))
        result = run(self._tmp)
        dirs = result["manifest"]["concern_doc_dirs"]
        self.assertEqual(len(dirs), 2)
        self.assertTrue(dirs[0].endswith("aaa"))
        self.assertTrue(dirs[1].endswith("zzz"))

    def test_adr_dir_first_match(self):
        _make_dir(os.path.join(self._tmp, "docs", "adr"))
        _make_dir(os.path.join(self._tmp, "docs", "architecture", "decisions"))
        result = run(self._tmp)
        self.assertIsNotNone(result["manifest"]["adr_dir"])
        self.assertTrue(result["manifest"]["adr_dir"].endswith(os.path.join("docs", "adr")))

    def test_constitution_root_fallback(self):
        _make_file(os.path.join(self._tmp, "constitution.md"))
        result = run(self._tmp)
        self.assertIsNotNone(result["manifest"]["constitution_md"])
        self.assertTrue(result["manifest"]["constitution_md"].endswith("constitution.md"))
        # Ensure it's the root file, not inside src/.
        self.assertNotIn("src", result["manifest"]["constitution_md"].replace(self._tmp, ""))

    def test_paths_absolute(self):
        _make_file(os.path.join(self._tmp, ".devforge", "constitute.json"))
        _make_file(os.path.join(self._tmp, "src", "constitution.md"))
        _make_dir(os.path.join(self._tmp, ".devforge", "concern1"))
        _make_dir(os.path.join(self._tmp, "docs", "adr"))
        result = run(self._tmp)
        manifest = result["manifest"]
        for key in ("constitute_json", "constitution_md"):
            val = manifest[key]
            self.assertIsNotNone(val)
            self.assertTrue(
                os.path.isabs(val),
                "{0} should be absolute, got: {1}".format(key, val),
            )
        for path in manifest["concern_doc_dirs"]:
            self.assertTrue(
                os.path.isabs(path),
                "concern_doc_dirs entry should be absolute, got: {0}".format(path),
            )
        self.assertTrue(os.path.isabs(result["manifest"]["adr_dir"]))
        self.assertTrue(os.path.isabs(result["target_path"]))

    def test_target_path_in_result(self):
        result = run(self._tmp)
        self.assertEqual(result["target_path"], os.path.abspath(self._tmp))

    def test_custom_devforge_dir(self):
        custom_dir = ".myforge"
        _make_file(os.path.join(self._tmp, custom_dir, "constitute.json"))
        _make_dir(os.path.join(self._tmp, custom_dir, "concern1"))
        _make_file(os.path.join(self._tmp, "src", "constitution.md"))
        result = run(self._tmp, devforge_dir=custom_dir)
        self.assertEqual(result["tier"], "full")

    def test_tier_partial_with_only_infra_dirs(self):
        """constitute.json + src/constitution.md + lib/ (no real concern dirs) → partial, not full."""
        _make_file(os.path.join(self._tmp, ".devforge", "constitute.json"))
        _make_file(os.path.join(self._tmp, "src", "constitution.md"))
        _make_dir(os.path.join(self._tmp, ".devforge", "lib"))
        result = run(self._tmp)
        self.assertEqual(result["tier"], "partial")
        self.assertEqual(result["manifest"]["concern_doc_dirs"], [])


if __name__ == "__main__":
    unittest.main()
