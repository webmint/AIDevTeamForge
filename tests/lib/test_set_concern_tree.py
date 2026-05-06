"""Tests for the set-concern-tree --text tree-entry coverage check (Fix B).

Verifies that set-concern-tree validates rendered entry count against
index.json file listings and rejects trees with coverage below 80%.

Test cases (13 new tests, numbered per spec):
  6.  test_tree_entry_coverage_above_threshold_passes
  7.  test_tree_entry_coverage_below_threshold_fails
  8.  test_tree_entry_coverage_skipped_when_index_missing
  9.  test_tree_entry_coverage_skipped_when_subfolder_empty
  10. test_tree_entry_coverage_excludes_trivial_leaves
  11. test_tree_entry_coverage_includes_canonical_aggregators
  12. test_tree_entry_coverage_skipped_when_expected_below_5
  13. test_tree_entry_coverage_canonical_threshold_value

  Plus unit tests for helpers:
  U1. _load_index_files returns None on missing file
  U2. _load_index_files returns None on bad JSON
  U3. _load_index_files returns None on missing pkg_path
  U4. _path_contains_trivial_dir detects node_modules component
  U5. _build_expected_entry_set counts files and intermediate dirs

Subprocess invocations mirror test_verify_annotations.py infrastructure.
Stdlib only. Python 3.8+.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"
_HELPER_PY = _LIB_DIR / "generate_docs_helper.py"
_SETTERS_CONCERN = _LIB_DIR / "_generate_docs" / "_setters_concern.py"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

# Import the module under test for unit-level testing of helpers.
from _generate_docs._setters_concern import (  # noqa: E402
    TREE_ENTRY_COVERAGE_THRESHOLD,
    _build_expected_entry_set,
    _check_tree_entry_coverage,
    _count_rendered_tree_entries,
    _load_index_files,
    _path_contains_trivial_dir,
)

import generate_docs_helper as gdh  # noqa: E402


# ---------------------------------------------------------------------------
# Shared infrastructure
# ---------------------------------------------------------------------------


def _run_cli(devforge_dir, *args):
    env = os.environ.copy()
    env["DEVFORGE_DIR"] = str(devforge_dir)
    env.pop("DEVFORGE_PROJECT_ROOT", None)
    return subprocess.run(
        [sys.executable, str(_HELPER_PY)] + list(args),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


class _SetConcernTreeBase(unittest.TestCase):
    """Isolated tmp dir + shared setup helpers."""

    def setUp(self):
        self._saved_devforge = os.environ.pop("DEVFORGE_DIR", None)
        self._saved_root = os.environ.pop("DEVFORGE_PROJECT_ROOT", None)
        self._tmp = tempfile.TemporaryDirectory()
        self.devforge_dir = Path(self._tmp.name) / ".devforge"
        self.devforge_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.devforge_dir / gdh.STATE_FILE_NAME

    def tearDown(self):
        self._tmp.cleanup()
        if self._saved_devforge is None:
            os.environ.pop("DEVFORGE_DIR", None)
        else:
            os.environ["DEVFORGE_DIR"] = self._saved_devforge
        if self._saved_root is None:
            os.environ.pop("DEVFORGE_PROJECT_ROOT", None)
        else:
            os.environ["DEVFORGE_PROJECT_ROOT"] = self._saved_root

    def _run(self, *args):
        return _run_cli(self.devforge_dir, *args)

    def _read_state(self):
        return json.loads(self.state_file.read_text(encoding="utf-8"))

    def _write_state_direct(self, state):
        self.state_file.write_text(
            json.dumps(state, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def _init_pkg_concern(self, package="apps/web", concern="components"):
        r = self._run("add-package", "--path", package, "--name", "web")
        self.assertEqual(r.returncode, 0, r.stderr)
        r = self._run("add-concern", "--package", package, "--concern", concern)
        self.assertEqual(r.returncode, 0, r.stderr)

    def _write_index_json(self, packages):
        """Write a minimal index.json to the devforge dir."""
        index = {
            "version": 1,
            "generated_at": "2026-05-06T00:00:00Z",
            "project_root": str(self._tmp.name),
            "packages": packages,
        }
        index_path = self.devforge_dir / "index.json"
        index_path.write_text(
            json.dumps(index, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def _make_tree_text(self, entries):
        """Build a minimal tree text string with N entries using tree glyphs."""
        lines = ["src/components/"]
        for i, entry in enumerate(entries):
            glyph = "└── " if i == len(entries) - 1 else "├── "
            lines.append("{0}{1}".format(glyph, entry))
        return "\n".join(lines)

    def _make_files_for_concern(self, concern="components", count=100,
                                prefix="src/components/"):
        """Build a list of file paths under the given prefix."""
        return ["{0}file_{1:03d}.ts".format(prefix, i) for i in range(count)]

    def _set_concern_tree(self, tree_text, package="apps/web",
                          concern="components"):
        return self._run(
            "set-concern-tree",
            "--package", package,
            "--concern", concern,
            "--text", tree_text,
        )


# ---------------------------------------------------------------------------
# CLI integration tests (subprocess)
# ---------------------------------------------------------------------------


class Test06CoverageAboveThresholdPasses(_SetConcernTreeBase):
    """Test 6: 100 files in index, 85-entry tree → coverage 85% >= 80% → exit 0."""

    def test_tree_entry_coverage_above_threshold_passes(self):
        self._init_pkg_concern()
        # 100 flat files in src/components/ (each is a single-level file,
        # so expected = 100 entries).
        files = self._make_files_for_concern(count=100)
        self._write_index_json({
            "apps/web": {"files": files, "files_truncated": False},
        })
        # 85 rendered entries → coverage = 85% >= 80% → should pass.
        tree_text = self._make_tree_text(
            ["file_{0:03d}.ts".format(i) for i in range(85)]
        )
        r = self._set_concern_tree(tree_text)
        self.assertEqual(r.returncode, 0, r.stderr)
        # State should be updated.
        state = self._read_state()
        self.assertEqual(
            state["packages"]["apps/web"]["concerns"]["components"]["directory_tree"],
            tree_text,
        )


class Test07CoverageBelowThresholdFails(_SetConcernTreeBase):
    """Test 7: 100 files, 23-entry tree → coverage 23% < 80% → exit 2."""

    def test_tree_entry_coverage_below_threshold_fails(self):
        self._init_pkg_concern()
        files = self._make_files_for_concern(count=100)
        self._write_index_json({
            "apps/web": {"files": files, "files_truncated": False},
        })
        # 23 rendered entries → 23% < 80% → should fail.
        tree_text = self._make_tree_text(
            ["Subfolder_{0}/".format(i) for i in range(23)]
        )
        r = self._set_concern_tree(tree_text)
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn(b"tree coverage", r.stderr)
        # Exact percentage match: 23/100 = 23.0%.
        self.assertIn(b"23.0%", r.stderr)
        self.assertIn(b"80.0%", r.stderr)


class Test08CoverageSkippedWhenIndexMissing(_SetConcernTreeBase):
    """Test 8: No index.json → coverage check skipped → exit 0 with warning."""

    def test_tree_entry_coverage_skipped_when_index_missing(self):
        self._init_pkg_concern()
        # No index.json written.
        tree_text = self._make_tree_text(["a.ts", "b.ts"])
        r = self._set_concern_tree(tree_text)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn(b"coverage check skipped", r.stderr)
        self.assertIn(b"index.json missing", r.stderr)


class Test09CoverageSkippedWhenSubfolderEmpty(_SetConcernTreeBase):
    """Test 9: index.json present but no files under src/components/ → skip."""

    def test_tree_entry_coverage_skipped_when_subfolder_empty(self):
        self._init_pkg_concern()
        # index.json has the package but zero files under src/components/.
        self._write_index_json({
            "apps/web": {
                "files": ["src/auth/login.ts", "src/auth/logout.ts"],
                "files_truncated": False,
            },
        })
        tree_text = self._make_tree_text(["ComponentA.ts"])
        r = self._set_concern_tree(tree_text)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn(b"coverage check skipped", r.stderr)


class Test10CoverageExcludesTrivialLeaves(_SetConcernTreeBase):
    """Test 10: 100 files, 30 inside node_modules → expected=70 → 70 rendered = 100%."""

    def test_tree_entry_coverage_excludes_trivial_leaves(self):
        self._init_pkg_concern()
        # 70 normal files + 30 under node_modules (trivial leaf → excluded).
        normal_files = [
            "src/components/comp_{0:02d}.ts".format(i) for i in range(70)
        ]
        trivial_files = [
            "src/components/node_modules/pkg_{0}/index.js".format(i)
            for i in range(30)
        ]
        all_files = normal_files + trivial_files
        self._write_index_json({
            "apps/web": {"files": all_files, "files_truncated": False},
        })
        # Render 70 entries (all normal, none from node_modules).
        tree_text = self._make_tree_text(
            ["comp_{0:02d}.ts".format(i) for i in range(70)]
        )
        r = self._set_concern_tree(tree_text)
        # expected_count = 70 (trivial excluded), rendered = 70 → 100% → pass.
        self.assertEqual(r.returncode, 0, r.stderr)


class Test11IncludesCanonicalAggregators(_SetConcernTreeBase):
    """Test 11: index has mod.rs and lib.rs aggregators → counted in expected AND rendered."""

    def test_tree_entry_coverage_includes_canonical_aggregators(self):
        self._init_pkg_concern()
        # 8 files: 6 normal + mod.rs + lib.rs (canonical aggregators).
        # Canonical aggregators are NOT in trivial-leaf dirs → counted in expected.
        files = [
            "src/components/mod.rs",
            "src/components/lib.rs",
            "src/components/a.rs",
            "src/components/b.rs",
            "src/components/c.rs",
            "src/components/d.rs",
            "src/components/e.rs",
            "src/components/f.rs",
        ]
        self._write_index_json({
            "apps/web": {"files": files, "files_truncated": False},
        })
        # Render all 8 entries → coverage = 100% → pass.
        tree_text = self._make_tree_text([
            "mod.rs", "lib.rs", "a.rs", "b.rs", "c.rs", "d.rs", "e.rs", "f.rs",
        ])
        r = self._set_concern_tree(tree_text)
        self.assertEqual(r.returncode, 0, r.stderr)


class Test12CoverageSkippedWhenExpectedBelow5(_SetConcernTreeBase):
    """Test 12: 4 files → expected ≤ 5 → coverage check skipped regardless of ratio."""

    def test_tree_entry_coverage_skipped_when_expected_below_5(self):
        self._init_pkg_concern()
        # Only 4 files → expected_count = 4 ≤ 5 → guard kicks in.
        files = [
            "src/components/a.ts",
            "src/components/b.ts",
            "src/components/c.ts",
            "src/components/d.ts",
        ]
        self._write_index_json({
            "apps/web": {"files": files, "files_truncated": False},
        })
        # Only 1 entry rendered → would be 25% if gate applied; shouldn't apply.
        tree_text = self._make_tree_text(["a.ts"])
        r = self._set_concern_tree(tree_text)
        self.assertEqual(r.returncode, 0, r.stderr)


class Test13CanonicalThresholdValue(unittest.TestCase):
    """Test 13: Regression guard — TREE_ENTRY_COVERAGE_THRESHOLD is exactly 0.80."""

    def test_tree_entry_coverage_canonical_threshold_value(self):
        self.assertEqual(TREE_ENTRY_COVERAGE_THRESHOLD, 0.80)


# ---------------------------------------------------------------------------
# Unit tests for helper functions (no subprocess)
# ---------------------------------------------------------------------------


class TestLoadIndexFiles(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.devforge_dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_returns_none_when_index_missing(self):
        """U1: No index.json → returns None."""
        result = _load_index_files(self.devforge_dir, "apps/web")
        self.assertIsNone(result)

    def test_returns_none_on_bad_json(self):
        """U2: Malformed JSON → returns None."""
        (self.devforge_dir / "index.json").write_text("NOT JSON", encoding="utf-8")
        result = _load_index_files(self.devforge_dir, "apps/web")
        self.assertIsNone(result)

    def test_returns_none_when_pkg_path_missing(self):
        """U3: pkg_path not in index.json["packages"] → returns None."""
        index = {
            "version": 1,
            "packages": {
                "other/pkg": {"files": ["src/a.ts"], "files_truncated": False},
            },
        }
        (self.devforge_dir / "index.json").write_text(
            json.dumps(index), encoding="utf-8"
        )
        result = _load_index_files(self.devforge_dir, "apps/web")
        self.assertIsNone(result)

    def test_returns_files_list_on_success(self):
        """Happy path: returns list of file strings."""
        files = ["src/components/a.ts", "src/components/b.ts"]
        index = {
            "version": 1,
            "packages": {
                "apps/web": {"files": files, "files_truncated": False},
            },
        }
        (self.devforge_dir / "index.json").write_text(
            json.dumps(index), encoding="utf-8"
        )
        result = _load_index_files(self.devforge_dir, "apps/web")
        self.assertEqual(result, files)

    def test_progressive_suffix_match_strips_monorepo_prefix(self):
        """State pkg_path may carry a monorepo prefix not present in index.

        Regression: testForge20 registers package as
        `db-cse-ui-strata/apps/app-web` while init-forge writes index
        keyed by `apps/app-web` (package-relative). Coverage gate must
        find the files via progressive-suffix lookup, not silent skip.
        """
        files = ["src/components/a.ts", "src/components/b.ts"]
        index = {
            "version": 1,
            "packages": {
                "apps/app-web": {"files": files, "files_truncated": False},
            },
        }
        (self.devforge_dir / "index.json").write_text(
            json.dumps(index), encoding="utf-8"
        )
        # Caller passes the monorepo-prefixed path; lookup must succeed
        # by stripping `db-cse-ui-strata/` and matching `apps/app-web`.
        result = _load_index_files(
            self.devforge_dir, "db-cse-ui-strata/apps/app-web",
        )
        self.assertEqual(result, files)

    def test_progressive_suffix_returns_none_when_no_suffix_matches(self):
        """If no suffix of pkg_path is in index, return None."""
        index = {
            "version": 1,
            "packages": {
                "completely/different/pkg": {
                    "files": ["x.ts"], "files_truncated": False,
                },
            },
        }
        (self.devforge_dir / "index.json").write_text(
            json.dumps(index), encoding="utf-8"
        )
        result = _load_index_files(
            self.devforge_dir, "monorepo/apps/app-web",
        )
        self.assertIsNone(result)


class TestPathContainsTrivialDir(unittest.TestCase):

    def test_detects_node_modules_component(self):
        """U4: Path through node_modules → True."""
        self.assertTrue(
            _path_contains_trivial_dir("src/components/node_modules/pkg/index.js")
        )

    def test_clean_path_returns_false(self):
        self.assertFalse(
            _path_contains_trivial_dir("src/components/auth/login.ts")
        )

    def test_detects_pycache(self):
        self.assertTrue(
            _path_contains_trivial_dir("src/__pycache__/module.pyc")
        )

    def test_detects_dist(self):
        self.assertTrue(
            _path_contains_trivial_dir("src/components/dist/bundle.js")
        )


class TestBuildExpectedEntrySet(unittest.TestCase):

    def test_counts_files_and_intermediate_dirs(self):
        """U5: files + their intermediate dirs are counted."""
        files = [
            "src/components/auth/login.ts",
            "src/components/auth/logout.ts",
            "src/components/ui/Button.ts",
        ]
        # Expected entries for prefix "src/components/":
        #   auth/login.ts  → auth/, auth/login.ts
        #   auth/logout.ts → auth/ (already), auth/logout.ts
        #   ui/Button.ts   → ui/, ui/Button.ts
        # Total: auth/, auth/login.ts, auth/logout.ts, ui/, ui/Button.ts = 5
        count = _build_expected_entry_set(files, "src/components/")
        self.assertEqual(count, 5)

    def test_excludes_trivial_leaf_paths(self):
        """Files under node_modules are excluded entirely."""
        files = [
            "src/components/a.ts",
            "src/components/node_modules/pkg/index.js",
        ]
        count = _build_expected_entry_set(files, "src/components/")
        # Only a.ts → 1 entry.
        self.assertEqual(count, 1)

    def test_only_files_under_prefix_counted(self):
        """Files outside the subfolder prefix are not counted."""
        files = [
            "src/auth/login.ts",        # outside src/components/
            "src/components/comp.ts",   # inside
        ]
        count = _build_expected_entry_set(files, "src/components/")
        self.assertEqual(count, 1)

    def test_empty_files_list_returns_zero(self):
        count = _build_expected_entry_set([], "src/components/")
        self.assertEqual(count, 0)


class TestCountRenderedTreeEntries(unittest.TestCase):

    def test_counts_glyph_lines_only(self):
        tree = "\n".join([
            "src/components/",      # header — no glyph → not counted
            "├── auth/",            # glyph → counted
            "│   ├── login.ts",     # glyph → counted
            "│   └── logout.ts",    # glyph → counted
            "└── ui/",              # glyph → counted
        ])
        self.assertEqual(_count_rendered_tree_entries(tree), 4)

    def test_empty_text_returns_zero(self):
        self.assertEqual(_count_rendered_tree_entries(""), 0)

    def test_header_only_returns_zero(self):
        self.assertEqual(_count_rendered_tree_entries("src/components/"), 0)


class TestCheckTreeEntryCoverage(unittest.TestCase):
    """Pure-function tests for _check_tree_entry_coverage."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.devforge_dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _write_index(self, files, pkg_path="apps/web"):
        index = {
            "version": 1,
            "packages": {pkg_path: {"files": files, "files_truncated": False}},
        }
        (self.devforge_dir / "index.json").write_text(
            json.dumps(index), encoding="utf-8"
        )

    def _make_tree(self, n_entries):
        lines = ["src/components/"]
        for i in range(n_entries):
            glyph = "└── " if i == n_entries - 1 else "├── "
            lines.append("{0}file_{1:03d}.ts".format(glyph, i))
        return "\n".join(lines)

    def test_returns_none_when_index_missing(self):
        """No index.json → graceful degrade → None."""
        tree = self._make_tree(3)
        result = _check_tree_entry_coverage(
            tree, "apps/web", "components", self.devforge_dir
        )
        self.assertIsNone(result)

    def test_returns_none_when_expected_zero(self):
        """Subfolder not in index → graceful degrade → None."""
        self._write_index(["src/auth/login.ts"])  # no src/components/ files
        tree = self._make_tree(5)
        result = _check_tree_entry_coverage(
            tree, "apps/web", "components", self.devforge_dir
        )
        self.assertIsNone(result)

    def test_returns_none_when_coverage_meets_threshold(self):
        """80 entries / 100 expected → 80% >= 80% → None (pass)."""
        files = ["src/components/f_{0:03d}.ts".format(i) for i in range(100)]
        self._write_index(files)
        tree = self._make_tree(80)
        result = _check_tree_entry_coverage(
            tree, "apps/web", "components", self.devforge_dir
        )
        self.assertIsNone(result)

    def test_returns_error_message_when_below_threshold(self):
        """23 entries / 100 expected → 23% < 80% → error message string."""
        files = ["src/components/f_{0:03d}.ts".format(i) for i in range(100)]
        self._write_index(files)
        tree = self._make_tree(23)
        result = _check_tree_entry_coverage(
            tree, "apps/web", "components", self.devforge_dir
        )
        self.assertIsNotNone(result)
        self.assertIn("tree coverage", result)
        self.assertIn("23.0%", result)
        self.assertIn("80.0%", result)
        self.assertIn("rendered 23", result)
        self.assertIn("expected 100", result)
        self.assertIn("concern=components", result)

    def test_returns_none_when_expected_below_5(self):
        """Only 4 expected entries → small-concern guard → None."""
        files = [
            "src/components/a.ts",
            "src/components/b.ts",
            "src/components/c.ts",
            "src/components/d.ts",
        ]
        self._write_index(files)
        tree = self._make_tree(1)  # 1/4 = 25% — would fail if gate applied
        result = _check_tree_entry_coverage(
            tree, "apps/web", "components", self.devforge_dir
        )
        self.assertIsNone(result)

    def test_exactly_at_threshold_returns_none(self):
        """Coverage exactly = 0.80 → should pass (>= threshold)."""
        files = ["src/components/f_{0:03d}.ts".format(i) for i in range(100)]
        self._write_index(files)
        tree = self._make_tree(80)  # 80/100 = 0.80
        result = _check_tree_entry_coverage(
            tree, "apps/web", "components", self.devforge_dir
        )
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
