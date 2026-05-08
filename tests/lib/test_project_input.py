"""Tests for _project_input.py — F.8a project-input helper.

Cases:
  1.  _enumerate_packages_with_overviews: walks docs/ for overview.md
      excluding the project-tier docs/overview.md
  2.  _enumerate_packages_with_overviews: missing docs/ → []
  3.  _read_package_seed: parses frontmatter + Purpose section
  4.  _read_package_seed: missing doc → None
  5.  _read_package_seed: malformed frontmatter → None
  6.  _collect_project_root_files: README + CHANGELOG + package.json
  7.  _collect_project_root_files: empty when none exist
  8.  _compute_source_stamp: deterministic across reorderings
  9.  _compute_source_stamp: changes when package stamp changes
 10.  cmd_project_input: synthetic project end-to-end
 11.  cmd_project_input: no package overviews → exit 2
 12.  cmd_project_input: --project label override

Stdlib only. Python 3.8+.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"
if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _generate_docs._project_input import (  # noqa: E402
    _collect_project_root_files,
    _compute_source_stamp,
    _enumerate_packages_with_overviews,
    _read_package_seed,
    cmd_project_input,
)


def _run(handler, args):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = handler(args)
    return code, out.getvalue(), err.getvalue()


_PKG_OVERVIEW_TEMPLATE = """---
package: {pkg}
last_indexed: 2026-05-08
source_stamp: stamp-{stamp}
---


# {pkg}

## Purpose

{purpose}

## Concerns

- alpha — first concern

## Files

- index.ts — barrel re-export
"""


class EnumeratePackagesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.docs = self.root / "docs"

    def _write_overview(self, rel_pkg: str, content: str = "stub"):
        path = self.docs / rel_pkg / "overview.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def test_walks_docs_for_overviews(self):
        self._write_overview("pkg-a")
        self._write_overview("nested/pkg-b")
        # Project-tier overview MUST be excluded
        (self.docs / "overview.md").write_text("project\n", encoding="utf-8")
        result = _enumerate_packages_with_overviews(self.root)
        self.assertEqual(sorted(result), ["nested/pkg-b", "pkg-a"])

    def test_missing_docs_dir(self):
        self.assertEqual(_enumerate_packages_with_overviews(self.root), [])


class ReadPackageSeedTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def _write(self, rel_pkg: str, content: str):
        path = self.root / "docs" / rel_pkg / "overview.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def test_parses_frontmatter_and_purpose(self):
        self._write(
            "pkg-a",
            _PKG_OVERVIEW_TEMPLATE.format(pkg="pkg-a", stamp="A", purpose="Pkg-A purpose paragraph."),
        )
        seed = _read_package_seed(self.root, "pkg-a")
        self.assertIsNotNone(seed)
        self.assertEqual(seed["package"], "pkg-a")
        self.assertEqual(seed["frontmatter"]["source_stamp"], "stamp-A")
        self.assertIn("Pkg-A purpose paragraph.", seed["purpose_text"])

    def test_missing_doc_returns_none(self):
        self.assertIsNone(_read_package_seed(self.root, "pkg-ghost"))

    def test_malformed_frontmatter_returns_none(self):
        self._write("pkg-a", "no frontmatter\n")
        self.assertIsNone(_read_package_seed(self.root, "pkg-a"))


class CollectProjectRootFilesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_picks_up_top_level_files(self):
        (self.root / "README.md").write_text("# project\nintro\n", encoding="utf-8")
        (self.root / "package.json").write_text("{}\n", encoding="utf-8")
        records, hashes = _collect_project_root_files(self.root)
        names = sorted(r["path"] for r in records)
        self.assertIn("README.md", names)
        self.assertIn("package.json", names)
        self.assertEqual(len(hashes), len(records))

    def test_no_eligible_files(self):
        records, hashes = _collect_project_root_files(self.root)
        self.assertEqual(records, [])
        self.assertEqual(hashes, [])


class ComputeSourceStampTests(unittest.TestCase):
    def test_deterministic_across_reordering(self):
        seed_a = {"package": "pkg-a", "frontmatter": {"source_stamp": "1"}}
        seed_b = {"package": "pkg-b", "frontmatter": {"source_stamp": "2"}}
        hashes_1 = [("README.md", "h1"), ("package.json", "h2")]
        hashes_2 = [("package.json", "h2"), ("README.md", "h1")]
        s1 = _compute_source_stamp([seed_a, seed_b], hashes_1)
        s2 = _compute_source_stamp([seed_b, seed_a], hashes_2)
        self.assertEqual(s1, s2)

    def test_changes_when_package_stamp_changes(self):
        v1 = {"package": "pkg-a", "frontmatter": {"source_stamp": "1"}}
        v2 = {"package": "pkg-a", "frontmatter": {"source_stamp": "2"}}
        self.assertNotEqual(
            _compute_source_stamp([v1], []),
            _compute_source_stamp([v2], []),
        )


class CmdProjectInputTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.devforge = self.root / ".devforge"
        self.devforge.mkdir()

    def _write_overview(self, rel_pkg: str, stamp: str = "X", purpose: str = "stub purpose"):
        path = self.root / "docs" / rel_pkg / "overview.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            _PKG_OVERVIEW_TEMPLATE.format(pkg=rel_pkg, stamp=stamp, purpose=purpose),
            encoding="utf-8",
        )

    def test_end_to_end(self):
        self._write_overview("pkg-a", purpose="Alpha purpose.")
        self._write_overview("packages/pkg-b", purpose="Beta purpose.")
        (self.root / "README.md").write_text("# project\n", encoding="utf-8")
        args = argparse.Namespace(
            project="my-project",
            devforge_dir=str(self.devforge),
        )
        code, out, _ = _run(cmd_project_input, args)
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertEqual(payload["project"], "my-project")
        self.assertEqual(len(payload["package_seeds"]), 2)
        self.assertEqual(
            sorted(s["package"] for s in payload["package_seeds"]),
            ["packages/pkg-b", "pkg-a"],
        )
        names = [r["path"] for r in payload["project_root_files"]]
        self.assertIn("README.md", names)
        self.assertRegex(payload["source_stamp"], r"^[0-9a-f]{16}$")

    def test_no_package_overviews_exit_2(self):
        args = argparse.Namespace(project="", devforge_dir=str(self.devforge))
        code, _, err = _run(cmd_project_input, args)
        self.assertEqual(code, 2)
        self.assertIn("no package overviews", err)

    def test_project_label_default_to_root_basename(self):
        self._write_overview("pkg-a")
        args = argparse.Namespace(project="", devforge_dir=str(self.devforge))
        code, out, _ = _run(cmd_project_input, args)
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertEqual(payload["project"], self.root.name)


if __name__ == "__main__":
    unittest.main()
